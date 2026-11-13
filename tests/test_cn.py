"""품목 코드 조회: 법령 부속서를 읽는 것과 코드를 견주는 셈."""
import datetime
import json
import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest

from tools.cn import annex

SAMPLE = """ANNEX I
List of goods and greenhouse gases
Cement
CN code
Greenhouse gas
►M1 ex 2507 00 80 – Other kaolinic clays except non-calcined kaolinic clays ◄
Carbon dioxide
2523 10 00 – Cement clinkers
Carbon dioxide
Fertilisers
CN code
Greenhouse gas
3105 – Mineral or chemical fertilisers containing two or three of the fertilising elements
Except: 3105 60 00 – Mineral or chemical fertilisers containing the two fertilising elements phosphorus and potassium
Carbon dioxide and nitrous oxide
Iron and steel
CN code
Greenhouse gas
72 – Iron and steel
Except:
7202 2 – Ferro-silicon
7202 99 – Other:
7202 99 10 – Ferro-phosphorus
7204 – Ferrous waste and scrap; remelting scrap ingots and steel
Carbon dioxide
7318 – Screws, bolts, nuts
Carbon dioxide
‘[Combined metal products
CN code
Greenhouse gas
ex- 8302 42 00 – Other base metal mountings, containing steel or aluminium
Carbon dioxide
ex 8704 31– Motor vehicles, of a gross vehicle weight not exceeding 5 tonnes
Carbon dioxide
ANNEX II
Aluminium
7601 – Unwrought aluminium
Carbon dioxide and perfluorocarbons
""".split("\n")


class AnnexTest(unittest.TestCase):
    def setUp(self):
        self.entries = annex.tables(annex.between(SAMPLE, "ANNEX I", "ANNEX II"))

    def test_entries_carry_sector_codes_gases_and_the_ex_mark(self):
        shown = [(entry["sector"], entry["shown"], entry["ex"], entry["gases"]) for entry in self.entries]
        self.assertEqual(shown[0], ("cement", "ex 2507 00 80", True, ["co2"]))
        self.assertEqual(shown[1], ("cement", "2523 10 00", False, ["co2"]))
        self.assertEqual(shown[2], ("fertilisers", "3105", False, ["co2", "n2o"]))
        self.assertEqual(self.entries[0]["text"], "Other kaolinic clays except non-calcined kaolinic clays")
        self.assertEqual([entry["shown"] for entry in self.entries if entry["sector"] == "combined"], ["ex 8302 42 00", "ex 8704 31"])
        self.assertNotIn("7601", [code for entry in self.entries for code in entry["codes"]])  # 다음 부속서는 읽지 않는다

    def test_exceptions_belong_to_the_entry_above_them(self):
        steel = next(entry for entry in self.entries if entry["codes"] == ["72"])
        self.assertEqual([item["codes"][0] for item in steel["except"]], ["72022", "720299", "72029910", "7204"])
        fertiliser = next(entry for entry in self.entries if entry["codes"] == ["3105"])
        self.assertEqual(fertiliser["except"][0]["codes"], ["31056000"])
        self.assertEqual(next(entry for entry in self.entries if entry["codes"] == ["7318"])["except"], [])

    def test_a_line_may_name_several_codes(self):
        found = annex.entry_of("7202 21 00, 7202 29 – Ferro-silicon")
        self.assertEqual(found["codes"], ["72022100", "720229"])
        self.assertIsNone(annex.entry_of("Whereas 2023 was a year – of change"))


