"""소식, 의무 일정, 용어집에 적힌 법령과 조문을 규정 원문으로 잇기(tools/publish/crossrefs.py)."""
import json
import pathlib
import tempfile
import unittest

from tools.publish import crossrefs


def part(key, kind, ko, title=""):
    return {"id": key, "kind": kind, "ko": ko, "titleKo": title}


INDEX = {"acts": [
    {"id": "32023R0956", "group": "act", "name": "CBAM 규정", "official": "Regulation (EU) 2023/956", "toc": [
        part("art-2a", "article", "제2a조", "소량 면제"), part("art-6", "article", "제6조", "CBAM 신고서"), part("art-7", "article", "제7조"), part("art-8", "article", "제8조"),
        part("art-9", "article", "제9조"), part("art-22", "article", "제22조", "CBAM 인증서의 제출"), part("annex-i", "annex", "부속서 I"), part("annex-ii", "annex", "부속서 II")]},
    {"id": "32025R2621", "group": "act", "name": "기본값 이행규정", "official": "Commission Implementing Regulation (EU) 2025/2621", "toc": [
        part("art-1", "article", "제1조"), part("annex-i", "annex", "부속서 I"), part("annex-iv", "annex", "부속서 IV")]},
    {"id": "32026R1740", "group": "act", "name": "기본값 이행규정의 정정 규정", "official": "Commission Implementing Regulation (EU) 2026/1740", "toc": [part("art-1", "article", "제1조")]},
    {"id": "32025R0486", "group": "act", "name": "승인된 CBAM 신고인 지위 이행규정", "official": "Commission Implementing Regulation (EU) 2025/486", "toc": [part("art-21", "article", "제21조")]},
    {"id": "32025R2546", "group": "act", "name": "내재배출량 검증 원칙 이행규정", "official": "Commission Implementing Regulation (EU) 2025/2546", "toc": [part("art-1", "article", "제1조")]},
    {"id": "guide-3", "group": "guide", "name": "가이던스 3", "official": "Guidance document 3", "toc": [part("sec-1", "section", "1")]},
]}
BASE, VALUES, FIX = "32023R0956", "32025R2621", "32026R1740"


