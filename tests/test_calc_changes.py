"""법령의 표가 바뀌어 품목 자료가 달라졌을 때 견주는 도구(tools/calc/changes.py)."""
import copy
import json
import os
import pathlib
import tempfile
import unittest

from tools.calc import changes
from tools.common.jsonio import read_json


class ChangesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.body = read_json(changes.ROOT / changes.TARGET, None)

    def good(self, body, code):
        return next(good for good in body["goods"] if good["code"] == code)

    def test_the_same_data_has_no_changes(self):
        found = changes.diff(self.body, copy.deepcopy(self.body))
        self.assertEqual(found["goods"], [])
        self.assertEqual((found["summary"]["before"], found["summary"]["after"], found["summary"]["changed"]), (len(self.body["goods"]), len(self.body["goods"]), 0))

    def test_a_changed_default_value_shows_on_every_good_that_uses_the_row(self):
        new = copy.deepcopy(self.body)
        good = self.good(new, "72081000")
        row = new["rows"][good["defaults"][0]["row"]]
        old_total = row["total"]
        row["direct"], row["total"] = round(row["direct"] - 0.1, 3), round(old_total - 0.1, 3)
        found = changes.diff(self.body, new)
        users = [one["code"] for one in self.body["goods"] if any(choice["row"] == good["defaults"][0]["row"] for choice in one["defaults"])]
        self.assertEqual([one["code"] for one in found["goods"]], users)
        self.assertGreater(len(users), 1)
        first = found["goods"][0]
        self.assertEqual(first["kind"], "changed")
        self.assertIn({"what": "기본값(총배출량)", "route": good["defaults"][0]["route"], "period": "", "before": old_total, "after": round(old_total - 0.1, 3)}, first["changes"])
        self.assertEqual(found["summary"]["byWhat"], {"기본값(직접배출량)": len(users), "기본값(총배출량)": len(users)})
        self.assertEqual(found["summary"]["bySector"], {"steel": len(users)})

    def test_benchmarks_are_compared_by_route_and_period(self):
        new = copy.deepcopy(self.body)
        ranged = next(good for good in new["goods"] if any(period == 2 for _, _, period in good["b"]))   # 연도 구간이 둘인 품목
        at = next(index for index, (_, _, period) in enumerate(ranged["b"]) if period == 2)
        before, route = ranged["b"][at][0], ranged["b"][at][1]
        ranged["b"][at][0] = round(before * 0.9, 3)
        plain = self.good(new, "72081000")
        plain["a"].append([0.5, "Z", 0])                                    # 새 생산경로의 값
        found = {good["code"]: good for good in changes.diff(self.body, new)["goods"]}
        self.assertEqual(found[ranged["code"]]["changes"], [{"what": "CBAM 벤치마크 B열", "route": route, "period": "2028~2030년", "before": before, "after": round(before * 0.9, 3)}])
        self.assertEqual(found["72081000"]["changes"], [{"what": "CBAM 벤치마크 A열", "route": "Z", "period": "", "before": None, "after": 0.5}])

    def test_goods_that_appear_or_disappear_and_a_changed_source_table(self):
        new = copy.deepcopy(self.body)
        gone = new["goods"].pop(0)
        new["goods"].append({"code": "99999999", "shown": "9999 99 99", "text": "New good", "sector": "steel", "a": [[1.0, "", 0]], "b": [[1.0, "", 0]],
                             "defaults": [{"row": 0, "route": "", "benchmark": [1.0, 1.0]}]})
        moved = next(good for good in new["goods"] if new["rows"][good["defaults"][0]["row"]]["origin"] == "kr")
        new["rows"][moved["defaults"][0]["row"]]["origin"] = "other"
        found = changes.diff(self.body, new)
        kinds = {good["code"]: good["kind"] for good in found["goods"]}
        self.assertEqual((kinds["99999999"], kinds[gone["code"]]), ("added", "removed"))
        self.assertEqual(found["goods"][-1]["code"], gone["code"])        # 없어진 품목은 끝에 둔다
        self.assertEqual((found["summary"]["added"], found["summary"]["removed"]), (1, 1))
        self.assertIn({"what": "기본값이 온 표", "route": moved["defaults"][0]["route"], "period": "", "before": "대한민국 표", "after": "그 밖의 나라와 영역 표"},
                      next(good for good in found["goods"] if good["code"] == moved["code"])["changes"])

    def test_the_report_and_the_command(self):
        new = copy.deepcopy(self.body)
        self.good(new, "72081000")["b"][0][0] = 1.2
        lines = changes.report(changes.diff(self.body, new))
        self.assertIn("값이 달라진 품목 1개", lines[0])
        self.assertTrue(any("7208 10 00" in line and "1.37 → 1.2" in line for line in lines))
        with tempfile.TemporaryDirectory() as folder:
            before, after, out = (pathlib.Path(folder) / name for name in ("before.json", "after.json", "out.json"))
            before.write_text(json.dumps(self.body), encoding="utf-8")
            after.write_text(json.dumps(new), encoding="utf-8")
            self.assertEqual(changes.main(["--from", str(before), "--to", str(before)]), 0)
            self.assertEqual(changes.main(["--from", str(before), "--to", str(after), "--json", str(out)]), 1)
            written = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual([good["code"] for good in written["goods"]], ["72081000"])
            self.assertEqual(changes.main(["--from", str(pathlib.Path(folder) / "none.json")]), 2)   # 읽지 못하는 자료
            self.assertEqual(changes.main(["--nothing"]), 2)
            self.assertEqual(changes.main(["--from", "--output=x"]), 2)   # '-'로 시작하는 이름은 git에 넘기지 않는다
            self.assertIsNone(changes.load("-HEAD"))

    def test_a_good_that_moves_to_another_default_row_is_named(self):
        new = copy.deepcopy(self.body)
        good = self.good(new, "72081000")
        was = good["defaults"][0]["row"]
        other = next(index for index, row in enumerate(new["rows"]) if index != was and row["shown"] != new["rows"][was]["shown"])
        good["defaults"][0]["row"] = other
        found = changes.diff(self.body, new)
        self.assertEqual([one["code"] for one in found["goods"]], ["72081000"])
        self.assertEqual(found["goods"][0]["changes"][0], {"what": "기본값 행", "route": good["defaults"][0]["route"], "period": "",
                                                           "before": self.body["rows"][was]["shown"], "after": new["rows"][other]["shown"]})

    def test_uneven_lists_and_empty_routes_are_still_compared(self):
        new = copy.deepcopy(self.body)
        good = self.good(new, "72081000")
        good["defaults"][0]["benchmark"].append(0.9)       # 구간이 하나 더 생긴 경우
        good["a"].append([0.7, None, 0])                   # 생산경로가 비어 있는 값
        changed = changes.diff(self.body, new)["goods"][0]["changes"]
        self.assertIn({"what": "기본값으로 신고할 때의 벤치마크", "route": good["defaults"][0]["route"], "period": "3", "before": None, "after": 0.9}, changed)
        self.assertIn({"what": "CBAM 벤치마크 A열", "route": None, "period": "", "before": None, "after": 0.7}, changed)
        self.assertTrue(changes.report(changes.diff(self.body, new)))

    def test_data_of_another_shape_ends_with_its_own_code(self):
        broken = copy.deepcopy(self.body)
        self.good(broken, "72081000")["defaults"][0]["row"] = len(broken["rows"]) + 5   # 없는 행을 가리킨다
        nameless = copy.deepcopy(self.body)
        del nameless["goods"][0]["code"]
        with tempfile.TemporaryDirectory() as folder:
            before = pathlib.Path(folder) / "before.json"
            before.write_text(json.dumps(self.body), encoding="utf-8")
            for name, body in (("broken.json", broken), ("nameless.json", nameless), ("list.json", {"goods": [1, 2]})):
                after = pathlib.Path(folder) / name
                after.write_text(json.dumps(body), encoding="utf-8")
                self.assertEqual(changes.main(["--from", str(before), "--to", str(after)]), 2, name)

    def test_the_stored_data_is_found_from_any_folder(self):
        here = os.getcwd()
        with tempfile.TemporaryDirectory() as folder:
            os.chdir(folder)
            try:
                self.assertEqual(changes.main(["--from", str(changes.ROOT / changes.TARGET)]), 0)   # --to는 저장소의 자료
            finally:
                os.chdir(here)


if __name__ == "__main__":
    unittest.main()
