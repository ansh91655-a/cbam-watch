"""수입 연도에 맞는 인증서 가격 고르기(site/js/calc/prices.js)와 그 칸의 도움말(site/js/views/calc/price.js의 priceHint, startPrice).

2026년 수입분에는 수입한 분기의 가격이, 2027년부터는 인증서를 사는 때의 주간 가격이 적용된다(이행규정 (EU) 2025/2548 제1조(6), 제5조).
화면 요소를 다루지 않는 부분만 node로 본다."""
import json
import pathlib
import shutil
import subprocess
import unittest

SCRIPT = r"""
import { atPurchase, byQuarter, latestPrice, periodsOf, pricedYears, priceOf, suggest, yearMean } from './site/js/calc/prices.js';
import { referencePrice } from './site/js/calc/carbon.js';
import { CUSTOM, priceHint, startPrice } from './site/js/views/calc/price.js';

// 2026년 11월의 자료: 분기 가격 셋과 게시 예정인 4분기
const now = {
  prices: [
    { period: '2026-Q1', kind: 'quarter', label: '2026년 1분기', from: '2026-01-01', to: '2026-03-31', published: '2026-04-07', value: 75.36 },
    { period: '2026-Q2', kind: 'quarter', label: '2026년 2분기', from: '2026-04-01', to: '2026-06-30', published: '2026-07-06', value: 75.28 },
    { period: '2026-Q3', kind: 'quarter', label: '2026년 3분기', from: '2026-07-01', to: '2026-09-30', published: '2026-10-05', value: 82.32 },
  ],
  upcoming: [{ period: '2026-Q4', kind: 'quarter', label: '2026년 4분기', from: '2026-10-01', to: '2026-12-31', published: '2027-01-04' }],
};
// 2027년 1월의 자료: 4분기 가격이 게시되고 주간 가격이 둘 실림
const later = {
  prices: [...now.prices,
    { period: '2026-Q4', kind: 'quarter', label: '2026년 4분기', from: '2026-10-01', to: '2026-12-31', published: '2027-01-04', value: 79.15 },
    { period: '2027-01-04', kind: 'week', label: '2027년 1주(1월 4일~1월 10일)', from: '2027-01-04', to: '2027-01-10', published: '2027-01-11', value: 80.02 },
    { period: '2027-01-11', kind: 'week', label: '2027년 2주(1월 11일~1월 17일)', from: '2027-01-11', to: '2027-01-17', published: '2027-01-18', value: 81.5 },
  ],
  upcoming: [],
};

console.log(JSON.stringify({
  periods: periodsOf(now, 2026).map((row) => [row.period, row.value, row.published]),
  none: periodsOf(now, 2027),
  latest: [latestPrice(now).period, latestPrice(later).period, latestPrice({ prices: [] }), latestPrice(null)],
  quarterly: [byQuarter(now, 2026), byQuarter(now, 2027), byQuarter(later, 2027), byQuarter(null, 2026)],
  atPurchase: [atPurchase(2026), atPurchase(2027), atPurchase(2030)],
  suggest: [suggest(now, 2026), suggest(now, 2027), suggest(later, 2027), suggest({ prices: [] }, 2026)],
  priceOf: [priceOf(now, 2026, '2026-Q1'), priceOf(now, 2026, '2026-Q4'), priceOf(now, 2026, '2027-01-04'), priceOf(now, 2027, '2026-Q1')],
  means: [yearMean(now, 2026), yearMean(later, 2026), yearMean(later, 2027), yearMean(now, 2027)],
  sameAsReference: [yearMean(now, 2026).value === referencePrice(now, 2026).value, yearMean(later, 2027).value === referencePrice(later, 2027).value],
  years: [pricedYears(now), pricedYears(later), pricedYears(null)],
  start: [startPrice(now, 2026), startPrice(now, 2027), startPrice(later, 2027)],
  hints: {
    quarter: priceHint(now, { year: 2026, period: '2026-Q3' }),
    unpublished: priceHint(now, { year: 2026, period: '2026-Q4' }),
    customQuarter: priceHint(now, { year: 2026, period: CUSTOM }),
    nextYear: priceHint(now, { year: 2027, period: '' }),
    weekly: priceHint(later, { year: 2027, period: '' }),
    customWeekly: priceHint(later, { year: 2027, period: CUSTOM }),
    nothing: priceHint({ prices: [] }, { year: 2028, period: '' }),
  },
}));
"""