class FoundTest(unittest.TestCase):
    def setUp(self):
        self.known = crossrefs.book(INDEX)

    def found(self, text, bare=False):
        return crossrefs.found(text, self.known, bare)[0]

    def test_articles_right_after_an_act_belong_to_that_act(self):
        self.assertEqual(self.found("CBAM 규정 제6조(1), 제22조(1)"), [(BASE, "art-6"), (BASE, "art-22")])
        self.assertEqual(self.found("CBAM 규정 제2a조(3)에 따라 EU 집행위원회는 평가해야 합니다."), [(BASE, "art-2a")])
        self.assertEqual(self.found("CBAM 규정 제7조(7)·제8조(3)"), [(BASE, "art-7"), (BASE, "art-8")])
        self.assertEqual(self.found("CBAM 규정 제6조~제9조"), [(BASE, "art-6"), (BASE, "art-7"), (BASE, "art-8"), (BASE, "art-9")])  # 사이의 조도 잇는다
        self.assertEqual(self.found("CBAM 규정 부속서 I·II"), [(BASE, "annex-i"), (BASE, "annex-ii")])

    def test_acts_are_known_by_number_and_by_name(self):
        self.assertEqual(self.found("이행규정(EU) 2025/2621의 부속서 I과 부속서 IV를 바로잡는 이행규정(EU) 2026/1740이 관보에 실렸습니다."),
                         [(VALUES, "annex-i"), (VALUES, "annex-iv"), (FIX, "")])
        self.assertEqual(self.found("기본값 이행규정의 부속서 I·IV 정정"), [(VALUES, "annex-i"), (VALUES, "annex-iv")])
        self.assertEqual(self.found("기본값 이행규정의 정정 규정 제1조"), [(FIX, "art-1")])                      # 긴 이름이 먼저다
        self.assertEqual(self.found("승인된 CBAM 신고인 지위 이행규정 (EU) 2025/486 제21조(10)(이행규정 (EU) 2025/2549로 추가)", bare=True), [("32025R0486", "art-21")])
        self.assertEqual(self.found("CBAM 규정 (EU) 2023/956의 취소를 구한 소송"), [(BASE, "")])                     # 이름과 번호가 이어지면 한 번만

    def test_a_bare_name_links_only_in_a_basis_field(self):
        self.assertEqual(self.found("CBAM 규정은 2026년부터 확정기간에 들어갑니다."), [])    # 거의 모든 소식에 나오는 말이라 잇지 않는다
        self.assertEqual(self.found("규정(EU) 2023/956을 개정하는 제안"), [(BASE, "")])     # 번호가 적히면 문서로 잇는다
        self.assertEqual(self.found("검증 원칙 이행규정 · G1 p.3", bare=True), [("32025R2546", "")])
        self.assertEqual(self.found("CBAM 규정", bare=True), [(BASE, "")])

    def test_other_laws_and_loose_articles_are_left_alone(self):
        self.assertEqual(self.found("EU 기능조약 제192조(1)을 법적 근거로 삼은 것이 옳다고 판단했습니다."), [])
        self.assertEqual(self.found("CBAM 규정과 개정 규정을 EEA 협정의 부속서 XX(환경)에 넣는 결정"), [])
        self.assertEqual(self.found("제1조의 (7)과 (10)은 2026년 1월 1일부터 적용됩니다."), [])           # 어느 법령의 조인지 적히지 않았다
        self.assertEqual(self.found("영국 CBAM 규정 제6조", bare=True), [])
        self.assertEqual(self.found("결정 (EU) 2025/2468", bare=True), [])                               # 사이트가 싣지 않는 법령
        self.assertEqual(self.found("CBAM 규정 개정안 제27a조"), [])                                      # 법령 바로 뒤에 이어 적힌 것만
        self.assertEqual(self.found("가이던스 3 제1조", bare=True), [])                                   # 법령만 잇는다

    def test_parts_missing_from_the_text_are_reported_not_linked(self):
        self.assertEqual(crossrefs.found("CBAM 규정 제6조, 제99조, 부속서 V", self.known, True), ([(BASE, "art-6")], ["CBAM 규정 제99조", "CBAM 규정 부속서 V"]))
        self.assertEqual(crossrefs.found("CBAM 규정 전문(17)", self.known, True), ([], []))   # 통합본에는 전문이 없다. 알리지 않는다

    def test_labels_name_the_act_and_the_part(self):
        self.assertEqual(crossrefs.label(self.known, BASE, "art-6"), "CBAM 규정 제6조 CBAM 신고서")
        self.assertEqual(crossrefs.label(self.known, VALUES, "annex-iv"), "기본값 이행규정 부속서 IV")
        self.assertEqual(crossrefs.label(self.known, FIX, ""), "기본값 이행규정의 정정 규정")


