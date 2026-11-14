"""규제 변화 기록(site/js/rules/changes.js): 규제마다의 연혁을 합쳐 최근 며칠 안에 달라진 것만 고르는 것과 그 화면의 주소."""
import json
import pathlib
import shutil
import subprocess
import unittest

SCRIPT = r"""
import { changes, hrefOf, periodOf, PERIODS, RECENT } from './site/js/rules/changes.js';
const rules = [
  { id: 'a', name: '가 규제', timeline: [
    { date: '2026-05-01', text: '오래된 일' }, { date: '2026-10-20', text: '가의 첫 일' }, { date: '2026-11-12', text: '가의 둘째 일' },
    { date: '2026-11-12', text: '가의 셋째 일', press: true }, { date: '2026-12-01', text: '앞날의 일' }, { date: '2026-11', text: '달만 적힌 일' }] },
  { id: 'b', name: '나 규제', timeline: [{ date: '2026-11-12', text: '나의 일' }, { date: '2026-08-20', text: '석 달 안의 일' }, { date: '2026-08-16', text: '90일째의 일' }, { date: '2026-08-15', text: '91일째의 일' }] },
  { id: 'c', name: '연혁이 없는 규제' },
];
const brief = (rows) => rows.map((row) => `${row.date} ${row.rule.id} ${row.text}`);
console.log(JSON.stringify({
  recent: RECENT, periods: PERIODS,
  month: brief(changes(rules, '2026-11-14')),
  quarter: brief(changes(rules, '2026-11-14', 90)),
  none: changes([], '2026-11-14'),
  kept: changes(rules, '2026-11-14')[0],
  period: Object.fromEntries(['recent', 'recent-90', 'recent-30', 'recent-7', 'recent-x', 'eu-law', '', 'recently'].map((arg) => [arg, periodOf(arg)])),
  href: [hrefOf(), hrefOf(30), hrefOf(90)],
}));
"""


@unittest.skipUnless(shutil.which("node"), "node가 없으면 화면의 셈은 시험하지 않는다")
class ChangesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        done = subprocess.run(["node", "--input-type=module", "-e", SCRIPT], capture_output=True, text=True)
        if done.returncode:
            raise AssertionError(done.stderr[-1500:])
        cls.seen = json.loads(done.stdout)

    def test_the_latest_entries_of_all_rules_come_newest_first(self):
        # 날짜가 늦은 것부터, 같은 날이면 규제의 차례대로, 한 규제 안에서는 나중에 적힌 것부터. 앞날의 일과 날짜가 아닌 것은 뺀다
        self.assertEqual(self.seen["month"], ["2026-11-12 a 가의 셋째 일", "2026-11-12 a 가의 둘째 일", "2026-11-12 b 나의 일", "2026-10-20 a 가의 첫 일"])
        self.assertEqual(self.seen["quarter"][-2:], ["2026-08-20 b 석 달 안의 일", "2026-08-16 b 90일째의 일"])   # 90일째까지 들고 91일째는 빠진다
        self.assertEqual(len(self.seen["quarter"]), 6)
        self.assertEqual(self.seen["none"], [])

    def test_an_entry_keeps_its_fields_and_names_its_rule(self):
        kept = self.seen["kept"]
        self.assertEqual((kept["date"], kept["text"], kept["press"], kept["rule"]["id"], kept["rule"]["name"]), ("2026-11-12", "가의 셋째 일", True, "a", "가 규제"))

    def test_the_address_tells_the_period(self):
        self.assertEqual(self.seen["periods"], [30, 90])
        self.assertEqual(self.seen["period"], {"recent": 30, "recent-90": 90, "recent-30": 30, "recent-7": 30, "recent-x": 30, "eu-law": 0, "": 0, "recently": 0})
        self.assertEqual(self.seen["href"], ["#rules-recent", "#rules-recent", "#rules-recent-90"])


class RepositoryTest(unittest.TestCase):
    def test_no_rule_or_group_is_named_like_the_change_log(self):
        """#rules-recent는 변화 기록의 주소다. 규제나 묶음의 이름이 이 말로 시작하면 그 화면에 갈 수 없다."""
        body = json.loads(pathlib.Path("data/regulations.json").read_text(encoding="utf-8"))
        names = [rule["id"] for rule in body["regulations"]] + [group["code"] for group in body["groups"]]
        self.assertEqual([name for name in names if name.split("-")[0] == "recent"], [])

    def test_every_timeline_entry_has_a_full_date(self):
        """연혁의 날짜가 온전해야(YYYY-MM-DD) 변화 기록에 든다."""
        body = json.loads(pathlib.Path("data/regulations.json").read_text(encoding="utf-8"))
        odd = [(rule["id"], event.get("date")) for rule in body["regulations"] for event in rule.get("timeline", []) if len(str(event.get("date", ""))) != 10]
        self.assertEqual(odd, [])

    def test_the_rules_view_offers_the_change_log(self):
        view = pathlib.Path("site/js/views/rules.js").read_text(encoding="utf-8")
        self.assertIn("const days = periodOf(arg);", view)
        self.assertIn("recentBlock(rules)", view)
        side = pathlib.Path("site/js/views/rules/side.js").read_text(encoding="utf-8")
        self.assertIn('link(hrefOf(), picked === RECENT, "clock", "최근 변화", recent, true)', side)

    def test_the_picked_entry_is_brought_into_view_on_narrow_screens(self):
        """좁은 화면에서는 왼쪽의 고르기가 가로로 넘겨 보는 줄이 된다. 줄의 끝에 있는 '최근 변화'를 골랐을 때 그것이 보여야 한다."""
        helper = pathlib.Path("site/js/ui/sidenav.js").read_text(encoding="utf-8")
        self.assertIn('nav.querySelector(\'[aria-current="true"]\')', helper)
        self.assertIn("nav.scrollLeft = ", helper)
        app = pathlib.Path("site/js/app.js").read_text(encoding="utf-8")
        self.assertIn("showPicked(main);", app)
        self.assertLess(app.index("title = await VIEWS[route.name](main, route.arg);"), app.index("showPicked(main);"))   # 화면을 그린 뒤에 부른다


if __name__ == "__main__":
    unittest.main()
