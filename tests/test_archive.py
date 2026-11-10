"""소급 수집과 소급 게시 도구를 확인한다."""
import unittest

from tools.archive import boards, ecnews, eurlex, gate, newsletter, store
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

    def test_compass_view_address(self):
        self.assertEqual(boards._compass_view("1"), "https://www.compass.or.kr/eucbam/data/view?idx=MQ%3D%3D")
        self.assertEqual(boards._compass_view(""), "")


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
        everything, now = tofeed.fresh({})
        self.assertTrue(everything and all(item["kind"] == "link" and item["source"] in ("ec-press", "eur-lex-related", "us-fedreg") for item in everything))
        self.assertTrue(all(item["textPath"].startswith("collected/archive/pages/") for item in everything))
        again, _ = tofeed.fresh(now)
        self.assertEqual(again, [])
        partly = {name: values[1:] for name, values in now.items()}
        self.assertEqual(len(tofeed.fresh(partly)[0]), len(now))


class StoreTest(unittest.TestCase):
    def test_dates(self):
        self.assertEqual(store.iso_from_long("30 September 2026"), "2026-09-30")
        self.assertEqual(store.iso_from_long("Latest news"), "")
        self.assertEqual(store.iso_from_numbers("17/12/2025"), "2025-12-17")
        self.assertEqual(store.iso_from_numbers("2026.10.01"), "2026-10-01")
        self.assertEqual(store.iso_from_numbers("2026-11-09"), "2026-11-09")

    def test_slug(self):
        self.assertEqual(store.slug("CBAM: New Guidance (2026)"), "cbam-new-guidance-2026")


if __name__ == "__main__":
    unittest.main()
