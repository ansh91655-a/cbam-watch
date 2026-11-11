"""소급 수집과 소급 게시 도구를 확인한다."""
import unittest

from tools.archive import acts, boards, ecnews, eurlex, gate, newsletter, store
from tools.check import term_check

TOPICS = {"law", "legis", "etc"}
SOURCE = "26 February 2025\nCommission proposes to simplify CBAM\nThe new 50 tonne mass threshold keeps 99% of emissions in scope.\n"


def draft(**changes):
    item = {"id": "20250226-ec-news-abc123", "published": "2025-02-26", "title": "CBAM 간소화 제안", "kind": "입법", "topic": "legis",
            "importance": "높음", "sourceCode": "ec-news", "sourceName": "EC", "link": "https://example.eu/news/a_en", "tier": "A",
            "summary": "EU 집행위원회는 2025년 2월 26일에 CBAM 간소화를 제안했습니다. 50톤 기준을 두어도 배출량의 99%가 대상에 남습니다."}
    item.update(changes)
    return item


class GateTest(unittest.TestCase):
    INDEX = {"rules": []}

    def problems(self, item, source=SOURCE):
        return gate.problems(item, source, self.INDEX, TOPICS)

    def test_good_item_passes(self):
        self.assertEqual(self.problems(draft()), [])

    def test_plain_ending_is_rejected(self):
        found = self.problems(draft(summary="EU 집행위원회는 2025년 2월 26일에 CBAM 간소화를 제안했다."))
        self.assertTrue(any(text.startswith("문체") for text in found), found)

    def test_number_not_in_source_is_rejected(self):
        found = self.problems(draft(summary="EU 집행위원회는 2025년 2월 26일에 제안했습니다. 배출량의 90%가 대상에 남습니다."))
        self.assertEqual(found, ["사실 대조: 원문에서 찾지 못함 90"])

    def test_allowed_value_needs_a_reason(self):
        item = draft(summary="EU 집행위원회는 2025년 2월 26일에 제안했습니다. 수입자의 약 90%가 빠집니다.", factAllow=["90"])
        self.assertEqual(len(self.problems(item)), 1)
        item["factNote"] = "원문은 'around nine in ten importers'로 적음"
        self.assertEqual(self.problems(item), [])

    def test_published_date_must_be_in_source(self):
        found = self.problems(draft(published="2025-02-27", summary="EU 집행위원회는 CBAM 간소화를 제안했습니다."))
        self.assertEqual(found, ["게시일 2025-02-27이 원문 글에 없음"])

    def test_missing_source_and_unknown_topic(self):
        self.assertIn("원문 글 없음", self.problems(draft(), source=None))
        self.assertIn("주제", self.problems(draft(topic="none")))

    def test_link_must_come_from_collected_material(self):
        self.assertEqual(gate.problems(draft(), SOURCE, self.INDEX, TOPICS, {"https://example.eu/news/a_en"}), [])
        self.assertEqual(gate.problems(draft(), SOURCE + "[주소] https://example.eu/news/a_en", self.INDEX, TOPICS, set()), [])
        self.assertIn("링크가 모아 둔 자료에 없는 주소", gate.problems(draft(link="https://example.eu/news/b_en"), SOURCE, self.INDEX, TOPICS, {"https://example.eu/news/a_en"}))

    def test_avoided_term_is_rejected(self):
        index = term_check.load()
        hard = next((rule for rule in index["rules"] if rule["hard"]), None)
        if hard is None:
            self.skipTest("강하게 막는 표기가 용어집에 없음")
        found = gate.problems(draft(summary=f"{hard['avoid']}에 관한 소식입니다. 2025년 2월 26일에 나왔습니다."), SOURCE, index, TOPICS)
        self.assertTrue(any(text.startswith("용어") for text in found), found)

    def test_excerpt_only_for_official_sources_and_exact_text(self):
        self.assertEqual(gate.excerpt_of(draft(excerpt="Commission proposes to simplify CBAM"), SOURCE), "Commission proposes to simplify CBAM")
        self.assertEqual(gate.excerpt_of(draft(excerpt="Commission proposes to simplify CBAM", tier="B"), SOURCE), "")
        self.assertEqual(gate.excerpt_of(draft(excerpt="Commission proposed to simplify CBAM"), SOURCE), "")


