"""첫 화면에 먼저 보일 소식의 차례(site/js/news/lead.js)와 중요도의 이름(site/js/news/importance.js)."""
import json
import pathlib
import shutil
import subprocess
import unittest

SCRIPT = r"""
import { HIGH, HIGH_NAME, IMPORTANCE, isHigh, isLow, LOW } from './site/js/news/importance.js';
import { leadFirst } from './site/js/news/lead.js';
const items = [
  { id: 'low-new', published: '2026-11-13', importance: '낮음' },
  { id: 'mid-new', published: '2026-11-12', importance: '보통' },
  { id: 'high', published: '2026-11-01', importance: '높음' },
  { id: 'plain', published: '2026-10-20' },
  { id: 'low-2', published: '2026-10-18', importance: '낮음' },
  { id: 'mid-old', published: '2026-09-01', importance: '보통' },
  { id: 'low-old', published: '2026-08-01', importance: '낮음' },
];
const dateOf = (item) => item.published;
const ids = (rows) => rows.map((item) => item.id);
console.log(JSON.stringify({
  ordered: ids(leadFirst(items, '2026-11-14', dateOf)),
  week: ids(leadFirst(items, '2026-11-14', dateOf, 7)),
  none: leadFirst([], '2026-11-14', dateOf),
  same: leadFirst(items, '2026-11-14', dateOf).length === items.length,
  names: { HIGH, LOW, HIGH_NAME, IMPORTANCE },
  marks: [isHigh({ importance: '높음' }), isHigh({ importance: '보통' }), isHigh(null), isLow({ importance: '낮음' }), isLow({})],
}));
"""


@unittest.skipUnless(shutil.which("node"), "node가 없으면 화면의 셈은 시험하지 않는다")
class LeadTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        done = subprocess.run(["node", "--input-type=module", "-e", SCRIPT], capture_output=True, text=True)
        if done.returncode:
            raise AssertionError(done.stderr[-1500:])
        cls.seen = json.loads(done.stdout)

    def test_recent_news_of_some_weight_comes_before_the_light_ones(self):
        # 최근 30일의 보통 이상(중요도가 없는 것도) → 최근 30일의 낮음 → 그보다 오래된 것. 갈래 안에서는 날짜 차례 그대로
        self.assertEqual(self.seen["ordered"], ["mid-new", "high", "plain", "low-new", "low-2", "mid-old", "low-old"])
        self.assertEqual(self.seen["week"], ["mid-new", "low-new", "high", "plain", "low-2", "mid-old", "low-old"])   # 날수를 줄이면 그 안의 것만 앞으로 온다
        self.assertEqual(self.seen["none"], [])
        self.assertTrue(self.seen["same"])                                                                          # 빠지는 소식은 없다

    def test_the_badge_and_the_filter_use_one_name(self):
        names = self.seen["names"]
        self.assertEqual((names["HIGH"], names["LOW"], names["HIGH_NAME"]), ("높음", "낮음", "중요"))
        self.assertEqual(names["IMPORTANCE"], [{"value": "높음", "text": "중요"}, {"value": "보통", "text": "보통"}, {"value": "낮음", "text": "낮음"}])
        self.assertEqual(self.seen["marks"], [True, False, False, True, False])
        for name in ("site/js/ui/card.js", "site/js/views/item.js"):
            text = pathlib.Path(name).read_text(encoding="utf-8")
            self.assertIn('isHigh(item) ? h("span", { class: "m-imp", text: HIGH_NAME })', text, name)
        self.assertIn('select("news-importance", "중요도", IMPORTANCE,', pathlib.Path("site/js/views/news.js").read_text(encoding="utf-8"))

    def test_the_first_screen_uses_the_order(self):
        home = pathlib.Path("site/js/views/home.js").read_text(encoding="utf-8")
        self.assertIn("const ordered = leadFirst(dated, today(), data.dateOf);", home)
        self.assertIn("hero(book, events, items, dated, ordered)", home)
        self.assertIn("ticker(ordered)", pathlib.Path("site/js/views/home/hero.js").read_text(encoding="utf-8"))

    def test_the_data_uses_only_the_three_values(self):
        items = json.loads(pathlib.Path("data/items.json").read_text(encoding="utf-8"))["items"]
        self.assertLessEqual({item.get("importance") for item in items} - {None, ""}, {"높음", "보통", "낮음"})


if __name__ == "__main__":
    unittest.main()