@unittest.skipUnless(shutil.which("node"), "node가 없으면 화면의 셈은 시험하지 않는다")
class MatchTest(unittest.TestCase):
    def states(self, queries):
        entries = annex.tables(annex.between(SAMPLE, "ANNEX I", "ANNEX II"))
        script = ("import('./site/js/cn/match.js').then((m) => { const e = JSON.parse(process.argv[1]); const q = JSON.parse(process.argv[2]);"
                  " console.log(JSON.stringify(q.map((text) => { const v = m.verdict(text, e); return [v.state, v.rows.map((r) => r.entry.shown)]; }))); });")
        done = subprocess.run(["node", "-e", script, json.dumps(entries), json.dumps(queries)], capture_output=True, text=True, check=True)
        return dict(zip(queries, json.loads(done.stdout)))

    def test_verdicts(self):
        got = self.states(["72", "7208 10 00", "7202", "7202 21 00", "7204", "7202 99 10", "3105", "3105 60 00", "3105 20 10",
                           "2507", "2507 00 80", "7318 15", "8302 42 00", "8703", "7208100000"])
        self.assertEqual(got["72"][0], "short")
        self.assertEqual(got["7208 10 00"], ["in", ["72"]])
        self.assertEqual(got["7202"][0], "mixed")           # 일부 합금철만 제외된다
        self.assertEqual(got["7202 21 00"][0], "excluded")
        self.assertEqual(got["7204"][0], "excluded")
        self.assertEqual(got["7202 99 10"][0], "excluded")
        self.assertEqual(got["3105"][0], "mixed")
        self.assertEqual(got["3105 60 00"][0], "excluded")
        self.assertEqual(got["3105 20 10"], ["in", ["3105"]])
        self.assertEqual(got["2507"], ["mixed", ["ex 2507 00 80"]])  # 아래의 한 코드만, 그것도 일부만
        self.assertEqual(got["2507 00 80"][0], "part")
        self.assertEqual(got["7318 15"], ["in", ["7318"]])
        self.assertEqual(got["8302 42 00"][0], "part")
        self.assertEqual(got["8703"][0], "out")
        self.assertEqual(got["7208100000"][0], "in")        # 10자리 코드도 앞자리로 견준다


@unittest.skipUnless(shutil.which("node"), "node가 없으면 화면의 셈은 시험하지 않는다")
class StageTest(unittest.TestCase):
    PATH = ["집행위 제안", "의회·이사회 입장", "3자 협상", "채택·공포", "시행"]

    def test_the_screen_and_the_health_check_agree_on_when_a_proposal_is_adopted(self):
        from tools.run import cn_health
        rules = [{"id": "cbam-downstream", "path": self.PATH, "at": at} for at in range(5)] + [{"id": "x", "path": ["준비", "시행"], "at": 1}, {"id": "y"}]
        script = "import('./site/js/cn/stage.js').then((m) => console.log(JSON.stringify(JSON.parse(process.argv[1]).map((rule) => m.adopted(rule)))));"
        done = subprocess.run(["node", "-e", script, json.dumps(rules)], capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(done.stdout), [cn_health.adopted(rule) for rule in rules])
        self.assertEqual(json.loads(done.stdout)[:5], [False, False, False, True, True])


class CnDataTest(unittest.TestCase):
    def test_the_published_list_matches_the_stored_law(self):
        from tools.cn import build
        law = build.read_lines("cbam-consolidated.txt")
        current = annex.tables(annex.between(law, "ANNEX I", "ANNEX II"))
        with open("data/cn.json", encoding="utf-8") as handle:
            book = json.load(handle)
        self.assertEqual([(entry["sector"], entry["codes"], entry["text"]) for entry in book["current"]],
                         [(entry["sector"], entry["codes"], entry["text"]) for entry in current])
        self.assertEqual(build.problems(book["current"], [entry for entry in book["current"] if entry["directOnly"]], book["proposed"]), [])


