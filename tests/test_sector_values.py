"""부문별 모아 보기의 '기본값과 벤치마크' 표(site/js/sector/values.js): 부문의 품목을 줄로 펴기, 찾기, 생산경로마다의 값, 내려받는 파일의 글.
화면 요소를 다루지 않는 부분만 node로 본다. 값은 비용 추정의 자료를 짧게 지은 것이다."""
import csv
import json
import pathlib
import shutil
import subprocess
import unittest

SCRIPT = r"""
import { defaultRoutes, unpack } from './site/js/calc/compute.js';
import { csv, filterRows, PAGE, routeRows, summary, valueRows } from './site/js/sector/values.js';

// 클링커(세부 품목이 둘이고 하나는 '그 밖의 나라'의 값), 열연 코일(경로 셋), 합금강(낮은 등급 F와 높은 등급 J, 연도 구간마다 값이 다름), 비료(간접배출이 있음)
const book = unpack({
  asOf: '2026-11-11', years: { from: 2026, to: 2034 }, periods: [{ key: 1, from: 2026, to: 2027 }, { key: 2, from: 2028, to: 2030 }],
  markups: [{ sectors: ['cement', 'steel'], values: { 2026: 10, 2027: 20, 2028: 30 } }, { sectors: ['fertilisers'], values: { 2026: 1 } }],
  routes: [{ key: 'A', name: '회색 클링커·시멘트' }, { key: 'B', name: '백색 클링커·시멘트' }, { key: 'C', name: '탄소강, 고로·전로' }, { key: 'D', name: '탄소강, 직접환원철·전기로' },
    { key: 'F', name: '저합금강, 고로·전로' }, { key: 'J', name: '고합금강(전기로)' }],
  rows: [['2523100010', 'White clinker', 'kr', 1.19, 0.04, 1.23], ['2523100090', 'Other clinker, "grey"', 'other', 0.88, 0.03, 0.92],
    ['7208', 'Flat-rolled products of iron or non-alloy steel', 'kr', 2.0, null, 2.0], ['722540', 'Flat-rolled products of alloy steel', 'kr', 4.03, null, 4.03],
    ['3102 10', 'Urea', 'kr', 1.6, 0.2, 1.8]],
  goods: [
    ['25231000', 'Cement clinkers', 'cement', [[0.666, 'A', 0], [0.859, 'B', 0]], [[0.666, 'A', 0], [0.859, 'B', 0]], [[0, 'B', 0.859, 0.859], [1, 'A', 0.666, 0.666]]],
    ['72081000', 'Flat-rolled products, in coils, hot-rolled', 'steel', [[0.1, '', 0]], [[1.37, 'C', 1], [1.288, 'C', 2], [0.481, 'D', 0]], [[2, 'C', 1.37, 1.288]]],
    ['72254015', 'Flat-rolled products of high-speed steel', 'steel', [[0.073, '', 0]], [[1.577, 'F', 1], [1.409, 'F', 2], [0.95, 'J', 1], [0.918, 'J', 2]], [[3, 'F', 1.577, 1.409]]],
    ['31021010', 'Urea, in aqueous solution', 'fertilisers', [[1.5, '', 0]], [[1.5, '', 0]], [[4, '', 1.5, 1.5]]],
  ],
});
const steel = valueRows(book, 'steel');
const cement = valueRows(book, 'cement');
const coil = book.goods[1];
const alloy = book.goods[2];
console.log(JSON.stringify({
  page: PAGE,
  cement: cement.map((row) => [row.code, row.shown, row.rowText, row.origin, row.direct, row.indirect, row.total, row.route, row.routeName, row.benchmark, row.routes, row.split]),
  steel: steel.map((row) => [row.code, row.shown, row.indirect, row.route, row.benchmark, row.routes, row.split]),
  none: valueRows(book, 'electricity'),
  found: {
    code: filterRows(steel, '7208').map((row) => row.code), spaced: filterRows(steel, '7225 40').map((row) => row.code), longer: filterRows(steel, '7208100099').map((row) => row.code),
    rowCode: filterRows(cement, '2523100090').map((row) => row.shown), word: filterRows(steel, 'HIGH-speed steel').map((row) => row.code),
    route: filterRows(steel, '고로').map((row) => row.code), nothing: filterRows(steel, 'aluminium').length, all: filterRows(steel, '  ').length,
  },
  routes: {
    coil: routeRows(book, coil, coil.defaults[0]).map((row) => [row.route, row.name, row.a, row.b, row.used]),
    alloy: routeRows(book, alloy, alloy.defaults[0]).map((row) => [row.route, row.used]),
    urea: routeRows(book, book.goods[3], book.goods[3].defaults[0]).map((row) => [row.route, row.a, row.b, row.used]),
    used: [defaultRoutes(coil, coil.defaults[0]), defaultRoutes(alloy, alloy.defaults[0]), defaultRoutes(book.goods[3], book.goods[3].defaults[0])],
  },
  summary: { steel: summary(book, 'steel'), cement: summary(book, 'cement'), fertilisers: summary(book, 'fertilisers'), none: summary(book, 'electricity') },
  csv: { cement: csv(book, 'cement').split('\r\n'), steel: csv(book, 'steel').split('\r\n'), fertilisers: csv(book, 'fertilisers').split('\r\n') },
}));
"""


