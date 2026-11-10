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
