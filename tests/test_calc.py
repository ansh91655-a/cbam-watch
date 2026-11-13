"""인증서 비용 추정: 받아 둔 표 읽기(calc.source), 품목 자료 만들기(calc.build), 검사와 공개 모양(publish.calc), 화면의 셈(site/js/calc/compute.js)."""
import copy
import json
import pathlib
import shutil
import subprocess
import tempfile
import unittest

from tools.calc import build, source
from tools.calc.source import Unreadable
from tools.common.jsonio import read_json
from tools.publish import calc, factor
from tools.run import reference_health


class SourceTest(unittest.TestCase):
    def test_a_benchmark_cell_is_read_with_its_route_and_period_marks(self):
        self.assertEqual(source.variants("0,666"), [{"value": 0.666, "route": "", "period": 0}])
        self.assertEqual(source.variants("1,288 (C) 0,424 (D) 0,027 (E)"),
                         [{"value": 1.288, "route": "C", "period": 0}, {"value": 0.424, "route": "D", "period": 0}, {"value": 0.027, "route": "E", "period": 0}])
        self.assertEqual(source.variants("0,717 (1) 0,686 (2)"), [{"value": 0.717, "route": "", "period": 1}, {"value": 0.686, "route": "", "period": 2}])
        self.assertEqual(source.variants("1,460 (F)(1) 0,852 (J)(1) 1,298 (F)(2) 0,820 (J)(2)")[2], {"value": 1.298, "route": "F", "period": 2})

    def test_a_cell_that_cannot_be_read_stops_the_build_instead_of_being_guessed(self):
        for cell in ("", "n/a", "0,5 (C) 0,4", "0,5 (C) 0,6 (C)", "0,5 (C)(D)", "0,5 see note"):
            with self.assertRaises(Unreadable, msg=cell):
                source.variants(cell)

    def test_the_stored_tables_are_read_whole(self):
        book, notes = source.benchmarks()
        self.assertEqual(len(book["rows"]), 570)
        self.assertEqual({good["sector"] for good in book["rows"]}, {"cement", "fertilisers", "steel", "aluminium", "hydrogen"})
        self.assertTrue(any("Value is to be used for production years 2026-27" in line for line in notes))
        tables = source.defaults()
        self.assertIn("Korea", tables["korea"]["caption"])
        self.assertEqual(len(tables["korea"]["rows"]), len(tables["other"]["rows"]))
        hot_rolled = next(row for row in tables["korea"]["rows"] if row["shown"] == "7208")
        self.assertEqual((hot_rolled["state"], hot_rolled["total"], hot_rolled["indirect"], hot_rolled["routes"]), ("value", 2.118, None, ["C"]))
        self.assertEqual({row["state"] for row in tables["korea"]["rows"]}, {"value", "none", "below"})