class BuildTest(unittest.TestCase):
    ITEMS = [
        {"id": "new", "published": "2026-11-10", "title": "임계값 평가", "summary": "CBAM 규정 제2a조(3)에 따라 평가했습니다.", "impact": ""},
        {"id": "old", "published": "2025-12-31", "title": "이행규정(EU) 2025/2621 관보 게재", "summary": "", "impact": "", "brief": True, "link": "https://example.org/act"},
        {"id": "gone", "published": "2026-01-01", "title": "CBAM 규정 제6조", "summary": "", "impact": "", "withdrawn": True},
        {"id": "plain", "published": "2026-02-01", "title": "CBAM 규정 안내", "summary": "CBAM 규정은 중요합니다.", "impact": ""},
    ]
    DUTIES = [
        {"id": "review", "date": "2026-04-30", "title": "임계값의 연례 평가", "basis": "CBAM 규정 제2a조(3)", "repeat": True},
        {"id": "review-2027", "date": "2027-04-30", "title": "임계값의 연례 평가", "basis": "CBAM 규정 제2a조(3)", "repeat": True},
        {"id": "review-2028", "date": "2028-04-30", "title": "임계값의 연례 평가", "basis": "CBAM 규정 제2a조(3)", "repeat": True},
        {"id": "declare", "date": "2027-09-30", "title": "첫 CBAM 신고서 제출", "basis": "CBAM 규정 제6조(1), 제22조(1)"},
        {"id": "uk", "date": "2027-01-01", "title": "영국 CBAM 시행", "basis": "Finance Act 2026 제143조"},
        {"id": "wrong", "date": "2027-01-01", "title": "잘못 적은 근거", "basis": "CBAM 규정 제99조"},
    ]
    TERMS = [{"en": "CBAM declaration", "ko": "CBAM 신고서", "article": "CBAM 규정 제6조"}, {"en": "Guidance", "ko": "가이던스", "article": "G1 p.3"}]

    def setUp(self):
        self.body, self.problems = crossrefs.build(INDEX, self.ITEMS, self.DUTIES, self.TERMS, "2026-11-13")

    def test_each_source_gets_its_links(self):
        self.assertEqual(self.body["items"], {"new": [{"act": BASE, "part": "art-2a", "label": "CBAM 규정 제2a조 소량 면제"}],
                                              "old": [{"act": VALUES, "part": "", "label": "기본값 이행규정"}]})
        self.assertEqual(sorted(self.body["duties"]), ["declare", "review", "review-2027", "review-2028"])
        self.assertEqual([ref["part"] for ref in self.body["duties"]["declare"]], ["art-6", "art-22"])
        self.assertEqual(list(self.body["terms"]), ["CBAM declaration"])

    def test_each_part_lists_what_points_to_it(self):
        laws = self.body["laws"]
        self.assertEqual(laws[BASE]["art-2a"]["items"], [{"id": "new", "title": "임계값 평가", "date": "2026-11-10"}])
        self.assertEqual([duty["id"] for duty in laws[BASE]["art-2a"]["duties"]], ["review-2027"])   # 해마다 돌아오는 의무는 다가오는 것 하나만
        self.assertEqual(laws[BASE]["art-6"], {"items": [], "duties": [{"id": "declare", "title": "첫 CBAM 신고서 제출", "date": "2027-09-30"}],
                                               "terms": [{"en": "CBAM declaration", "ko": "CBAM 신고서"}], "more": 0})
        self.assertEqual(laws[VALUES][""]["items"], [{"id": "old", "title": "이행규정(EU) 2025/2621 관보 게재", "date": "2025-12-31", "link": "https://example.org/act"}])
        self.assertNotIn("art-99", laws[BASE])

    def test_fields_of_an_item_are_read_apart(self):
        # 제목 끝의 법령과 요약 첫머리의 조를 한데 잇지 않는다
        items = [{"id": "name", "published": "2026-11-11", "title": "개정 대상은 CBAM 규정", "summary": "제6조에 따른 신고서의 서식도 함께 바뀝니다.", "impact": ""},
                 {"id": "number", "published": "2026-11-12", "title": "개정 대상은 규정(EU) 2023/956", "summary": "제6조에 따른 신고서의 서식도 함께 바뀝니다.", "impact": ""}]
        found = crossrefs.build(INDEX, items, [], [], "2026-11-13")[0]["items"]
        self.assertEqual(found, {"number": [{"act": BASE, "part": "", "label": "CBAM 규정"}]})   # 번호로 적은 법령만 잇고, 다른 칸의 제6조는 붙이지 않는다

    def test_a_basis_naming_a_missing_part_is_reported(self):
        self.assertEqual(self.problems, [("의무 wrong", "근거에 적힌 조각이 사이트의 규정 원문에 없음: CBAM 규정 제99조")])

    def test_long_lists_of_news_are_capped(self):
        many = [{"id": f"n{number}", "published": f"2026-01-{number + 1:02d}", "title": "규정(EU) 2023/956", "summary": "", "impact": ""} for number in range(crossrefs.ITEMS_PER_PART + 3)]
        row = crossrefs.build(INDEX, many, [], [], "2026-11-13")[0]["laws"][BASE][""]
        self.assertEqual((len(row["items"]), row["more"], row["items"][0]["id"]), (crossrefs.ITEMS_PER_PART, 3, f"n{crossrefs.ITEMS_PER_PART + 2}"))   # 새 것부터

    def test_the_file_is_written_from_the_built_laws_index(self):
        with tempfile.TemporaryDirectory() as folder:
            (pathlib.Path(folder) / "laws").mkdir()
            (pathlib.Path(folder) / "laws" / "index.json").write_text(json.dumps(INDEX), encoding="utf-8")
            counts, problems = crossrefs.write(folder, self.ITEMS, self.DUTIES, self.TERMS, "2026-11-13")
            written = json.loads((pathlib.Path(folder) / "refs.json").read_text(encoding="utf-8"))
        self.assertEqual((counts, len(problems)), ({"items": 2, "duties": 4, "terms": 1, "handbook": 0}, 1))
        self.assertEqual(sorted(written), ["duties", "items", "laws", "read", "terms"])
        self.assertEqual(written["read"], {"terms": {}, "rules": {}})   # 해설서가 없으면 돌아가는 길도 없다


