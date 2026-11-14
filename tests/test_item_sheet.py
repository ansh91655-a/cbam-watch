"""품목 한 장 보기가 잇는 곳 만들기(tools/publish/item_sheet.py)."""
import json
import pathlib
import tempfile
import unittest
from unittest import mock

from tools.common.jsonio import read_json
from tools.publish import handbook, item_sheet

INDEX = {"acts": [
    {"id": "32023R0956", "group": "act", "name": "CBAM 규정", "toc": [
        {"id": "art-2a", "kind": "article", "ko": "제2a조", "titleKo": "소량 면제"},
        {"id": "annex-i", "kind": "annex", "ko": "부속서 I", "titleKo": "제품과 온실가스의 목록"}]},
    {"id": "32025R2620", "group": "act", "name": "무상할당 조정 이행규정", "toc": [{"id": "annex-0", "kind": "annex", "ko": "부속서", "titleKo": ""}]},
]}
BOOK = {"chapters": [{"id": "scope", "title": "대상 품목과 적용 제외", "sections": [{"id": "goods-cn", "title": "부속서 I의 품목과 CN 코드"}, {"id": "direct-only", "title": "직접배출량만 보는 품목"}]}]}
SHEET = {"basis": [{"about": "대상 품목과 온실가스", "act": "32023R0956", "part": "annex-i"}, {"about": "소량 면제", "act": "32023R0956", "part": "art-2a"},
                   {"about": "CBAM 벤치마크", "act": "32025R2620", "part": "annex-0", "when": "priced"}, {"about": "법 전체", "act": "32023R0956"}],
         "read": [{"section": "scope.goods-cn"}, {"section": "scope.direct-only", "when": "direct"}]}


class BuildTest(unittest.TestCase):
    def setUp(self):
        self.known = handbook.known_laws(INDEX)
        self.sections = item_sheet._sections(BOOK)

    def test_names_come_from_the_law_index_and_the_handbook(self):
        self.assertEqual(item_sheet.problems(SHEET, self.known, self.sections), [])
        body = item_sheet.build(SHEET, self.known, self.sections)
        self.assertEqual(body["basis"][0], {"about": "대상 품목과 온실가스", "act": "32023R0956", "part": "annex-i", "label": "CBAM 규정 부속서 I 제품과 온실가스의 목록", "when": ""})
        self.assertEqual([(row["label"], row["when"]) for row in body["basis"][1:]],
                         [("CBAM 규정 제2a조 소량 면제", ""), ("무상할당 조정 이행규정 부속서", "priced"), ("CBAM 규정", "")])   # 조각을 적지 않으면 문서 전체
        self.assertEqual(body["read"], [{"href": "#handbook-scope.goods-cn", "chapter": "대상 품목과 적용 제외", "title": "부속서 I의 품목과 CN 코드", "when": ""},
                                        {"href": "#handbook-scope.direct-only", "chapter": "대상 품목과 적용 제외", "title": "직접배출량만 보는 품목", "when": "direct"}])

    def test_lines_that_point_nowhere_are_reported(self):
        broken = {"basis": [{"about": "", "act": "32023R0956"}, {"about": "없는 문서", "act": "nothing"}, {"about": "없는 조각", "act": "32023R0956", "part": "annex-x"},
                            {"about": "모르는 표시", "act": "32023R0956", "part": "annex-i", "when": "always"}],
                  "read": [{"section": "scope.nothing"}, {"section": "scope.goods-cn", "when": "sometimes"}, "scope.goods-cn"]}
        found = [what for _, what in item_sheet.problems(broken, self.known, self.sections)]
        self.assertEqual(found, ["about이 비어 있음", "규정 원문에 없는 문서: nothing", "규정 원문에 없는 조각: 32023R0956.annex-x", "모르는 when: always",
                                 "해설서에 없는 절: scope.nothing", "모르는 when: sometimes", "해설서에 없는 절: scope.goods-cn"])
        self.assertEqual(item_sheet.problems(None, self.known, self.sections), [("품목 한 장 보기", f"자료({item_sheet.SOURCE})를 읽지 못함")])
        self.assertIn(("품목 한 장 보기", "근거나 해설서의 줄이 하나도 없음"), item_sheet.problems({"basis": [], "read": []}, self.known, self.sections))

    def test_nothing_is_written_when_a_line_points_nowhere(self):
        with tempfile.TemporaryDirectory() as folder:
            root = pathlib.Path(folder)
            (root / "laws").mkdir()
            (root / "laws" / "index.json").write_text(json.dumps(INDEX, ensure_ascii=False), encoding="utf-8")
            (root / "handbook.json").write_text(json.dumps(BOOK, ensure_ascii=False), encoding="utf-8")
            with mock.patch.object(item_sheet, "read_json", side_effect=lambda path, fallback: SHEET if path == item_sheet.SOURCE else read_json(path, fallback)):
                self.assertEqual(item_sheet.write(root), (6, []))
            self.assertEqual(len(read_json(root / "sheet.json", {})["basis"]), 4)
            (root / "sheet.json").unlink()
            count, found = item_sheet.write(root)   # 저장소의 자료는 이 작은 사이트에 없는 문서와 절을 가리킨다
            self.assertEqual(count, 0)
            self.assertTrue(found)
            self.assertFalse((root / "sheet.json").exists())


class RepositoryTest(unittest.TestCase):
    def test_the_source_file_names_places_and_no_facts(self):
        sheet = read_json(item_sheet.SOURCE, {})
        sections = item_sheet._sections(read_json(handbook.SOURCE, {}))
        for row in sheet["basis"]:   # 무엇의 근거인지를 적는 이름과 가리키는 곳만 둔다(조문의 이름과 글은 사이트의 자료에서 온다)
            self.assertLessEqual(set(row), {"about", "act", "part", "when"})
            self.assertLessEqual(len(row["about"]), 20, row["about"])
            self.assertIn(row.get("when", ""), item_sheet.WHEN)
        for row in sheet["read"]:
            self.assertLessEqual(set(row), {"section", "when"})
            self.assertIn(row["section"], sections)    # 해설서의 절은 저장소의 글에도 있다(규정 원문의 조각은 사이트를 만들 때 본다)
            self.assertIn(row.get("when", ""), item_sheet.WHEN)
        # 값이 있는 품목과 없는 품목, 직접배출량만 넣는 품목과 간접배출량도 넣는 품목 모두에 읽을 곳이 있다
        for flag in ("direct", "both", "priced", "unpriced"):
            self.assertTrue([row for row in sheet["read"] if row.get("when") == flag], flag)


if __name__ == "__main__":
    unittest.main()