class BuildTest(unittest.TestCase):
    ROWS = [{"code": "7208", "state": "value"}, {"code": "7211", "state": "below"}, {"code": "721113", "state": "value"}, {"code": "72111400", "state": "value"},
            {"code": "2523100010", "state": "value"}, {"code": "2523100090", "state": "value"}]

    def test_the_longest_matching_default_row_is_used(self):
        self.assertEqual(build.matching("72081000", self.ROWS), [0])
        self.assertEqual(build.matching("72111300", self.ROWS), [2])
        self.assertEqual(build.matching("72111400", self.ROWS), [3])
        self.assertEqual(build.matching("72119000", self.ROWS), [])       # '아래를 보라'고만 적힌 행은 값이 아니다
        self.assertEqual(build.matching("25231000", self.ROWS), [4, 5])   # TARIC 코드로 갈린 품목은 둘 다

    def good(self, cell):
        return {"shown": "x", "b": source.variants(cell)}

    def test_the_default_benchmark_follows_the_route_named_in_the_default_row(self):
        self.assertEqual(build.default_benchmark(self.good("1,288 (C) 0,424 (D) 0,027 (E)"), ["C"]), ("C", [1.288, 1.288]))
        self.assertEqual(build.default_benchmark(self.good("1,423 (K) 0,091 (L)"), ["L"]), ("L", [0.091, 0.091]))
        self.assertEqual(build.default_benchmark(self.good("0,717 (1) 0,686 (2)"), []), ("", [0.717, 0.686]))
        # 품목의 벤치마크에 경로 표시가 없으면 기본값 행에 경로가 적혀 있어도 경로와 상관없는 값이다
        self.assertEqual(build.default_benchmark(self.good("0,500"), ["C"]), ("", [0.5, 0.5]))
        # 기본값 행에 (C)/(F)가 함께 적혀 있으면 품목의 벤치마크에 있는 쪽을 쓴다
        self.assertEqual(build.default_benchmark(self.good("1,288 (C) 0,424 (D) 0,027 (E)"), ["C", "F"])[0], "C")

    def test_for_alloy_steel_the_higher_of_the_alloy_grades_is_used(self):
        cell = "1,460 (F)(1) 0,659 (G)(1) 0,328 (H)(1) 0,852 (J)(1) 1,298 (F)(2) 0,600 (G)(2) 0,300 (H)(2) 1,350 (J)(2)"
        self.assertEqual(build.default_benchmark(self.good(cell), ["C", "F"]), ("F", [1.46, 1.35]))

    def test_cases_the_law_does_not_settle_stop_the_build(self):
        with self.assertRaises(Unreadable):   # 경로가 맞지 않음
            build.default_benchmark(self.good("1,288 (C) 0,424 (D)"), ["K"])
        with self.assertRaises(Unreadable):   # 기본값 행에 경로가 없는데 벤치마크는 경로에 따라 다름
            build.default_benchmark(self.good("1,288 (C) 0,424 (D)"), [])
        with self.assertRaises(Unreadable):   # 합금강인데 경로가 F가 아님
            build.default_benchmark(self.good("1,460 (F)(1) 0,328 (H)(1) 0,852 (J)(1) 1,298 (F)(2) 0,300 (H)(2) 0,820 (J)(2)"), ["H"])

    def test_the_goods_file_matches_what_the_stored_tables_give(self):
        body = build.build()
        self.assertEqual(read_json(build.TARGET), body)
        self.assertEqual(json.loads(build.dump(body)), body)
        goods = {good["code"]: good for good in body["goods"]}
        self.assertEqual(len(goods), 570)
        coil = goods["72081000"]["defaults"][0]
        self.assertEqual((body["rows"][coil["row"]]["shown"], body["rows"][coil["row"]]["origin"], coil["route"], coil["benchmark"]), ("7208", "kr", "C", [1.37, 1.37]))
        self.assertEqual(len(goods["25231000"]["defaults"]), 2)
        ammonia = goods["28141000"]["defaults"][0]
        self.assertEqual(body["rows"][ammonia["row"]]["origin"], "other")  # 대한민국 표에 값이 없는 품목


