"""부문별 모아 보기의 자료 만들기(tools/publish/sectors.py)."""
import json
import pathlib
import tempfile
import unittest

from tools.common.jsonio import read_json
from tools.publish import sectors

BOOK = {"common": ["32023R0956", "guide-3"], "sectors": [
    {"key": "steel", "name": "철강", "cn": ["steel"], "calc": "steel", "docs": ["guide-5d"], "words": ["철강"], "proposed": ["steel", "combined"]},
    {"key": "electricity", "name": "전력", "cn": ["electricity"], "calc": "", "docs": ["guide-5f", "fact-electricity"], "words": ["전력"], "except": ["전력투구"], "proposed": []},
]}
INDEX = {"acts": [
    {"id": "32023R0956", "group": "act", "name": "CBAM 규정", "toc": []},
    {"id": "guide-3", "group": "guide", "name": "가이던스 3", "toc": []},
    {"id": "guide-5d", "group": "guide", "name": "가이던스 5d: 철강", "official": "Guidance document 5d", "pages": 65, "received": "2026-11-10", "toc": [
        {"id": "cover", "kind": "cover", "level": 0, "ko": "표지", "title": ""},
        {"id": "sec-1", "kind": "section", "level": 1, "ko": "1", "title": "PREFACE", "titleKo": "서문"},
        {"id": "sec-1-1", "kind": "section", "level": 2, "ko": "1.1", "title": "Deep", "titleKo": "깊은 절"},
        {"id": "sec-2", "kind": "section", "level": 1, "ko": "2", "title": "GOODS", "titleKo": ""}]},
    {"id": "guide-5f", "group": "guide", "name": "가이던스 5f: 전력", "toc": []},
    {"id": "fact-electricity", "group": "paper", "name": "전력 생산자 안내 자료", "remark": "전환기간용 자료입니다.", "toc": []},
]}
CN = {"asOf": "2026-11-11", "law": {"name": "규정 (EU) 2023/956 부속서 I·II", "url": "https://example.org/law"}, "proposalEnacted": False,
      "proposal": {"name": "하류제품 확대 개정안의 부속서"},
      "current": [
          {"sector": "steel", "codes": ["72"], "shown": "72", "ex": False, "text": "Iron and steel", "gases": ["co2"], "directOnly": True},
          {"sector": "steel", "codes": ["26011200"], "shown": "2601 12 00", "ex": False, "text": "Agglomerated iron ores", "gases": ["co2"], "directOnly": False},
          {"sector": "steel", "codes": ["73269098"], "shown": "ex 7326 90 98", "ex": True, "text": "Other articles", "gases": ["co2"], "directOnly": True},
          {"sector": "electricity", "codes": ["27160000"], "shown": "2716 00 00", "ex": False, "text": "Electrical energy", "gases": ["co2"], "directOnly": True},
          {"sector": "cement", "codes": ["25231000"], "shown": "2523 10 00", "ex": False, "text": "Cement clinkers", "gases": ["co2"], "directOnly": False}],
      "proposed": [{"sector": "steel", "codes": ["7315"]}, {"sector": "steel", "codes": ["7316"]}, {"sector": "combined", "codes": ["8544"]}]}
CALC = {"markups": [{"sectors": ["cement", "steel"], "values": {"2026": 10, "2027": 20, "2028": 30}}],
        "goods": [["25231000", "Cement clinkers", "cement", [], [], []], ["26011200", "Agglomerated iron ores", "steel", [], [], []], ["72081000", "Flat-rolled", "steel", [], [], []]]}
PDFS = {"docs": {"guide-5d": {"pages": 65}}}
ITEMS = [
    {"id": "a", "published": "2026-10-01", "title": "철강 세이프가드 개편", "summary": "", "topics": []},
    {"id": "b", "published": "2026-11-01", "title": "설명회", "summary": "철강과 알루미늄 수출기업 대상입니다.", "topics": [], "brief": True, "link": "https://example.org/b"},
    {"id": "c", "published": "2026-11-05", "title": "내린 소식", "summary": "철강", "topics": [], "withdrawn": True},
    {"id": "d", "published": "2026-09-01", "title": "전력 수입 가이던스", "summary": "", "topics": []},
    {"id": "e", "published": "2026-08-01", "title": "다른 소식", "summary": "", "topics": ["철강 품목"]},
    {"id": "f", "published": "2026-11-09", "title": "수출 지원에 전력투구", "summary": "", "topics": []},
]


def site(folder):
    root = pathlib.Path(folder)
    (root / "laws").mkdir()
    for name, body in (("laws/index.json", INDEX), ("laws/pdf.json", PDFS), ("cn.json", CN), ("calc.json", CALC)):
        (root / name).write_text(json.dumps(body, ensure_ascii=False), encoding="utf-8")
    return root