class HandbookTest(unittest.TestCase):
    """해설서로 돌아가는 길: 해설서의 절이 스스로 적어 둔 근거, 풀이한 용어, 관련 화면을 뒤집는다."""

    BOOK = {"chapters": [
        {"id": "cycle", "title": "한 해의 일정", "sections": [
            {"id": "declaration", "title": "CBAM 신고서의 기한과 내용", "terms": [{"ko": "CBAM 신고서", "en": "CBAM declaration", "text": "풀이입니다."}],
             "basis": [{"act": BASE, "part": "art-6", "label": "CBAM 규정 제6조 CBAM 신고서"}, {"act": BASE, "part": "art-6", "label": "CBAM 규정 제6조 CBAM 신고서"},
                       {"label": "EU 배출권거래제 지침", "url": "https://example.org/ets"}],
             "see": [{"href": "#calendar", "text": "일정"}, {"href": "#rules-ir-declarations", "text": "신고서 이행규정(안)"}]},
            {"id": "surrender", "title": "인증서 제출과 분기 말 보유 의무", "basis": [{"act": BASE, "part": "art-22", "label": "CBAM 규정 제22조"}, {"act": BASE, "part": "art-6", "label": "CBAM 규정 제6조"}],
             "see": [{"href": "#rules-ir-declarations", "text": "신고서 이행규정(안)"}, {"href": "#rules-eu-law", "text": "규제 묶음"}]}]},
        {"id": "defaults", "title": "기본값과 마크업", "sections": [
            {"id": "tables", "title": "기본값을 찾는 표", "terms": [{"ko": "기본값", "en": "Default Value", "text": "풀이입니다."}],
             "basis": [{"act": "guide-3", "part": "sec-1", "label": "가이던스 3 1"}, {"act": VALUES, "part": "", "label": "기본값 이행규정"}], "see": []}]},
    ]}

    def setUp(self):
        self.body, _ = crossrefs.build(INDEX, [], [], [{"en": "CBAM declaration", "ko": "CBAM 신고서", "article": "CBAM 규정 제6조"}], "2026-11-13", self.BOOK, {"ir-declarations"})

    def test_a_part_lists_the_sections_that_rest_on_it(self):
        laws = self.body["laws"]
        here = {"href": "#handbook-cycle.declaration", "title": "CBAM 신고서의 기한과 내용", "chapter": "한 해의 일정"}
        there = {"href": "#handbook-cycle.surrender", "title": "인증서 제출과 분기 말 보유 의무", "chapter": "한 해의 일정"}
        self.assertEqual(laws[BASE]["art-6"]["handbook"], [here, there])        # 한 절이 같은 조를 두 번 들어도 한 번만. 책의 차례대로
        self.assertEqual(laws[BASE]["art-6"]["terms"], [{"en": "CBAM declaration", "ko": "CBAM 신고서"}])   # 다른 것(용어)과 함께 실린다
        self.assertEqual(laws[BASE]["art-22"], {"items": [], "duties": [], "terms": [], "handbook": [there], "more": 0})
        # 가이던스의 절과 문서 전체를 근거로 든 것도 잇는다. 사이트 밖의 근거(주소만 있는 것)는 잇지 않는다
        self.assertEqual([one["href"] for one in laws["guide-3"]["sec-1"]["handbook"]], ["#handbook-defaults.tables"])
        self.assertEqual([one["href"] for one in laws[VALUES][""]["handbook"]], ["#handbook-defaults.tables"])

    def test_terms_and_rules_lead_back_to_their_sections(self):
        read = self.body["read"]
        self.assertEqual(read["terms"], {"cbam declaration": {"href": "#handbook-cycle.declaration", "title": "CBAM 신고서의 기한과 내용", "chapter": "한 해의 일정"},
                                         "default value": {"href": "#handbook-defaults.tables", "title": "기본값을 찾는 표", "chapter": "기본값과 마크업"}})   # 영문 표기의 대소문자는 가리지 않는다
        # 관련 화면으로 그 규제를 가리킨 절들. 규제가 아닌 주소(규제 묶음, 다른 화면)는 싣지 않는다
        self.assertEqual({rule: [one["href"] for one in rows] for rule, rows in read["rules"].items()},
                         {"ir-declarations": ["#handbook-cycle.declaration", "#handbook-cycle.surrender"]})

    def test_a_chapter_on_another_scheme_does_not_answer_for_glossary_terms(self):
        # 다른 제도를 다루는 장(scope)의 용어 풀이는 용어집의 용어와 잇지 않는다(용어집은 EU CBAM의 용어다). 근거 조각과 규제로 돌아가는 길은 그대로 싣는다
        other = {"id": "uk", "title": "영국 CBAM", "scope": "uk", "sections": [
            {"id": "returns", "title": "회계기간, 신고, 납부", "terms": [{"ko": "기본값", "en": "default value", "text": "영국의 풀이입니다."}, {"ko": "회계기간", "en": "accounting period", "text": "풀이입니다."}],
             "basis": [{"label": "2026년 재정법 부칙 17", "url": "https://example.org/sch17", "parts": ["제6항"]}], "see": [{"href": "#rules-ir-declarations", "text": "규제"}]}]}
        body, _ = crossrefs.build(INDEX, [], [], [], "2026-11-13", {"chapters": [other] + self.BOOK["chapters"]}, {"ir-declarations"})
        self.assertEqual(sorted(body["read"]["terms"]), ["cbam declaration", "default value"])
        self.assertEqual(body["read"]["terms"]["default value"]["href"], "#handbook-defaults.tables")
        self.assertEqual(body["read"]["rules"]["ir-declarations"][0]["href"], "#handbook-uk.returns")

    def test_without_the_rule_list_every_rule_address_is_kept(self):
        body, _ = crossrefs.build(INDEX, [], [], [], "2026-11-13", self.BOOK)
        self.assertEqual(sorted(body["read"]["rules"]), ["eu-law", "ir-declarations"])

    def test_the_count_tells_how_many_parts_lead_back(self):
        with tempfile.TemporaryDirectory() as folder:
            (pathlib.Path(folder) / "laws").mkdir()
            (pathlib.Path(folder) / "laws" / "index.json").write_text(json.dumps(INDEX), encoding="utf-8")
            (pathlib.Path(folder) / "handbook.json").write_text(json.dumps(self.BOOK, ensure_ascii=False), encoding="utf-8")
            counts, _ = crossrefs.write(folder, [], [], [], "2026-11-13", {"ir-declarations"})
        self.assertEqual(counts["handbook"], 4)


class RepositoryTest(unittest.TestCase):
    def test_every_basis_in_the_repository_points_to_a_part_that_exists(self):
        self.assertEqual(crossrefs.source_problems("2026-11-13"), [])


if __name__ == "__main__":
    unittest.main()