class PublishTest(unittest.TestCase):
    def setUp(self):
        self.terms, self.goods = read_json(calc.SOURCE), read_json(calc.GOODS)

    def test_the_stored_data_has_no_problems(self):
        self.assertEqual(calc.problems(self.terms, self.goods), [])

    def test_a_changed_value_is_reported_as_drift_from_the_legal_text(self):
        terms = copy.deepcopy(self.terms)
        terms["markups"][0]["values"]["2027"] = 25
        found = calc.problems(terms, self.goods)
        self.assertEqual([where for where, _ in found], ["마크업 1"])
        self.assertTrue(found[0][1].startswith(calc.DRIFT))
        self.assertEqual(calc.blocking(found), [])
        terms = copy.deepcopy(self.terms)
        terms["cscf"]["values"]["2031"] = 100   # 결정문은 2030년까지만 정했다
        self.assertTrue(any("2026 to 2031" in what for _, what in calc.problems(terms, self.goods)))
        terms = copy.deepcopy(self.terms)
        terms["routes"][2]["en"] = "Carbon Steel based on hydrogen"
        self.assertEqual([where for where, _ in calc.problems(terms, self.goods)], ["생산경로 C"])
        terms = copy.deepcopy(self.terms)
        note = next(one for one in terms["notes"] if one["key"] == "cscf")
        note["evidence"]["contains"].append("a sentence the law does not have")
        self.assertEqual([where for where, _ in calc.problems(terms, self.goods)], ["설명 글 cscf"])

    def test_a_broken_shape_blocks_the_build(self):
        terms = copy.deepcopy(self.terms)
        terms["markups"][1]["sectors"] = []
        self.assertTrue(calc.blocking(calc.problems(terms, self.goods)))
        terms = copy.deepcopy(self.terms)
        terms["periods"][1]["from"] = 2029
        self.assertTrue(any(where == "연도 구간" for where, _ in calc.blocking(calc.problems(terms, self.goods))))
        goods = copy.deepcopy(self.goods)
        goods["goods"][0]["defaults"][0]["row"] = 9999
        self.assertTrue(calc.blocking(calc.problems(self.terms, goods)))
        terms = copy.deepcopy(self.terms)
        terms["watch"]["known"] = []
        self.assertEqual([where for where, _ in calc.blocking(calc.problems(terms, self.goods))], ["지켜볼 법령"])

    def test_goods_that_differ_from_the_stored_tables_are_reported_but_do_not_block(self):
        goods = copy.deepcopy(self.goods)
        goods["goods"][10]["b"][0][0] += 0.1
        found = calc.problems(self.terms, goods)
        self.assertEqual(len(found), 1)
        self.assertIn("다시 만든 것과 다름(품목 1개", found[0][1])
        self.assertEqual(calc.blocking(found), [])

    def test_a_renumbered_table_is_not_drift_while_the_values_stay_the_same(self):
        goods = copy.deepcopy(self.goods)
        goods["builtFrom"]["benchmarks"]["table"] += 7
        goods["builtFrom"]["defaults"]["korea"]["table"] += 7
        self.assertEqual(calc.problems(self.terms, goods), [])

    def test_the_public_shape_carries_no_repository_paths(self):
        body = calc.public(self.terms, self.goods)
        text = calc.dump(body)
        self.assertNotIn("collected/", text)
        self.assertNotIn("originals/", text)
        self.assertNotIn("evidence", text)
        self.assertEqual(len(body["goods"]), 570)
        self.assertEqual(body["goods"][0][0], self.goods["goods"][0]["code"])
        self.assertTrue(all(note["sources"] and all(source["url"].startswith("https://") for source in note["sources"]) for note in body["notes"]))
        self.assertEqual(len(body["formula"]["sources"]), 2)   # 법령과, 식이 글로 적힌 집행위 가이던스

    def test_evidence_must_be_a_stored_text_and_every_block_of_a_list_is_checked(self):
        terms = copy.deepcopy(self.terms)
        terms["notes"][0]["evidence"] = {"path": "README.md", "contains": ["cbam-watch"]}
        found = calc.problems(terms, self.goods)
        self.assertEqual([where for where, _ in found], ["설명 글 certificate"])
        self.assertIn("근거 글이 없음", found[0][1])
        terms = copy.deepcopy(self.terms)
        terms["formula"]["evidence"][1]["contains"].append("𝑆𝐸𝐹𝐴 = 𝐵𝑀 + 1")
        self.assertEqual([where for where, _ in calc.problems(terms, self.goods)], ["계산식"])
        terms = copy.deepcopy(self.terms)
        terms["formula"]["sources"] = ["faa", "nowhere"]
        self.assertEqual([where for where, _ in calc.blocking(calc.problems(terms, self.goods))], ["계산식"])


