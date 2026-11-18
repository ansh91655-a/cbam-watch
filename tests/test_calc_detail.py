"""인증서 비용 추정의 자세한 셈(site/js/calc): 실제 배출량을 직접·간접으로 나누어 넣기, 전구물질을 따로 넣어 무상할당 조정을 법령의 식대로 셈하기,
탄소가격 차감(실질적으로 지불된 탄소가격, 기본 탄소가격)과 기준가격, 기본값과 같아지는 직접배출량, 내려받는 표의 줄.
화면 요소를 다루지 않는 부분만 node로 본다. 값은 비용 추정의 자료를 짧게 지은 것이다."""
import json
import pathlib
import shutil
import subprocess
import unittest

SCRIPT = r"""
import { estimate, series, unpack, defaultBenchmarkAt, period } from './site/js/calc/compute.js';
import { breakEven } from './site/js/calc/breakeven.js';
import { referencePrice, paid } from './site/js/calc/carbon.js';
import { basketRows, yearlyRows } from './site/js/calc/export.js';
import { precursorLine } from './site/js/calc/precursor.js';
import { csvText } from './site/js/ui/csv.js';

// 열연 코일(공정 벤치마크와 경로 셋), 강관(열연 코일이 전구물질), 합금강(등급이 여럿이고 연도 구간마다 값이 다름), 클링커(세부 품목 둘), 포틀랜드 시멘트(간접배출량을 세고 공정 벤치마크가 0)
const book = unpack({
  asOf: '2026-11-11', years: { from: 2026, to: 2034 }, periods: [{ key: 1, from: 2026, to: 2027 }, { key: 2, from: 2028, to: 2030 }],
  cscf: { 2026: 100, 2027: 100, 2028: 100, 2029: 100, 2030: 100 },
  markups: [{ sectors: ['cement', 'steel'], values: { 2026: 10, 2027: 20, 2028: 30 } }],
  routes: [{ key: 'A', name: '회색' }, { key: 'B', name: '백색' }, { key: 'C', name: '고로·전로' }, { key: 'D', name: '직접환원철·전기로' }, { key: 'E', name: '철스크랩·전기로' },
    { key: 'F', name: '저합금강, 고로·전로' }, { key: 'H', name: '저합금강, 철스크랩·전기로' }, { key: 'J', name: '고합금강(전기로)' }],
  rows: [['7208', 'Flat-rolled', 'kr', 2.118, null, 2.118], ['7306 30 77', 'Tubes', 'kr', 2.164, null, 2.164], ['722540', 'Alloy flat-rolled', 'kr', 4.03, null, 4.03],
    ['2523100010', 'White clinker', 'kr', 1.19, 0.04, 1.23], ['2523100090', 'Grey clinker', 'kr', 0.88, 0.03, 0.92], ['2523 29 00', 'Grey Portland cement', 'kr', 0.89, 0.06, 0.94]],
  goods: [
    ['72081000', 'Hot-rolled coil', 'steel', [[0.044, '', 0]], [[1.37, 'C', 0], [0.481, 'D', 0], [0.072, 'E', 0]], [[0, 'C', 1.37, 1.37]]],
    ['73063077', 'Welded tubes', 'steel', [[0.112, '', 0]], [[1.491, 'C', 0], [0.567, 'D', 0], [0.141, 'E', 0]], [[1, 'C', 1.491, 1.491]]],
    ['72254015', 'High-speed steel', 'steel', [[0.073, '', 0]], [[1.577, 'F', 1], [1.409, 'F', 2], [0.7, 'H', 0], [0.95, 'J', 1], [0.918, 'J', 2]], [[2, 'F', 1.577, 1.409]]],
    ['25231000', 'Cement clinkers', 'cement', [[0.666, 'A', 0], [0.859, 'B', 0]], [[0.666, 'A', 0], [0.859, 'B', 0]], [[3, 'B', 0.859, 0.859], [4, 'A', 0.666, 0.666]]],
    ['25232900', 'Portland cement', 'cement', [[0.0, '', 0]], [[0.666, '', 0]], [[5, '', 0.666, 0.666]]],
  ],
});
const path = { values: { 2026: 97.5, 2027: 95, 2028: 90, 2029: 77.5, 2030: 51.5, 2031: 39, 2032: 26.5, 2033: 14, 2034: 0 } };
const prices = { prices: [{ from: '2026-01-01', value: 75.36 }, { from: '2026-04-01', value: 75.28 }, { from: '2026-07-01', value: 82.32 }], upcoming: [{ from: '2026-10-01' }] };
const good = (code) => book.goods.find((one) => one.code === code);
const coil = good('72081000'); const tube = good('73063077'); const alloy = good('72254015'); const clinker = good('25231000'); const cement = good('25232900');
const base = { good: tube, mode: 'actual', year: 2026, tonnes: 100, price: 80, route: 'C' };
const run = (more) => estimate(book, path, { ...base, ...more });
const pick = (row) => row && { embedded: row.embedded, parts: row.parts, benchmark: row.benchmark, column: row.column, allocation: row.allocation, process: row.process,
  inputAllocation: row.inputAllocation, perTonne: row.perTonne, relieved: row.relieved, certificates: row.certificates, cost: row.cost,
  lines: row.lines.map((line) => ({ code: line.good.code, mass: line.mass, see: line.see, sefa: line.sefa, embedded: line.embedded, allocation: line.allocation })),
  deduction: row.deduction && { how: row.deduction.how, euros: row.deduction.euros, certificates: row.deduction.certificates, ref: row.deduction.ref, refFrom: row.deduction.refFrom, detail: row.deduction.detail || null } };
const listed = { pre: 'listed', precursors: [{ good: coil, mass: 1.05 }] };
console.log(JSON.stringify({
  simple: pick(run({ direct: 2.0 })),
  alias: pick(run({ see: 2.0 })),
  whole: pick(run({ direct: 2.0, scope: 'whole', ...listed })),
  process: pick(run({ direct: 0.08, scope: 'process', ...listed })),
  given: pick(run({ direct: 0.08, scope: 'process', pre: 'listed', precursors: [{ good: coil, mass: 1.05, see: 1.9, sefa: 1.2 }] })),
  unfinished: pick(run({ direct: 2.0, pre: 'listed', precursors: [{ good: coil, mass: '' }, { good: null, mass: 1 }, { good: coil, mass: 0 }] })),
  otherRoute: pick(run({ direct: 2.0, pre: 'listed', precursors: [{ good: coil, mass: 1, route: 'E' }] })),
  noDirect: run({ direct: '', ...listed }),
  directOnly: pick(run({ direct: 2.0, indirect: 0.5 })),
  years: series(book, path, { ...base, direct: 0.08, scope: 'process', pre: 'listed', precursors: [{ good: coil, mass: 1, sefa: 1.2 }] })
    .map((row) => [row.year, row.lines[0].see.value, row.lines[0].see.markup, row.lines[0].sefa.value, row.lines[0].sefa.given, row.lines[0].sefa.scaled]),
  lateBase: [2033, 2034].map((year) => { const line = precursorLine(book, path, { good: coil, mass: 1, sefa: 0.5 }, year, 2034); return [line.sefa.value, line.sefa.given]; }),
  alloy: [2026, 2028].map((year) => [defaultBenchmarkAt(alloy, alloy.defaults[0], period(book, year)), defaultBenchmarkAt(alloy, alloy.defaults[0], period(book, year), 'H'),
    defaultBenchmarkAt(alloy, alloy.defaults[0], period(book, year), 'J'), defaultBenchmarkAt(alloy, alloy.defaults[0], period(book, year), 'Z')]),
  cement: pick(estimate(book, path, { good: cement, mode: 'actual', year: 2026, tonnes: 10, price: 80, direct: 0.75, indirect: 0.05, scope: 'whole', pre: 'listed',
    precursors: [{ good: clinker, choice: 1, mass: 0.85 }] })),
  cementProcess: pick(estimate(book, path, { good: cement, mode: 'actual', year: 2027, tonnes: 10, price: 80, direct: 0.02, indirect: 0.05, scope: 'process', pre: 'listed',
    precursors: [{ good: clinker, choice: 1, mass: 0.85 }, { good: clinker, choice: 0, mass: 0.05 }] })),
  reference: [referencePrice(prices, 2026), referencePrice(prices, 2027), referencePrice({ prices: [{ from: '2027-01-04', value: 80.004 }, { from: '2027-01-11', value: 81 }] }, 2027), referencePrice(null, 2026)],
  report: pick(run({ direct: 2.0, prices, carbon: { how: 'paid', entry: 'report', perTonne: 10 } })),
  reportGivenRef: pick(run({ direct: 2.0, prices, carbon: { how: 'paid', entry: 'report', perTonne: 10, ref: 80 } })),
  built: pick(run({ direct: 2.0, prices, carbon: { how: 'paid', entry: 'build', price: 10000, free: 90, rate: 1500, other: 0.5 } })),
  builtCovered: paid({ entry: 'build', price: 10000, covered: 1.5, free: 120, rate: 1500 }, 2.0),
  builtShort: [paid({ entry: 'build', price: 10000, rate: 0 }, 2.0), paid({ entry: 'build', rate: 1500 }, 2.0), paid({ entry: 'build', price: 1, rate: 1 }, null), paid({ entry: 'report', perTonne: '' }, 2.0)],
  defaultPrice: pick(run({ direct: 2.0, prices, carbon: { how: 'default', dcp: 5 } })),
  defaultMode: pick(estimate(book, path, { good: tube, mode: 'default', year: 2027, tonnes: 100, price: 70, prices, carbon: { how: 'default', dcp: 5 } })),
  defaultModePaid: pick(estimate(book, path, { good: tube, mode: 'default', year: 2026, tonnes: 100, price: 80, prices, carbon: { how: 'paid', entry: 'report', perTonne: 10 } })),
  capped: pick(run({ direct: 1.5, prices, carbon: { how: 'paid', entry: 'report', perTonne: 500 } })),
  none: pick(run({ direct: 2.0, prices, carbon: { how: 'none', perTonne: 10 } })),
  empty: pick(run({ direct: 2.0, prices, carbon: { how: 'paid', entry: 'report', perTonne: '' } })),
  yearsCarbon: series(book, path, { ...base, direct: 2.0, prices, carbon: { how: 'paid', entry: 'report', perTonne: 10 } }).map((row) => [row.year, row.deduction.ref, row.deduction.refFrom]).slice(0, 2),
  even: {
    simple: breakEven(book, path, { ...base, direct: 5 }),
    never: breakEven(book, path, { ...base, direct: 0.08, scope: 'process', ...listed }),
    below: breakEven(book, path, { ...base, direct: 0.08, scope: 'process', pre: 'listed', precursors: [{ good: coil, mass: 1.05, see: 1.9 }] }),
    nothingDue: breakEven(book, { values: { 2026: 200 } }, { ...base, direct: 1 }),
    untouched: breakEven(book, path, { ...base, direct: '' }),
  },
  yearly: yearlyRows(book, path, { ...base, direct: 2.0 }).slice(0, 2),
  basket: (() => {
    const found = basketRows(book, [{ input: { ...base, direct: 2.0 }, path: { ...path, name: '현행 지침' } }, { input: { ...base, direct: 1.0, tonnes: 50 }, path }, { input: { ...base, direct: '' }, path }]);
    return { rows: found.rows, lines: found.lines.map((line) => Boolean(line.row)), certificates: found.certificates, cost: found.cost };
  })(),
  csv: csvText([['a', 'b,c', 'd "e"'], [1, null, 'x\ny']]),
}));
"""