class ReadersTest(unittest.TestCase):
    def test_article_keeps_only_the_body(self):
        lines = ["Price published - Taxation and Customs Union Skip to main content", "Menu", "CBAM", "Home", "News", "Price published", "Price published",
                 "The first CBAM price is out.", "News article", "7 April 2026", "1 min read", "Body line about CBAM.", "Publication date", "7 April 2026", "Footer CBAM"]
        title, text = ecnews.article(lines)
        self.assertEqual(title, "Price published")
        self.assertEqual(text[0], "Price published")
        self.assertEqual(text[1], "The first CBAM price is out.")
        self.assertEqual(text[-1], "Body line about CBAM.")
        self.assertEqual(len(ecnews.KEY.findall("\n".join(text))), 2)  # 메뉴와 바닥글의 CBAM은 세지 않는다

    def test_sitemap_pattern(self):
        xml = "<url><loc>https://taxation-customs.ec.europa.eu/news/first-cbam-certificate-price-now-available-2026-04-07_en</loc></url><url><loc>https://taxation-customs.ec.europa.eu/index_en</loc></url>"
        self.assertEqual(ecnews.NEWS_LOC.findall(xml), [("https://taxation-customs.ec.europa.eu/news/first-cbam-certificate-price-now-available-2026-04-07_en", "2026-04-07")])

    def test_lead_is_subtitles_and_first_paragraph(self):
        first = "정부는 10월 23일 오후 2시에 서울에서 업계 설명회를 열었다고 밝혔다."
        lines = ["설명회 개최", "담당부서", "설명회 개최", "- 부제 하나", "- 부제 둘", first, "둘째 문단은 싣지 않는다. 길이가 충분히 긴 문장이어도 마찬가지다.", "목록"]
        self.assertEqual(boards.lead_of(lines, "설명회 개최"), "- 부제 하나\n- 부제 둘\n" + first)
        self.assertEqual(boards.lead_of(lines, "없는 제목"), "")
        # 제목이 본문에 다시 나오지 않는 글: 담당자와 첨부파일 줄을 건너뛰고 본문의 첫 문단을 찾는다
        lines = ["책자 발간", "담당자홍길동", "담당부서통상과", "연락처044-000-0000", "등록일2026-03-30", "조회수1,234", "첨부파일", "책자.pdf [1 MB] 바로보기", "81",
                 "정부는 3월 30일에 기업이 실무에 바로 쓸 수 있는 매뉴얼 책자를 발간했다고 밝혔다.", "둘째 문단은 싣지 않는다. 길이가 충분히 긴 문장이어도 마찬가지다.", "목록"]
        self.assertEqual(boards.lead_of(lines, "책자 발간"), "정부는 3월 30일에 기업이 실무에 바로 쓸 수 있는 매뉴얼 책자를 발간했다고 밝혔다.")