class ReferenceHealthTest(unittest.TestCase):
    ENTRIES = [
        {"celex": "32025R2620", "title": "Commission Implementing Regulation (EU) 2025/2620 of 16 December 2025 laying down rules"},
        {"celex": "32026R1740", "title": "Commission Implementing Regulation (EU) 2026/1740 correcting Implementing Regulation (EU) 2025/2621"},
        {"celex": "52026PC0619", "title": "Proposal amending Directive 2003/87/EC as regards revised benchmark values"},
    ]

    def test_nothing_is_reported_while_the_data_agrees_with_the_stored_texts(self):
        self.assertEqual(reference_health.problems(self.ENTRIES), [])

    def test_a_new_act_that_amends_a_law_behind_the_estimate_is_reported(self):
        newer = self.ENTRIES + [{"celex": "32027R0100", "title": "Commission Implementing Regulation (EU) 2027/100 amending Implementing Regulation (EU) 2025/2620 as regards the CBAM benchmarks"}]
        found = reference_health.problems(newer)
        self.assertEqual(len(found), 1)
        self.assertIn("32027R0100", found[0])
        self.assertIn("인증서 비용 추정", found[0])

    def test_long_lists_of_the_same_kind_are_cut_short(self):
        lines = reference_health._lines("실무 달력", [(f"의무 {number}", "근거 어긋남: x") for number in range(9)])
        self.assertEqual(len(lines), 5)
        self.assertIn("이 밖에 5건", lines[-1])