@unittest.skipUnless(shutil.which("node"), "node가 없으면 화면의 셈은 시험하지 않는다")
class DetailTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = pathlib.Path(__file__).resolve().parent.parent
        done = subprocess.run(["node", "--input-type=module", "-e", SCRIPT], capture_output=True, text=True, cwd=root)
        if done.returncode:
            raise AssertionError(done.stderr)
        cls.got = json.loads(done.stdout)

    def near(self, value, expected, places=9):
        self.assertAlmostEqual(value, expected, places=places)

    def test_without_precursors_the_default_benchmark_stands_in(self):
        row = self.got["simple"]
        self.assertEqual((row["column"], row["benchmark"], row["lines"]), ("B", 1.491, []))
        self.near(row["allocation"], 1.491 * 0.975)
        self.near(row["perTonne"], 2.0 - 1.491 * 0.975)
        self.assertEqual(row["parts"], {"direct": 2.0, "indirect": 0, "inputs": 0})
        self.assertEqual(self.got["alias"]["perTonne"], row["perTonne"])  # 옛 이름(see)으로 넣어도 같다

    def test_listed_precursors_switch_to_the_process_benchmark_plus_each_precursor(self):
        row = self.got["whole"]
        self.assertEqual((row["column"], row["benchmark"]), ("A", 0.112))
        self.near(row["process"], 0.112 * 0.975)
        self.near(row["inputAllocation"], 1.05 * 1.37 * 0.975)
        self.near(row["allocation"], 0.112 * 0.975 + 1.05 * 1.37 * 0.975)
        self.near(row["embedded"], 2.0)                                   # 넣은 값이 제품 전체의 값이면 전구물질의 배출량을 더하지 않는다
        line = row["lines"][0]
        self.assertEqual((line["code"], line["mass"], line["sefa"]["given"], line["sefa"]["route"], line["sefa"]["benchmark"]), ("72081000", 1.05, False, "C", 1.37))
        self.near(row["certificates"], (2.0 - row["allocation"]) * 100)
        self.near(row["cost"], (2.0 - row["allocation"]) * 100 * 80)

    def test_process_scope_adds_the_precursors_with_default_values_and_markup(self):
        row = self.got["process"]
        self.near(row["lines"][0]["see"]["value"], 2.118 * 1.10)
        self.assertEqual((row["lines"][0]["see"]["given"], row["lines"][0]["see"]["markup"], row["lines"][0]["see"]["total"]), (False, 10, 2.118))
        self.near(row["parts"]["inputs"], 1.05 * 2.118 * 1.10)
        self.near(row["embedded"], 0.08 + 1.05 * 2.118 * 1.10)

    def test_values_given_for_a_precursor_replace_the_defaults(self):
        row = self.got["given"]
        self.near(row["embedded"], 0.08 + 1.05 * 1.9)
        self.near(row["allocation"], 0.112 * 0.975 + 1.05 * 1.2)
        self.assertEqual((row["lines"][0]["see"]["given"], row["lines"][0]["see"]["markup"], row["lines"][0]["sefa"]["given"]), (True, None, True))

    def test_unfinished_lines_are_left_out_and_a_missing_direct_value_gives_no_estimate(self):
        row = self.got["unfinished"]
        self.assertEqual(row["lines"], [])
        self.near(row["allocation"], 0.112 * 0.975)                        # 전구물질을 따로 넣기로 했으면 공정 벤치마크만 남는다
        self.assertIsNone(self.got["noDirect"])

    def test_a_precursor_made_by_another_route_takes_that_routes_benchmark(self):
        line = self.got["otherRoute"]["lines"][0]
        self.assertEqual((line["sefa"]["route"], line["sefa"]["benchmark"]), ("E", 0.072))
        self.near(line["allocation"], 0.072 * 0.975)

    def test_goods_that_count_direct_emissions_only_ignore_an_indirect_value(self):
        self.assertEqual(self.got["directOnly"]["parts"]["indirect"], 0)
        self.near(self.got["directOnly"]["embedded"], 2.0)

    def test_over_the_years_defaults_follow_the_year_and_a_given_allocation_is_scaled_by_the_factor(self):
        years = {row[0]: row[1:] for row in self.got["years"]}
        self.near(years[2026][0], 2.118 * 1.10)
        self.near(years[2027][0], 2.118 * 1.20)
        self.near(years[2029][0], 2.118 * 1.30)
        self.assertEqual([years[year][1] for year in (2026, 2027, 2028)], [10, 20, 30])
        self.assertEqual(years[2026][2:], [1.2, True, False])              # 넣은 해에는 넣은 값 그대로
        self.near(years[2028][2], 1.2 * 0.90 / 0.975)
        self.assertEqual(years[2028][3:], [True, True])
        self.near(years[2034][2], 0)                                       # 계수가 0인 해에는 무상할당도 0
        # 넣은 해의 계수가 0이면 다른 해의 값은 알 수 없어 기본 벤치마크로 정한다
        self.near(self.got["lateBase"][0][0], 1.37 * 0.14)
        self.assertEqual((self.got["lateBase"][0][1], self.got["lateBase"][1]), (False, [0.5, True]))

    def test_alloy_grades_take_the_higher_benchmark_whatever_route_is_chosen(self):
        first, later = self.got["alloy"]
        self.assertEqual(first[0], {"value": 1.577, "route": "F", "routeAlt": "J"})
        self.assertEqual(first[1], {"value": 0.95, "route": "H", "routeAlt": "J"})   # 저합금강(철스크랩) 0.7과 고합금강 0.95 가운데 큰 값
        self.assertEqual(first[2], {"value": 0.95, "route": "J", "routeAlt": ""})
        self.assertEqual(first[3], first[0])                                          # 모르는 경로는 기본값 표의 경로
        self.assertEqual((later[0]["value"], later[1]["value"]), (1.409, 0.918))

    def test_cement_counts_indirect_emissions_and_gets_its_allocation_from_the_clinker(self):
        row = self.got["cement"]
        self.assertEqual(row["parts"], {"direct": 0.75, "indirect": 0.05, "inputs": 0})
        self.assertEqual((row["column"], row["benchmark"], row["process"]), ("A", 0.0, 0))
        self.near(row["allocation"], 0.85 * 0.666 * 0.975)
        self.assertEqual(row["lines"][0]["sefa"]["route"], "A")
        later = self.got["cementProcess"]
        self.near(later["embedded"], 0.02 + 0.05 + (0.85 * 0.92 + 0.05 * 1.23) * 1.20)
        self.near(later["allocation"], (0.85 * 0.666 + 0.05 * 0.859) * 0.95)

    def test_the_reference_price_is_the_mean_of_the_prices_published_for_the_year(self):
        first, missing, weekly, nothing = self.got["reference"]
        self.assertEqual(first, {"value": 77.65, "count": 3, "partial": True})
        self.assertIsNone(missing)
        self.assertEqual(weekly, {"value": 80.5, "count": 2, "partial": True})   # 1월의 주간 가격 둘뿐이다: 그해의 가격이 더 남아 있다
        self.assertIsNone(nothing)

    def test_a_certified_carbon_price_is_divided_by_the_reference_price(self):
        row = self.got["report"]
        self.assertEqual((row["deduction"]["how"], row["deduction"]["ref"], row["deduction"]["refFrom"]), ("paid", 77.65, "partial"))
        self.near(row["deduction"]["certificates"], 10 / 77.65)
        self.near(row["relieved"], 10 / 77.65)
        self.near(row["perTonne"], 2.0 - 1.491 * 0.975 - 10 / 77.65)
        stated = self.got["reportGivenRef"]["deduction"]
        self.assertEqual((stated["ref"], stated["refFrom"]), (80, "given"))
        self.near(stated["certificates"], 0.125)
        self.assertEqual(self.got["yearsCarbon"], [[2026, 77.65, "partial"], [2027, 80, "price"]])  # 가격이 공개되지 않은 해에는 넣은 인증서 가격

    def test_a_carbon_price_can_be_built_from_the_price_the_free_share_and_the_exchange_rate(self):
        row = self.got["built"]
        detail = row["deduction"]["detail"]
        self.assertEqual((detail["covered"], detail["free"], detail["price"], detail["rate"], detail["other"]), (2.0, 90, 10000, 1500, 0.5))
        self.near(detail["charged"], 0.2)
        self.near(detail["direct"], 0.2 * 10000 / 1500)
        self.near(row["deduction"]["euros"], 0.2 * 10000 / 1500 + 0.5)
        self.near(row["deduction"]["certificates"], (0.2 * 10000 / 1500 + 0.5) / 77.65)
        covered = self.got["builtCovered"]
        self.assertEqual((covered["covered"], covered["free"], covered["euros"]), (1.5, 100, 0))   # 무상 몫은 100%를 넘지 않는다
        self.assertEqual(self.got["builtShort"], [None, None, None, None])

    def test_a_default_carbon_price_is_multiplied_by_the_declared_emissions(self):
        row = self.got["defaultPrice"]
        self.assertEqual(row["deduction"]["how"], "default")
        self.near(row["deduction"]["euros"], 5 * 2.0)
        self.near(row["deduction"]["certificates"], 10 / 77.65)
        other = self.got["defaultMode"]
        self.near(other["embedded"], 2.164 * 1.20)
        self.near(other["deduction"]["euros"], 5 * 2.164 * 1.20)
        self.assertEqual((other["deduction"]["ref"], other["deduction"]["refFrom"]), (70, "price"))
        self.near(other["perTonne"], 2.164 * 1.20 - 1.491 * 0.95 - 5 * 2.164 * 1.20 / 70)

    def test_default_values_cannot_claim_a_paid_carbon_price_and_the_deduction_stops_at_zero(self):
        self.assertIsNone(self.got["defaultModePaid"]["deduction"])
        capped = self.got["capped"]
        self.near(capped["relieved"], 1.5 - 1.491 * 0.975)
        self.assertEqual((capped["perTonne"], capped["certificates"], capped["cost"]), (0, 0, 0))
        self.assertIsNone(self.got["none"]["deduction"])
        self.assertIsNone(self.got["empty"]["deduction"])
        self.assertEqual(self.got["empty"]["relieved"], 0)

    def test_the_break_even_point_is_the_direct_emissions_that_match_default_values(self):
        even = self.got["even"]
        self.assertEqual(even["simple"]["kind"], "below")
        self.near(even["simple"]["direct"], 2.164 * 1.10, places=7)      # 벤치마크가 같으면 기본값(마크업 포함)과 같아지는 곳
        self.assertEqual(even["never"], {"kind": "never"})               # 전구물질의 기본값(마크업 포함)만으로 이미 더 크다
        self.assertEqual(even["below"]["kind"], "below")
        base = 2.164 * 1.10 - 1.491 * 0.975
        self.near(even["below"]["direct"], base + (0.112 * 0.975 + 1.05 * 1.37 * 0.975) - 1.05 * 1.9, places=7)
        self.assertIsNone(even["nothingDue"])                            # 기본값으로 신고해도 인증서가 없으면 견줄 것이 없다
        self.assertEqual(even["untouched"]["kind"], "below")             # 직접배출량을 넣기 전에도 찾을 수 있다

    def test_the_tables_to_download_carry_plain_numbers(self):
        head, first = self.got["yearly"]
        self.assertEqual(head[:4], ["year", "cn_code", "method", "tonnes"])
        row = dict(zip(head, first))
        self.assertEqual((row["year"], row["cn_code"], row["method"], row["tonnes"], row["certificate_price_eur"], row["cbam_factor_percent"]), (2026, "73063077", "actual emissions", 100, 80, 97.5))
        self.near(row["certificates_per_t"], round(2.0 - 1.491 * 0.975, 4))
        self.assertEqual(row["includes_assumed_values"], "no")
        basket = self.got["basket"]
        self.assertEqual(basket["lines"], [True, True, False])           # 아직 추정할 수 없는 것은 줄에 싣지 않는다
        self.assertEqual(len(basket["rows"]), 4)                          # 머리 줄, 추정 둘, 합계
        self.near(basket["certificates"], (2.0 - 1.491 * 0.975) * 100)   # 둘째 품목은 0(무상할당 조정이 더 크다): 남은 몫을 첫째에서 빼지 않는다
        self.near(basket["cost"], (2.0 - 1.491 * 0.975) * 100 * 80)
        self.assertEqual(basket["rows"][1][6], "현행 지침")
        self.assertEqual(basket["rows"][-1][0], "total")
        self.assertEqual(self.got["csv"], 'a,"b,c","d ""e"""\r\n1,,"x\ny"\r\n')


if __name__ == "__main__":
    unittest.main()