class LawAndNewsletterTest(unittest.TestCase):
    def test_act_digest(self):
        lines = ["L_1.xml", "Official Journal", "of the European Union", "EN", "L series", "2025/2621", "31.12.2025", "COMMISSION IMPLEMENTING REGULATION (EU) 2025/2621",
                 "of 16 December 2025", "laying down rules as regards the establishment of default values", "Whereas:", "Article 1", "Default values are set out in Annex I.",
                 "Article 2", "This Regulation shall enter into force on the third day following that of its publication.", "It shall apply from 1 January 2026.",
                 "Done at Brussels, 16 December 2025.", "For the Commission", "ANNEX I", "a very long table", "ELI: http://data.europa.eu/eli/reg_impl/2025/2621/oj"]
        kept, published, adopted, name, subject = eurlex.digest(lines)
        self.assertEqual((published, adopted), ("2025-12-31", "2025-12-16"))
        self.assertEqual(name, "COMMISSION IMPLEMENTING REGULATION (EU) 2025/2621")
        self.assertTrue(subject.startswith("laying down rules"))
        self.assertIn("It shall apply from 1 January 2026.", kept)
        self.assertEqual(kept[-1], "ELI: http://data.europa.eu/eli/reg_impl/2025/2621/oj")
        self.assertEqual(kept[kept.index("[마지막 조문]") + 1], "Article 2")

    def test_newsletter_issues(self):
        html = ('<html><body><table><tr><td>15/10/2026</td><td><a href="/newsroom/taxud/newsletter-archives/80397">CBAM Newsletter #4: New webinar</a></td></tr>'
                '<tr><td>31/08/2026</td><td><a href="/newsroom/taxud/newsletter-archives/78600">CBAM Newsletter #3: Latest guidance</a></td></tr></table>'
                '<a href="/newsroom/taxud/newsletter-archives/view">Archives</a></body></html>')
        found = newsletter.issues_of(html, "https://ec.europa.eu/newsroom/taxud/newsletter-archives/view/service/9510?page=1")
        self.assertEqual([(issue["date"], issue["url"].rsplit("/", 1)[-1]) for issue in found], [("2026-10-15", "80397"), ("2026-08-31", "78600")])

    def test_newsletter_body_drops_the_site_menu(self):
        lines = ["TAXUD - Newsletter", "Menu", "Search", "CBAM Newsletter #4", "Dear CBAM Insiders", "Menu", "New webinar available"]
        self.assertEqual(newsletter.body_of(lines, "CBAM Newsletter #4"), ["CBAM Newsletter #4", "Dear CBAM Insiders", "New webinar available"])


class MoreReadersTest(unittest.TestCase):
    def test_related_documents_are_chosen_by_how_they_are_linked(self):
        from tools.archive import docs
        rows = [
            {"celex": "52025PC0990", "date": "2025-12-17", "relations": ["http://x#work_cites_work:32023R0956", "title-match"]},
            {"celex": "52025SC0988", "date": "2025-12-17", "relations": ["http://x#work_cites_work:32023R0956"]},
            {"celex": "52026PC0616", "date": "2026-07-17", "relations": ["http://x#work_cites_work:32023R0956"]},
            {"celex": "32025R2546", "date": "2025-12-10", "relations": ["http://x#resource_legal_based_on_resource_legal:32023R0956"]},
            {"celex": "02023R0956-20251020", "date": "2025-10-20", "relations": ["title-match"]},
            {"celex": "32023R1773", "date": "2023-08-17", "relations": ["http://x#resource_legal_based_on_resource_legal:32023R0956"]},
            {"celex": "52026SC0067", "date": "2026-03-16", "relations": ["title-match"]},
            {"celex": "32025R2083R(01)", "date": "2025-11-12", "relations": ["http://x#resource_legal_corrects_resource_legal:32025R2083"]},
        ]
        self.assertEqual([row["celex"] for row in docs.wanted(rows)], ["52025PC0990", "52026PC0616"])

    def test_procedure_numbers_in_a_proposal(self):
        from tools.archive import docs
        self.assertEqual(docs.procedures_in(["COM(2025) 990 final", "2025/0418 (COD)", "Proposal for a", "see also 2025/0419(COD)"]),
                         ["2025/0418(COD)", "2025/0419(COD)"])

    def test_procedure_status_and_forecasts(self):
        from tools.archive import oeil
        self.assertEqual(oeil.status_of(["Subject", "Status", "Awaiting committee decision", "Key players"]), "Awaiting committee decision")
        rows = [["Date", "Event", "Reference", "Summary"], ["16/12/2025", "Legislative proposal published", "COM(2025)0995", "Summary"],
                ["Date", "Subject"], ["14/12/2026", "Indicative plenary sitting date, 1st reading"], ["Procedure reference", "2025/0420(COD)"]]
        self.assertEqual(oeil.forecasts_of(rows), [{"date": "2026-12-14", "subject": "Indicative plenary sitting date, 1st reading"}])
        title, events = oeil.events_of(["Full procedure", "A title"], rows, "2025/0420(COD)")
        self.assertEqual((title, [event["date"] for event in events]), ("A title", ["2025-12-16"]))

    def test_daily_news_keeps_only_the_passages_about_cbam(self):
        from tools.archive import presscorner
        lines = ["Daily News", "Farm item", "The Commission published the CBAM certificate price.", "It is EUR 82.32.", "Other item", "More"]
        self.assertEqual(presscorner.around(lines), ["Farm item", "The Commission published the CBAM certificate price.", "It is EUR 82.32."])
        self.assertTrue(presscorner.TITLE.search("Commission proposes ETS review"))
        self.assertFalse(presscorner.TITLE.search("Commission approves State aid for offshore wind"))

    def test_uk_instrument_dates(self):
        from tools.archive import ukleg
        lines = ["Statutory Instruments", "2026 No. 995", "CARBON BORDER ADJUSTMENT MECHANISM", "Made", "8th September 2026",
                 "Laid before the House of Commons", "9th September 2026", "Coming into force", "1st January 2027"]
        self.assertEqual(ukleg.dates_of(lines), {"Made": "8th September 2026", "Laid before the House of Commons": "9th September 2026",
                                                  "Coming into force": "1st January 2027"})
        self.assertTrue(ukleg.ITEM.match("https://www.legislation.gov.uk/uksi/2026/995/contents/made"))
        self.assertFalse(ukleg.ITEM.match("https://www.legislation.gov.uk/search?type=uksi"))