@unittest.skipUnless(shutil.which("node"), "node가 없으면 화면의 셈은 시험하지 않는다")
class PricePickingTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = pathlib.Path(__file__).resolve().parent.parent
        done = subprocess.run(["node", "--input-type=module", "-e", SCRIPT], capture_output=True, text=True, cwd=root)
        if done.returncode:
            raise AssertionError(done.stderr)
        cls.got = json.loads(done.stdout)

    def test_the_periods_of_a_year_come_in_order_with_the_unpublished_ones(self):
        self.assertEqual(self.got["periods"], [["2026-Q1", 75.36, "2026-04-07"], ["2026-Q2", 75.28, "2026-07-06"], ["2026-Q3", 82.32, "2026-10-05"], ["2026-Q4", None, "2027-01-04"]])
        self.assertEqual(self.got["none"], [])

    def test_the_latest_published_price_is_found_whatever_the_year(self):
        self.assertEqual(self.got["latest"], ["2026-Q3", "2027-01-11", None, None])

    def test_2026_is_picked_by_quarter_and_later_years_by_the_week_of_purchase(self):
        self.assertEqual(self.got["quarterly"], [True, False, False, False])
        self.assertEqual(self.got["atPurchase"], [False, True, True])

    def test_the_price_put_in_first_follows_the_year_of_import(self):
        this_year, next_year, weekly, nothing = self.got["suggest"]
        self.assertEqual((this_year["value"], this_year["period"], this_year["from"]), (82.32, "2026-Q3", "period"))
        # 그해의 가격이 아직 없으면 가장 최근에 게시된 가격을 넣고, 어느 기간의 가격인지 적는다
        self.assertEqual((next_year["value"], next_year["period"], next_year["label"], next_year["from"]), (82.32, "", "2026년 3분기", "latest"))
        self.assertEqual((weekly["value"], weekly["period"], weekly["from"]), (81.5, "2027-01-11", "period"))
        self.assertEqual((nothing["value"], nothing["from"]), (0, "none"))
        # 조건에 넣는 꼴: 분기를 고르는 해에만 기간을 적는다(주간 가격의 해는 사는 때에 달려 있어 기간을 고르지 않는다)
        self.assertEqual(self.got["start"], [{"price": 82.32, "period": "2026-Q3"}, {"price": 82.32, "period": ""}, {"price": 81.5, "period": ""}])

    def test_a_picked_period_gives_its_price_only_when_it_is_published_and_of_that_year(self):
        first, unpublished, other_year, wrong_year = self.got["priceOf"]
        self.assertEqual(first, {"value": 75.36, "label": "2026년 1분기"})
        self.assertEqual([unpublished, other_year, wrong_year], [None, None, None])

    def test_the_yearly_mean_matches_the_reference_price_of_the_deduction(self):
        partial, whole, weekly, missing = self.got["means"]
        self.assertEqual((partial["value"], partial["count"], partial["partial"], partial["kind"]), (77.65, 3, True, "quarter"))   # (75.36 + 75.28 + 82.32) / 3
        self.assertEqual((whole["value"], whole["count"], whole["partial"]), (78.03, 4, False))                                   # 312.11 / 4 = 78.0275
        self.assertEqual((weekly["value"], weekly["count"], weekly["kind"], weekly["partial"]), (80.76, 2, "week", True))   # 그해가 끝나지 않았다
        self.assertIsNone(missing)
        self.assertEqual(self.got["sameAsReference"], [True, True])
        self.assertEqual(self.got["years"], [[2026], [2026, 2027], []])

    def test_the_hint_says_which_price_applies_and_which_one_was_put_in(self):
        hints = self.got["hints"]
        self.assertEqual(hints["quarter"], "2026년 수입분에는 수입한 분기의 가격이 적용됩니다. 2026년 3분기 가격 82.32유로를 넣었습니다.")
        self.assertIn("2026년 4분기 가격은 2027년 1월 4일", hints["unpublished"])
        self.assertIn("가격을 직접 넣어 주세요", hints["unpublished"])
        self.assertIn("직접 넣은 값", hints["customQuarter"])
        self.assertIn("인증서를 사는 때의 주간 가격이 적용됩니다", hints["nextYear"])
        self.assertIn("가장 최근에 게시된 2026년 3분기 가격 82.32유로", hints["nextYear"])
        self.assertIn("2027년 2주(1월 11일~1월 17일) 가격 81.50유로", hints["weekly"])
        self.assertIn("직접 넣은 값", hints["customWeekly"])
        self.assertIn("가격을 직접 넣어 주세요", hints["nothing"])


if __name__ == "__main__":
    unittest.main()