class BuildTest(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = site(self.folder.name)
        self.body = sectors.build(BOOK, self.root, ITEMS)
        self.steel, self.power = self.body["sectors"]

    def test_goods_come_from_the_annex_list_with_their_scope(self):
        goods = self.steel["goods"]
        self.assertEqual([row["shown"] for row in goods["rows"]], ["72", "2601 12 00", "ex 7326 90 98"])
        self.assertEqual((goods["gases"], goods["directOnly"], goods["both"]), (["co2"], 2, 1))
        # 그 줄의 코드로 시작하는 품목 가운데 기본값·벤치마크가 정해진 첫 품목으로 비용 추정을 잇는다. 없으면 잇지 않는다
        self.assertEqual([row["calc"] for row in goods["rows"]], ["72081000", "26011200", ""])
        self.assertEqual((self.body["asOf"], self.body["law"]["url"]), ("2026-11-11", "https://example.org/law"))

    def test_documents_carry_their_top_sections_and_whether_a_pdf_view_exists(self):
        doc = self.steel["docs"][0]
        self.assertEqual((doc["id"], doc["name"], doc["pages"], doc["pdf"]), ("guide-5d", "가이던스 5d: 철강", 65, True))
        self.assertEqual([part["id"] for part in doc["sections"]], ["sec-1", "sec-2"])   # 큰 절만. 표지와 깊은 절은 싣지 않는다
        self.assertEqual([(doc["id"], doc["pdf"], doc["remark"]) for doc in self.power["docs"]], [("guide-5f", False, ""), ("fact-electricity", False, "전환기간용 자료입니다.")])
        self.assertEqual(self.body["common"], [{"id": "32023R0956", "name": "CBAM 규정", "group": "act"}, {"id": "guide-3", "name": "가이던스 3", "group": "guide"}])

    def test_priced_goods_and_markups_come_from_the_estimator_data(self):
        self.assertEqual(self.steel["calc"], {"goods": 2, "first": "26011200", "markups": {"2026": 10, "2027": 20, "2028": 30}})
        self.assertIsNone(self.power["calc"])     # 비용 추정에 싣지 않는 부문

    def test_proposed_goods_are_counted_until_the_proposal_becomes_law(self):
        self.assertEqual(self.steel["proposed"], {"own": 2, "combined": 1, "name": "하류제품 확대 개정안의 부속서"})
        self.assertIsNone(self.power["proposed"])
        (self.root / "cn.json").write_text(json.dumps({**CN, "proposalEnacted": True}, ensure_ascii=False), encoding="utf-8")
        self.assertIsNone(sectors.build(BOOK, self.root, ITEMS)["sectors"][0]["proposed"])

    def test_news_is_picked_by_the_sector_words_newest_first(self):
        self.assertEqual([item["id"] for item in self.steel["items"]], ["b", "a", "e"])     # 내린 소식은 싣지 않는다. 다룬 내용(topics)에 나온 것도 고른다
        self.assertEqual(self.steel["items"][0], {"id": "b", "title": "설명회", "date": "2026-11-01", "link": "https://example.org/b"})   # 제목만 실은 소식은 원문으로
        self.assertEqual((self.steel["itemCount"], self.power["itemCount"]), (3, 1))
        self.assertEqual([item["id"] for item in self.power["items"]], ["d"])                # 그 낱말이 든 다른 말(전력투구)은 세지 않는다
        both = [{"id": "g", "published": "2026-11-10", "title": "전력투구한 끝에 전력 수입 신고", "summary": "", "topics": []}]
        self.assertEqual(sectors.build(BOOK, self.root, both)["sectors"][1]["itemCount"], 1)  # 다른 말을 지운 뒤에도 그 낱말이 남으면 고른다
        many = [{"id": f"n{number}", "published": f"2026-01-{number + 1:02d}", "title": "철강", "summary": ""} for number in range(sectors.ITEMS + 4)]
        found = sectors.build(BOOK, self.root, many)["sectors"][0]
        self.assertEqual((len(found["items"]), found["itemCount"]), (sectors.ITEMS, sectors.ITEMS + 4))


class ProblemsTest(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = site(self.folder.name)

    def test_a_good_book_has_no_problems(self):
        self.assertEqual(sectors.problems(BOOK, self.root), [])

    def test_names_that_point_nowhere_are_reported(self):
        broken = {"common": ["nothing"], "sectors": [
            {"key": "steel", "name": "철강", "cn": ["iron"], "calc": "metal", "docs": ["guide-9"], "words": ["철강"], "proposed": ["wires"]},
            {"key": "steel", "name": "", "cn": [], "words": []}]}
        found = [problem for _, problem in sectors.problems(broken, self.root)]
        for word in ("key가 겹침", "품목 목록에 없는 부문: ['iron']", "인증서 비용 추정의 자료에 없는 부문: metal", "규정 원문에 없는 문서: guide-9",
                     "개정안의 품목 목록에 없는 부문: wires", "name이나 words가 비어 있음", "품목 목록에 없는 부문: (없음)", "규정 원문에 없는 문서(common): nothing"):
            self.assertTrue(any(word in problem for problem in found), word)
        self.assertEqual(sectors.problems(None, self.root)[0][1], f"자료({sectors.SOURCE})를 읽지 못함")


class RepositoryTest(unittest.TestCase):
    def test_the_source_file_names_six_sectors_and_no_facts(self):
        book = read_json(sectors.SOURCE, {})
        self.assertEqual([sector["key"] for sector in book["sectors"]], ["steel", "aluminium", "cement", "fertilisers", "hydrogen", "electricity"])
        for sector in book["sectors"]:   # 사실을 적는 글은 두지 않는다(화면의 수와 글은 사이트의 자료에서 만든다)
            self.assertEqual(sorted(sector), ["calc", "cn", "docs", "except", "key", "name", "proposed", "words"], sector["key"])
            self.assertFalse([word for word in sector["except"] if not any(own in word for own in sector["words"])], sector["key"])   # 지울 말에는 그 부문의 낱말이 들어 있다


if __name__ == "__main__":
    unittest.main()