class ToFeedTest(unittest.TestCase):
    def test_only_unseen_records_become_candidates(self):
        from tools.archive import tofeed
        names = [record[0] for record in tofeed.RECORDS]
        everything, now = tofeed.fresh({name: [] for name in names})
        codes = {record[1] for record in tofeed.RECORDS}
        self.assertTrue(everything and all(item["kind"] == "link" and item["source"] in codes for item in everything))
        self.assertTrue(all(item["textPath"].startswith("collected/archive/pages/") for item in everything))
        again, _ = tofeed.fresh(now)
        self.assertEqual(again, [])
        partly = {name: values[1:] for name, values in now.items()}
        self.assertEqual(len(tofeed.fresh(partly)[0]), sum(1 for values in now.values() if values))

    def test_a_record_added_to_the_list_is_only_noted_the_first_time(self):
        from tools.archive import tofeed
        first, now = tofeed.fresh({})
        self.assertEqual(first, [])
        self.assertEqual(set(now), {record[0] for record in tofeed.RECORDS})


class GovUkTest(unittest.TestCase):
    def test_search_keeps_only_cbam_titles_on_gov_uk_since_the_start(self):
        from tools.archive import govuk
        rows = [{"title": "Carbon Border Adjustment Mechanism (CBAM): a consultation", "link": "/government/consultations/a", "public_timestamp": "2026-10-28T12:00:00Z"},
                {"title": "Budget 2026", "link": "/government/publications/b", "public_timestamp": "2026-10-28T12:00:00Z"},
                {"title": "Criminal Bills Assessment Manual (CBAM) and Supervisor Guidance", "link": "/government/news/e", "public_timestamp": "2026-07-31T12:00:00Z"},
                {"title": "CBAM policy update", "link": "https://example.org/c", "public_timestamp": "2026-10-28T12:00:00Z"},
                {"title": "Factsheet: CBAM", "link": "/government/publications/d", "public_timestamp": "2024-03-01T12:00:00Z"}]
        self.assertEqual(govuk.titled(rows), ["/government/consultations/a"])

    def test_change_rows_carry_the_consultation_period(self):
        from tools.archive import govuk
        document = {"title": "T", "document_type": "open_consultation", "first_published_at": "2026-10-28T12:30:00+00:00",
                    "details": {"opening_date": "2026-10-28T12:30:00+00:00", "closing_date": "2027-01-20T23:59:00+00:00",
                                "change_history": [{"public_timestamp": "2026-10-28T12:30:00+00:00", "note": "First  published."}]}}
        rows = govuk.changes_of(document, "/government/consultations/a", "search")
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0]["date"], rows[0]["opens"], rows[0]["closes"], rows[0]["via"]), ("2026-10-28", "2026-10-28", "2027-01-20", "search"))
        self.assertEqual(rows[0]["key"], "/government/consultations/a@2026-10-28")
        self.assertIn("의견 접수 2026-10-28~2027-01-20", govuk._line(rows[0]))