class CnHealthTest(unittest.TestCase):
    CN = {"law": {"celex": "02023R0956-20251020"}, "proposed": [{"codes": ["7318"]}], "council": {"added": ["73181100"]}}
    RULE = {"id": "cbam-downstream", "path": ["집행위 제안", "의회·이사회 입장", "3자 협상", "채택·공포", "시행"], "at": 2, "positions": {"rows": []}}
    NOW = datetime.datetime(2027, 3, 10, 8, 0, tzinfo=datetime.timezone(datetime.timedelta(hours=9)))

    def _problems(self, entries=(), rule=None, refresh=None):
        from tools.run import cn_health
        return cn_health.problems(self.CN, list(entries), [rule or self.RULE], refresh or {}, self.NOW)

    def test_nothing_to_report_while_the_law_and_the_proposal_stand_as_they_are(self):
        entries = [{"celex": "02023R0956-20251020"}, {"celex": "02023R0956-20230516"}, {"celex": "02024R3210-20260101"}]
        self.assertEqual(self._problems(entries), [])

    def test_a_newer_consolidated_text_that_was_not_picked_up_is_reported(self):
        found = self._problems([{"celex": "02023R0956-20251020"}, {"celex": "02023R0956-20270301"}])
        self.assertEqual(len(found), 1)
        self.assertIn("02023R0956-20270301", found[0])
        self.assertIn("돌지 않음", found[0])

    def test_a_failed_rebuild_is_reported_with_its_reason(self):
        refresh = {"state": "failed", "celex": "02023R0956-20270301", "triedAt": "2027-03-10T06:20:00+09:00", "problems": ["부속서 II를 읽지 못함"]}
        found = self._problems([{"celex": "02023R0956-20270301"}], refresh=refresh)
        self.assertEqual(len(found), 1)
        self.assertIn("부속서 II를 읽지 못함", found[0])

    def test_a_rebuild_is_announced_for_a_few_days_and_then_falls_silent(self):
        done = {"state": "rebuilt", "celex": "02023R0956-20251020", "added": ["7326"], "removed": []}
        fresh = self._problems(refresh=dict(done, triedAt="2027-03-09T06:20:00+09:00"))
        self.assertEqual(len(fresh), 1)
        self.assertIn("더해진 줄 1", fresh[0])
        self.assertEqual(self._problems(refresh=dict(done, triedAt="2027-03-01T06:20:00+09:00")), [])

    def test_adoption_of_the_amendment_is_reported_for_the_notes_and_the_comparison(self):
        found = self._problems(rule=dict(self.RULE, at=3))
        self.assertEqual(len(found), 2)
        self.assertTrue(any("개정안" in line for line in found) and any("비교표" in line for line in found))

    def test_the_check_reads_the_repository_without_arguments(self):
        from tools.run import cn_health
        self.assertIsInstance(cn_health.problems(), list)  # 무엇이 나오는지는 자료에 달렸으므로 꼴만 본다


class VersionsTest(unittest.TestCase):
    def test_the_name_and_address_follow_the_number_of_the_consolidated_text(self):
        from tools.cn import versions
        meta = versions.law_meta("02023R0956-20270301", "http://example.org/x")
        self.assertIn("2027년 3월 1일 통합본", meta["name"])
        self.assertTrue(meta["url"].endswith("CELEX:02023R0956-20270301"))
        self.assertEqual(versions.day_of("02023R0956"), "")

    def test_only_later_versions_of_the_same_law_count_as_newer(self):
        from tools.cn import versions
        entries = [{"celex": "02023R0956-20230516"}, {"celex": "02024R3210-20280101"}, {"celex": "02023R0956-20270301"}, {"celex": "02023R0956-20260101"}]
        self.assertEqual(versions.newer_consolidated("02023R0956-20251020", entries), "02023R0956-20270301")
        self.assertEqual(versions.newer_consolidated("02023R0956-20270301", entries), "")


class EnactedTest(unittest.TestCase):
    PROPOSED = [{"sector": "steel", "codes": ["7326"]}, {"sector": "combined", "codes": ["83024200"]}, {"sector": "combined", "codes": ["870431"]}]

    def test_the_proposal_counts_as_enacted_once_its_goods_are_in_the_law(self):
        from tools.cn import build
        before = [{"sector": "steel", "codes": ["72"]}, {"sector": "steel", "codes": ["7326"]}]
        self.assertFalse(build.enacted(before, self.PROPOSED))
        self.assertTrue(build.enacted(before + [{"sector": "combined", "codes": ["83024200"]}], self.PROPOSED))
        self.assertFalse(build.enacted(before, []))