@unittest.skipUnless(shutil.which("node"), "node가 없으면 화면의 셈은 시험하지 않는다")
class ComputeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.book = calc.public(read_json(calc.SOURCE), read_json(calc.GOODS))
        cls.paths = factor.public(read_json(factor.SOURCE))["paths"]
        cls.folder = pathlib.Path(tempfile.mkdtemp())
        (cls.folder / "book.json").write_text(json.dumps({"book": cls.book, "paths": cls.paths}), encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.folder, ignore_errors=True)

    def run_js(self, body):
        """compute.js(m), 편 자료(book), 계수 경로(paths), 품목 찾기(good)를 쓸 수 있는 자리에서 body를 돌리고 그 값을 받는다."""
        script = ("import('./site/js/calc/compute.js').then(async (m) => { const fs = await import('node:fs');"
                  " const all = JSON.parse(fs.readFileSync(process.argv[1], 'utf8')); const book = m.unpack(all.book); const paths = all.paths;"
                  " const good = (code) => book.goods.find((one) => one.code === code);"
                  f" console.log(JSON.stringify((() => {{ {body} }})())); }});")
        done = subprocess.run(["node", "-e", script, str(self.folder / "book.json")], capture_output=True, text=True, check=True)
        return json.loads(done.stdout)

    def test_default_values_get_the_markup_and_the_default_benchmark(self):
        got = self.run_js("return [2026, 2027, 2028, 2030].map((year) => m.estimate(book, paths[0], { good: good('72081000'), mode: 'default', year, tonnes: 1000, price: 80 }));")
        first = got[0]
        self.assertAlmostEqual(first["embedded"], 2.118 * 1.10, places=9)
        self.assertAlmostEqual(first["allocation"], 1.37 * 0.975, places=9)
        self.assertAlmostEqual(first["perTonne"], 2.118 * 1.10 - 1.37 * 0.975, places=9)
        self.assertAlmostEqual(first["certificates"], first["perTonne"] * 1000, places=6)
        self.assertAlmostEqual(first["cost"], first["perTonne"] * 1000 * 80, places=4)
        self.assertEqual([row["markup"] for row in got], [10, 20, 30, 30])
        self.assertEqual([row["factor"] for row in got], [97.5, 95, 90, 51.5])
        self.assertEqual(first["assumed"], {"benchmark": False, "cscf": False, "updated": False})
        self.assertTrue(got[1]["assumed"]["updated"])

    def test_the_estimate_says_which_production_route_its_benchmark_came_from(self):
        got = self.run_js("const one = (code, more) => { const row = m.estimate(book, paths[0], { good: good(code), mode: 'default', year: 2026, tonnes: 1, price: 1, ...more }); return [row.route, row.routeAlt]; };"
                          " return [one('72081000'), one('72253010'), one('72081000', { mode: 'actual', see: 1.5, route: 'E' }), one('31021019')];")
        self.assertEqual(got[0], ["C", ""])       # 탄소강: 기본값 행에 적힌 경로
        self.assertEqual(got[1][0], "F")           # 합금강: 기본값 행의 경로와
        self.assertEqual(got[1][1], "J")           # 높은 등급의 경로 가운데 큰 값을 쓴다
        self.assertEqual(got[2], ["E", ""])       # 실제 배출량: 고른 경로
        self.assertEqual(got[3], ["", ""])        # 경로를 가르지 않는 품목

    def test_fertilisers_keep_the_one_percent_markup(self):
        got = self.run_js("return [2026, 2029].map((year) => m.estimate(book, paths[0], { good: good('31021019'), mode: 'default', year, tonnes: 1, price: 1 }).markup);")
        self.assertEqual(got, [1, 1])

    def test_the_benchmark_changes_with_the_production_year_and_is_assumed_after_2030(self):
        got = self.run_js("return [2027, 2028, 2030, 2031].map((year) => { const row = m.estimate(book, paths[0], { good: good('72189180'), mode: 'default', year, tonnes: 1, price: 1 }); return [row.benchmark, row.assumed.benchmark, row.assumed.cscf, row.cscf]; });")
        self.assertEqual(got, [[1.189, False, False, 100], [1.151, False, False, 100], [1.151, False, False, 100], [1.151, True, True, 100]])

    def test_the_two_factor_paths_part_from_2028_and_free_allocation_ends(self):
        got = self.run_js("return [0, 1].map((index) => [2027, 2028, 2034, 2038, 2040].map((year) => m.factorAt(paths[index], year)));")
        self.assertEqual(got[0], [95, 90, 0, 0, 0])
        self.assertEqual(got[1], [95, 91.5, 15, 0, 0])

    def test_actual_emissions_use_the_chosen_route_and_never_go_below_zero(self):
        got = self.run_js("const base = { good: good('72081000'), mode: 'actual', year: 2026, tonnes: 10, price: 50 };"
                          " return [m.estimate(book, paths[0], { ...base, see: 1.9, route: 'C' }), m.estimate(book, paths[0], { ...base, see: 0.4, route: 'E' }),"
                          " m.estimate(book, paths[0], { ...base, see: 1.0, route: 'C' }), m.estimate(book, paths[0], { ...base, see: '', route: 'C' }), m.estimate(book, paths[0], { ...base, see: 1.9, route: 'Z' })];")
        self.assertAlmostEqual(got[0]["perTonne"], 1.9 - 1.37 * 0.975, places=9)
        self.assertIsNone(got[0]["markup"])
        self.assertAlmostEqual(got[1]["allocation"], 0.072 * 0.975, places=9)
        self.assertEqual((got[2]["perTonne"], got[2]["certificates"], got[2]["cost"]), (0, 0, 0))
        self.assertAlmostEqual(got[2]["covered"], 1.0, places=9)
        self.assertIsNone(got[3])                                       # 값을 넣지 않으면 추정하지 않는다
        self.assertAlmostEqual(got[4]["benchmark"], 1.37, places=9)     # 모르는 경로는 기본값 표의 경로로 본다

    def test_every_good_can_be_estimated_and_matches_a_plain_recalculation(self):
        got = self.run_js("return book.goods.map((one) => one.defaults.map((choice, index) => { const row = m.estimate(book, paths[0], { good: one, choice: index, mode: 'default', year: 2028, tonnes: 1, price: 1 });"
                          " return [one.code, one.sector, choice.row.total, choice.benchmark[1], row.perTonne]; })).flat();")
        self.assertEqual(len(got), 572)
        for code, sector, total, benchmark, per_tonne in got:
            rate = 1 if sector == "fertilisers" else 30
            self.assertAlmostEqual(per_tonne, max(0, total * (1 + rate / 100) - benchmark * 0.90), places=9, msg=code)

    def test_goods_are_found_by_code_or_by_words(self):
        got = self.run_js("return [m.search(book.goods, '7208 10').map((one) => one.code), m.search(book.goods, '7208').length, m.search(book.goods, 'UREA aqueous').length,"
                          " m.search(book.goods, '').length, m.search(book.goods, '9999').length, m.routesOf(good('72253010')), m.routesOf(good('28041000'))];")
        self.assertEqual(got, [["72081000"], 8, 6, 0, 0, ["F", "G", "H", "J"], []])


if __name__ == "__main__":
    unittest.main()