class StoreTest(unittest.TestCase):
    def test_dates(self):
        self.assertEqual(store.iso_from_long("30 September 2026"), "2026-09-30")
        self.assertEqual(store.iso_from_long("Latest news"), "")
        self.assertEqual(store.iso_from_numbers("17/12/2025"), "2025-12-17")
        self.assertEqual(store.iso_from_numbers("2026.10.01"), "2026-10-01")
        self.assertEqual(store.iso_from_numbers("2026-11-09"), "2026-11-09")

    def test_slug(self):
        self.assertEqual(store.slug("CBAM: New Guidance (2026)"), "cbam-new-guidance-2026")


class FourColumnTest(unittest.TestCase):
    """네 칸 대조 문서: 낱말의 자리로 칸을 가리고, 줄이 그어진 말을 따로 적는다."""

    @staticmethod
    def word(text, x0, top, font="TimesNewRomanPSMT", width=20):
        return {"text": text, "x0": x0, "x1": x0 + width, "top": top, "bottom": top + 11, "fontname": font}

    def test_words_fall_into_columns_by_their_left_edge(self):
        from tools.archive import fourcolumn
        self.assertEqual([fourcolumn.column_of(x) for x in (54, 63, 100, 274, 449, 629)], ["", "번호", "집행위", "의회", "이사회", "합의안"])

    def test_struck_words_leave_the_current_text_and_added_words_are_listed(self):
        from tools.archive import fourcolumn
        w = self.word
        words = [
            w("Recital", 54, 100, "ABC+Calibri"), w("21", 90, 100, "ABC+Calibri"),
            w("34", 63, 118), w("(21)", 100, 118), w("credits", 125, 118),
            w("deleted", 274, 118),
            w("(21)", 449, 118), w("credits", 475, 118),
            w("Article", 54, 150, "ABC+Calibri"), w("30", 90, 150, "ABC+Calibri"),
            w("204d", 63, 168), w("redirect", 274, 168, "TimesNewRomanPS-BoldItalicMT"), w("revenues", 300, 168, "TimesNewRomanPS-BoldItalicMT"),
        ]
        rects = [{"x0": 475, "x1": 495, "top": 123.5, "height": 0.6}]   # 이사회 칸의 credits 위에 그은 줄
        rows = fourcolumn.rows_of([(31, fourcolumn.mark(words, rects))])
        self.assertEqual([row["number"] for row in rows], ["34", "204d"])
        self.assertEqual(rows[0]["cells"], {"집행위": "(21) credits", "의회": "deleted", "이사회": "(21)"})
        self.assertEqual(rows[0]["removed"], {"이사회": "credits"})
        self.assertEqual(rows[1]["added"], {"의회": "redirect revenues"})
        lines = fourcolumn.text_lines(rows)
        self.assertIn("[이사회 34 지움] credits", lines)
        self.assertIn("[의회 204d 더함] redirect revenues", lines)
        self.assertEqual([row["number"] for row in fourcolumn.only_in(rows, "의회")], ["204d"])

    def test_an_underline_below_the_word_is_not_a_strike(self):
        from tools.archive import fourcolumn
        word = self.word("kept", 274, 100)
        self.assertFalse(fourcolumn.struck(word, [{"x0": 274, "x1": 294, "top": 110.6, "height": 0.6}]))
        self.assertTrue(fourcolumn.struck(word, [{"x0": 274, "x1": 294, "top": 105.5, "height": 0.6}]))