class RefreshTest(unittest.TestCase):
    """새 통합본이 나오면 목록을 다시 만든다. 저장소의 실제 원문을 임시 폴더에 옮겨 놓고 시험한다."""
    NEWER = "02023R0956-20270301"
    FILES = ["data/cn.json", "collected/archive/eu-fulltext.json", "collected/archive/pages/eu-fulltext/cbam-consolidated.txt",
             "collected/archive/pages/eu-fulltext/downstream-commission-DOC_2.txt", "collected/archive/pages/eu-fulltext/downstream-council.txt"]

    def setUp(self):
        self.previous = os.getcwd()
        self.folder = tempfile.TemporaryDirectory()
        for name in self.FILES:
            target = pathlib.Path(self.folder.name) / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(name, target)
        os.chdir(self.folder.name)
        self._related([self.NEWER])
        self.law = pathlib.Path(self.FILES[2]).read_text(encoding="utf-8").split("\n")[2:]

    def tearDown(self):
        os.chdir(self.previous)
        self.folder.cleanup()

    def _related(self, numbers):
        path = pathlib.Path("collected/archive/eur-lex-related.json")
        path.write_text(json.dumps({"entries": [{"celex": "02023R0956-20251020"}] + [{"celex": number} for number in numbers]}), encoding="utf-8")

    def _book(self):
        return json.loads(pathlib.Path("data/cn.json").read_text(encoding="utf-8"))

    def _with_new_line(self):
        """철강 표의 7318 줄 앞에 품목 한 줄을 끼운 통합본."""
        at = next(index for index, line in enumerate(self.law) if line.strip().startswith("7318"))
        return self.law[:at] + ["7399 – Imaginary articles of iron or steel", "Carbon dioxide"] + self.law[at:]

    def test_nothing_is_fetched_when_no_newer_text_exists(self):
        from tools.cn import refresh
        self._related([])
        called = []
        result = refresh.refresh(fetch_parts=lambda number: called.append(number) or ([], "x"))
        self.assertEqual((result["state"], called), ("same", []))
        self.assertFalse(pathlib.Path(refresh.STATE).exists())

    def test_a_newer_text_that_reads_well_replaces_the_list(self):
        from tools.cn import refresh
        address = f"http://publications.europa.eu/resource/celex/{self.NEWER}"
        result = refresh.refresh(fetch_parts=lambda number: ([("", address, self._with_new_line())], ""))
        self.assertEqual(result["state"], "rebuilt")
        self.assertEqual((result["added"], result["removed"]), (["7399"], []))
        book = self._book()
        self.assertEqual(book["law"]["celex"], self.NEWER)
        self.assertIn("2027년 3월 1일", book["law"]["name"])
        self.assertIn("7399", [entry["shown"] for entry in book["current"]])
        self.assertTrue(pathlib.Path(self.FILES[2]).read_text(encoding="utf-8").startswith(f"[주소] {address}"))
        index = json.loads(pathlib.Path(self.FILES[1]).read_text(encoding="utf-8"))
        self.assertEqual([row["code"] for row in index["entries"] if row["name"] == "cbam-consolidated"], [self.NEWER])
        self.assertTrue(any(row["name"].startswith("downstream-") for row in index["entries"]))  # 다른 문서의 기록은 그대로다
        self.assertEqual(refresh.refresh(fetch_parts=lambda number: self.fail("다시 받으면 안 된다"))["state"], "same")

    def test_the_text_in_use_is_kept_as_an_earlier_version_before_it_is_replaced(self):
        from tools.archive import earlier
        from tools.cn import refresh
        before = pathlib.Path(self.FILES[2]).read_text(encoding="utf-8")
        refresh.refresh(fetch_parts=lambda number: ([("", "http://x.example/doc", self._with_new_line())], ""))
        kept = [row for row in earlier.entries() if row["code"] == "02023R0956-20251020"]
        self.assertEqual([(row["act"], row["kind"], row["date"]) for row in kept], [("32023R0956", "consolidated", "2025-10-20")])
        self.assertEqual(pathlib.Path(kept[0]["textPath"]).read_text(encoding="utf-8"), before)
        self.assertNotEqual(pathlib.Path(self.FILES[2]).read_text(encoding="utf-8"), before)

    def test_a_text_that_does_not_read_well_changes_nothing(self):
        from tools.cn import refresh
        before = (self._book(), pathlib.Path(self.FILES[2]).read_text(encoding="utf-8"))
        broken = [line for line in self.law if not line.strip().startswith("2523 10 00")]  # 꼭 읽혀야 하는 품목 하나가 빠진 글
        result = refresh.refresh(fetch_parts=lambda number: ([("", "http://x.example/doc", broken)], ""))
        self.assertEqual(result["state"], "failed")
        self.assertTrue(any("25231000" in why for why in result["problems"]))
        self.assertEqual((self._book(), pathlib.Path(self.FILES[2]).read_text(encoding="utf-8")), before)
        self.assertEqual(json.loads(pathlib.Path(refresh.STATE).read_text(encoding="utf-8"))["celex"], self.NEWER)

    def test_a_failed_download_changes_nothing(self):
        from tools.cn import refresh
        before = self._book()
        self.assertEqual(refresh.refresh(fetch_parts=lambda number: ([], "응답 503"))["state"], "failed")
        self.assertEqual(refresh.refresh(fetch_parts=lambda number: ([("", "http://x.example/doc", ["다른 문서"])], ""))["state"], "failed")
        self.assertEqual(self._book(), before)


if __name__ == "__main__":
    unittest.main()