@unittest.skipUnless(shutil.which("node"), "node가 없으면 화면 모듈은 시험하지 않는다")
class SectorValuesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        done = subprocess.run(["node", "--input-type=module", "-e", SCRIPT], capture_output=True, text=True)
        if done.returncode:
            raise AssertionError(done.stderr[-1500:])
        cls.seen = json.loads(done.stdout)

    def test_each_default_row_of_a_good_is_one_line(self):
        cement = self.seen["cement"]
        self.assertEqual(cement, [
            ["25231000", "2523100010", "White clinker", "kr", 1.19, 0.04, 1.23, "B", "백색 클링커·시멘트", [0.859, 0.859], 2, True],
            ["25231000", "2523100090", 'Other clinker, "grey"', "other", 0.88, 0.03, 0.92, "A", "회색 클링커·시멘트", [0.666, 0.666], 2, True],
        ])                                                             # 세부 품목으로 갈린 품목은 줄이 둘이고, 줄마다 제 경로의 벤치마크가 붙는다
        self.assertEqual(self.seen["steel"], [["72081000", "7208", None, "C", [1.37, 1.288], 2, False], ["72254015", "722540", None, "F", [1.577, 1.409], 2, False]])
        self.assertEqual(self.seen["none"], [])                        # 값의 표가 없는 부문
        self.assertEqual(self.seen["page"], 40)

    def test_rows_are_found_by_code_or_by_words(self):
        found = self.seen["found"]
        self.assertEqual((found["code"], found["spaced"], found["longer"]), (["72081000"], ["72254015"], ["72081000"]))   # 앞자리로, 띄어 적어도, 8자리를 넘으면 앞 8자리로
        self.assertEqual(found["rowCode"], ["2523100090"])             # 기본값 표의 줄에 적힌 코드로도 찾는다
        self.assertEqual((found["word"], found["route"]), (["72254015"], ["72081000", "72254015"]))                       # 영문 낱말(대소문자 없이), 생산경로의 국문 이름
        self.assertEqual((found["nothing"], found["all"]), (0, 2))

    def test_benchmarks_of_every_route_with_the_ones_used_for_default_reporting(self):
        routes = self.seen["routes"]
        self.assertEqual(routes["coil"], [["C", "탄소강, 고로·전로", [0.1, 0.1], [1.37, 1.288], True], ["D", "탄소강, 직접환원철·전기로", [0.1, 0.1], [0.481, 0.481], False]])
        self.assertEqual(routes["alloy"], [["F", True], ["J", True]])  # 합금강은 두 등급의 값 가운데 큰 것을 쓰므로 둘 다 표시한다
        self.assertEqual(routes["urea"], [["", [1.5, 1.5], [1.5, 1.5], False]])   # 경로를 가르지 않는 품목은 한 줄
        self.assertEqual(routes["used"], [["C"], ["F", "J"], []])

    def test_the_summary_counts_what_the_table_holds(self):
        summary = self.seen["summary"]
        self.assertEqual(summary["cement"], {"goods": 1, "rows": 2, "korea": 1, "other": 1, "indirect": 2, "routed": 1, "markups": {"2026": 10, "2027": 20, "2028": 30}})
        self.assertEqual((summary["steel"]["goods"], summary["steel"]["indirect"], summary["steel"]["routed"]), (2, 0, 2))
        self.assertEqual(summary["fertilisers"]["markups"], {"2026": 1})
        self.assertEqual(summary["none"], {"goods": 0, "rows": 0, "korea": 0, "other": 0, "indirect": 0, "routed": 0, "markups": {}})

    def test_the_download_has_one_line_for_each_good_and_route(self):
        cement = self.seen["csv"]["cement"]
        self.assertEqual(cement[0], "cn_code,goods,default_row_code,default_row,default_origin,direct_tco2e_per_t,indirect_tco2e_per_t,total_tco2e_per_t,"
                                    "total_with_markup_2026,total_with_markup_2027,total_with_markup_2028,route,route_name,used_for_default_reporting,"
                                    "benchmark_b_2026-2027,benchmark_b_2028-2030,benchmark_a_2026-2027,benchmark_a_2028-2030")
        self.assertEqual(len(cement), 1 + 4 + 1)                       # 머리, 줄 둘에 경로 둘씩, 끝의 빈 줄
        self.assertEqual(cement[1], '25231000,Cement clinkers,2523100010,White clinker,"Korea, Republic of",1.19,0.04,1.23,1.353,1.476,1.599,A,회색 클링커·시멘트,no,0.666,0.666,0.666,0.666')
        self.assertEqual(cement[4], '25231000,Cement clinkers,2523100090,"Other clinker, ""grey""",Other countries and territories,0.88,0.03,0.92,1.012,1.104,1.196,B,백색 클링커·시멘트,no,0.859,0.859,0.859,0.859')
        steel = list(csv.reader(self.seen["csv"]["steel"]))          # 쉼표가 든 품목 이름은 따옴표로 싸여 있다
        self.assertEqual((steel[1][1], steel[1][5:8]), ("Flat-rolled products, in coils, hot-rolled", ["2", "", "2"]))   # 간접배출의 값이 없으면 빈칸
        self.assertEqual([(line[0], line[-7], line[-5]) for line in steel[1:5]], [("72081000", "C", "yes"), ("72081000", "D", "no"), ("72254015", "F", "yes"), ("72254015", "J", "yes")])
        urea = list(csv.reader(self.seen["csv"]["fertilisers"]))
        self.assertEqual(sum(1 for name in urea[0] if name.startswith("total_with_markup")), 1)   # 마크업이 한 해뿐인 부문
        self.assertEqual(urea[1][-7:], ["", "", "yes", "1.5", "1.5", "1.5", "1.5"])               # 경로를 가르지 않는 품목

    def test_the_view_and_its_address_are_wired(self):
        view = pathlib.Path("site/js/views/sector.js").read_text(encoding="utf-8")
        self.assertIn('page === "values"', view)
        self.assertIn("valuesView(unpack(calc), sector)", view)
        table = pathlib.Path("site/js/views/sector/values.js").read_text(encoding="utf-8")
        for piece in ("#law-32026R1740", "#law-32025R2620", "#pdf-32026R1740.p5", "표 내려받기(CSV)", "aria-expanded"):
            self.assertIn(piece, table)


if __name__ == "__main__":
    unittest.main()