class DatabaseOutageTest(unittest.TestCase):
    """EU 법령 데이터베이스가 답하지 않는 날에도 모아 둔 목록이 줄어들지 않는지."""

    def setUp(self):
        import os
        import tempfile
        self.folder = tempfile.TemporaryDirectory()
        self.previous = os.getcwd()
        os.chdir(self.folder.name)

    def tearDown(self):
        import os
        os.chdir(self.previous)
        self.folder.cleanup()

    def test_missing_documents_and_relations_come_back_from_the_stored_list(self):
        from tools.archive import cellar
        found = {"32025R2546": {"celex": "32025R2546", "date": "2025-12-10", "title": "", "relations": ["resource_legal_based_on_resource_legal:32023R0956"]}}
        before = [
            {"celex": "32025R2546", "date": "2025-12-10", "title": "Implementing Regulation", "relations": ["resource_legal_based_on_resource_legal:32023R0956", "title-match"], "url": "x"},
            {"celex": "32026D2256", "date": "2026-09-24", "title": "Council Decision", "relations": ["title-match"], "url": "y"},
        ]
        self.assertEqual(cellar.restore(found, before), 1)
        self.assertEqual(found["32025R2546"]["relations"], ["resource_legal_based_on_resource_legal:32023R0956", "title-match"])
        self.assertEqual((found["32025R2546"]["title"], found["32026D2256"]["date"]), ("Implementing Regulation", "2026-09-24"))

    def test_a_day_without_answers_keeps_the_stored_list(self):
        from unittest import mock
        from tools.archive import cellar
        from tools.common.jsonio import read_json, write_json
        entries = [{"celex": "32026D2256", "date": "2026-09-24", "title": "Council Decision", "relations": ["title-match"], "url": "y"}]
        write_json(cellar.ROOT / "eur-lex-related.json", {"report": {"cases": {"62023CJ0512": "2025-05-08"}}, "entries": entries})
        with mock.patch.object(cellar, "ask", return_value=([], "503 Service Temporarily Unavailable")):
            report = cellar.crawl()
        stored = read_json(cellar.ROOT / "eur-lex-related.json", {})
        self.assertEqual([entry["celex"] for entry in stored["entries"]], ["32026D2256"])
        self.assertEqual((report["keptFromBefore"], report["works"], report["cases"]), (1, 1, {"62023CJ0512": "2025-05-08"}))
        self.assertTrue(report["failures"])

    def test_an_incomplete_run_never_shrinks_a_stored_list(self):
        from tools.archive import store
        from tools.common.jsonio import read_json
        first = {"number": "2026 No. 802", "title": "행정 규정", "url": "https://uk.example/802"}
        second = {"number": "2026 No. 809", "title": "요율 규정", "url": "https://uk.example/809"}
        store.save_index("uk-legislation", [first, second], {"found": 2, "failures": []})
        store.save_index("uk-legislation", [], {"error": "503"})  # 목록을 읽지 못한 날
        stored = read_json(store.ROOT / "uk-legislation.json", {})
        self.assertEqual(([entry["number"] for entry in stored["entries"]], stored["report"]["keptFromBefore"]), (["2026 No. 802", "2026 No. 809"], 2))
        store.save_index("uk-legislation", [second], {"found": 2, "failures": ["행정 규정 (timeout)"]})  # 하나를 읽지 못한 날
        self.assertEqual(len(read_json(store.ROOT / "uk-legislation.json", {})["entries"]), 2)
        store.save_index("uk-legislation", [second], {"found": 1, "failures": []})  # 다 읽은 날은 그날의 목록 그대로
        self.assertEqual([entry["number"] for entry in read_json(store.ROOT / "uk-legislation.json", {})["entries"]], ["2026 No. 809"])

    def test_a_procedure_page_that_fails_keeps_its_stored_events(self):
        from unittest import mock
        from tools.archive import oeil
        from tools.common.jsonio import read_json, write_json
        reference = "2025/0419(COD)"
        event = {"date": "2026-09-15", "event": "Decision by Parliament, 1st reading", "reference": "T10-0276/2026", "procedure": reference, "procedureTitle": "CBAM"}
        info = {"title": "CBAM", "events": 1, "status": "Awaiting Council's 1st reading position", "forecasts": [], "url": "https://oeil.example/x"}
        write_json(oeil.ROOT / "ep-oeil.json", {"report": {"procedures": {reference: info}}, "entries": [event]})
        with mock.patch.object(oeil, "procedures", return_value=[reference]), mock.patch.object(oeil.time, "sleep"), \
                mock.patch.object(oeil, "fetch", return_value=(503, {}, b"", "Service Unavailable")):
            report = oeil.crawl()
        stored = read_json(oeil.ROOT / "ep-oeil.json", {})
        self.assertEqual(stored["entries"], [event])
        self.assertEqual((report["procedures"][reference], len(report["failures"])), (info, 1))

    def test_documents_already_stored_stay_listed_when_time_runs_out(self):
        import time
        from unittest import mock
        from tools.archive import docs
        from tools.common.jsonio import read_json, write_json
        linked = ["resource_legal_based_on_resource_legal:32023R0956"]
        write_json(docs.ROOT / "eur-lex-related.json", {"entries": [
            {"celex": "52026PC0001", "date": "2026-03-01", "title": "new one", "relations": linked},
            {"celex": "52025PC0989", "date": "2025-12-17", "title": "stored one", "relations": linked},
        ]})
        text = docs.ROOT / "pages" / "eur-lex-docs" / "52025PC0989.txt"
        text.parent.mkdir(parents=True)
        text.write_text("stored", encoding="utf-8")
        write_json(docs.ROOT / "eur-lex-docs.json", {"entries": [{"celex": "52025PC0989", "date": "2025-12-17", "title": "stored one", "textPath": str(text)}]})
        with mock.patch.object(docs, "lines_of") as fetching:
            report = docs.crawl(deadline=time.monotonic() - 1)
        fetching.assert_not_called()
        self.assertEqual([entry["celex"] for entry in read_json(docs.ROOT / "eur-lex-docs.json", {})["entries"]], ["52025PC0989"])
        self.assertEqual((report["kept"], report["stoppedAt"]), (1, "52026PC0001"))


class ActsTest(unittest.TestCase):
    """법령 본문 받아 두기: 전문과 조문은 모두 남기고 부속서는 앞부분만 남긴다."""

    def test_the_body_is_kept_whole_and_each_annex_is_cut(self):
        lines = ["Article 1", "Subject matter", "Article 2", "ANNEX I", "a", "b", "c", "d", "ANNEX II", "e", "f"]
        self.assertEqual(acts.trim(lines, keep=2), ["Article 1", "Subject matter", "Article 2", "ANNEX I", "a", "b", "[이 부속서의 나머지 2줄은 싣지 않음]", "ANNEX II", "e", "f"])

    def test_a_text_without_annexes_is_unchanged(self):
        lines = ["Article 1", "The word ANNEX in a sentence is not a heading", "Article 2"]
        self.assertEqual(acts.trim(lines, keep=1), lines)

    def test_every_act_is_listed_once(self):
        numbers = [celex for celex, _ in acts.ACTS]
        self.assertEqual(len(numbers), len(set(numbers)))
        self.assertTrue(all(len(celex) == 10 and celex.startswith("3") for celex in numbers))


if __name__ == "__main__":
    unittest.main()
