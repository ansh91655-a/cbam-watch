"""구독 피드: 항목을 누르면 이 사이트의 국문 요약 화면이 먼저 열리고, 원문 주소는 함께 실린다."""
import unittest
import xml.etree.ElementTree as ET

from tools.publish import feed

ATOM = "{http://www.w3.org/2005/Atom}"
SITE = "https://example.org/site/"


def _links(entry):
    return {link.get("rel"): link.get("href") for link in entry.findall(f"{ATOM}link")}


class NewsFeedTest(unittest.TestCase):
    def _entries(self, items):
        root = ET.fromstring(feed.news(items, [{"code": "law", "name": "제도·법령"}], SITE, "2026-11-11T06:00:00+09:00"))
        return root.findall(f"{ATOM}entry")

    def test_an_item_with_a_summary_opens_this_sites_summary_first(self):
        entries = self._entries([{"id": "a-1", "title": "가", "summary": "요약입니다.", "link": "https://eu.example/a?x=1&y=2", "published": "2026-11-10", "topic": "law"}])
        self.assertEqual(len(entries), 1)
        links = _links(entries[0])
        self.assertEqual(links["alternate"], f"{SITE}#item-a-1")
        self.assertEqual(links["related"], "https://eu.example/a?x=1&y=2")
        self.assertEqual(entries[0].find(f"{ATOM}id").text, f"{SITE}#item-a-1")

    def test_a_title_only_item_goes_straight_to_the_original(self):
        entries = self._entries([{"id": "b-1", "title": "나", "brief": True, "link": "https://kr.example/b", "listed": "2026-11-09"}])
        links = _links(entries[0])
        self.assertEqual(links, {"alternate": "https://kr.example/b"})

    def test_it_lists_the_newest_first_with_topic_and_escaped_text(self):
        root = ET.fromstring(feed.news([
            {"id": "a", "title": "A & B", "summary": "요약 <1>", "link": "https://x.example/a?b=1&c=2", "published": "2026-11-01", "topic": "law", "sourceName": "출처"},
            {"id": "b", "title": "B", "summary": "내린 것", "link": "https://x.example/b", "published": "2026-11-05", "withdrawn": True},
            {"id": "c", "title": "C", "summary": "게시일 없음", "link": "https://x.example/c", "listed": "2026-11-09"},
        ], [{"code": "law", "name": "제도·법령"}], SITE, "2026-11-10T09:00:00+09:00"))
        entries = root.findall(f"{ATOM}entry")
        self.assertEqual([entry.findtext(f"{ATOM}title") for entry in entries], ["C", "A & B"])  # 게시일이 없으면 실린 날로 센다
        self.assertEqual(entries[1].find(f"{ATOM}category").get("term"), "제도·법령")
        self.assertIn("요약 <1>", entries[1].findtext(f"{ATOM}summary"))
        self.assertEqual(_links(entries[1])["related"], "https://x.example/a?b=1&c=2")

    def test_withdrawn_and_undated_items_are_left_out(self):
        entries = self._entries([
            {"id": "c-1", "title": "다", "summary": "요약", "link": "https://eu.example/c", "published": "2026-11-08", "withdrawn": True},
            {"id": "c-2", "title": "라", "summary": "요약", "link": "https://eu.example/d"},
        ])
        self.assertEqual(entries, [])


class RulesFeedTest(unittest.TestCase):
    def test_a_timeline_entry_opens_the_rule_on_this_site(self):
        body = {"regulations": [{"id": "cbam-downstream", "name": "하류제품 확대", "stage": "3자 협상 중", "timeline": [
            {"date": "2026-09-15", "text": "유럽의회가 입장을 채택했습니다.", "source": "유럽의회", "link": "https://ep.example/x"},
        ]}]}
        root = ET.fromstring(feed.rules(body, SITE, "2026-11-11T06:00:00+09:00"))
        entry = root.find(f"{ATOM}entry")
        links = _links(entry)
        self.assertEqual(links["alternate"], f"{SITE}#rules-cbam-downstream")
        self.assertEqual(links["related"], "https://ep.example/x")
        self.assertTrue(entry.find(f"{ATOM}id").text.startswith(f"{SITE}#rules-cbam-downstream/"))

    def test_press_reports_are_marked(self):
        body = {"regulations": [{"id": "r1", "name": "규제 하나", "stage": "협상 중", "timeline": [
            {"date": "2026-10-20", "text": "첫 회의가 열렸다는 보도가 있었습니다.", "source": "매체", "link": "https://m.example/1", "basis": "press"},
            {"date": "2026-09-15", "text": "의회가 입장을 채택했습니다.", "source": "의회", "link": "https://p.example/2", "basis": "stored"}]}]}
        entries = ET.fromstring(feed.rules(body, SITE, "2026-11-10T09:00:00+09:00")).findall(f"{ATOM}entry")
        self.assertEqual(len(entries), 2)
        self.assertTrue(entries[0].findtext(f"{ATOM}summary").startswith("[언론 보도] "))
        self.assertFalse(entries[1].findtext(f"{ATOM}summary").startswith("[언론 보도]"))


if __name__ == "__main__":
    unittest.main()
