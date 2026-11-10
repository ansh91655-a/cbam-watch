"""품목 코드 조회: 법령 부속서를 읽는 것과 코드를 견주는 셈."""
import json
import shutil
import subprocess
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

    def test_nothing_to_report_while_the_law_and_the_proposal_stand_as_they_are(self):
        from tools.run import cn_health
        entries = [{"celex": "02023R0956-20251020"}, {"celex": "02023R0956-20230516"}, {"celex": "02024R3210-20260101"}]
        self.assertEqual(cn_health.problems(self.CN, entries, [self.RULE]), [])

    def test_a_newer_consolidated_text_asks_for_a_rebuild(self):
        from tools.run import cn_health
        entries = [{"celex": "02023R0956-20251020"}, {"celex": "02023R0956-20270301"}]
        found = cn_health.problems(self.CN, entries, [self.RULE])
        self.assertEqual(len(found), 1)
        self.assertIn("02023R0956-20270301", found[0])

    def test_adoption_of_the_amendment_asks_to_retire_the_proposal_notes_and_the_comparison(self):
        from tools.run import cn_health
        found = cn_health.problems(self.CN, [], [dict(self.RULE, at=3)])
        self.assertEqual(len(found), 2)
        self.assertTrue(any("개정안" in line for line in found) and any("비교표" in line for line in found))

    def test_the_repository_as_it_is_reports_nothing(self):
        from tools.run import cn_health
        self.assertEqual(cn_health.problems(), [])


if __name__ == "__main__":
    unittest.main()
