"""입법 절차 화면의 셈(site/js/procedure/model.js)과 그 화면이 메뉴와 주소에 제대로 걸려 있는지.

절차의 단계는 실린 자료(data/procedures.json)의 것을 쓰고, 규제는 여기에서 만든 표본을 쓴다.
실린 규제는 날마다 단계가 바뀌므로, 그 값에 기대는 시험은 두지 않는다(실린 규제로는 셈이 어디에서도 넘어지지 않는지만 본다).
"""
import json
import pathlib
import shutil
import subprocess
import tempfile
import unittest

from tools.common.jsonio import read_json
from tools.publish import procedures, regulations, rule_steps

SCRIPT = r"""
import { readFileSync } from 'node:fs';
import { activity, alsoCalled, current, dots, kindOf, lanes, ongoing, shortName, stepsOf, summary } from './site/js/procedure/model.js';
import { groupOf, SCREENS } from './site/js/nav/map.js';
const { book, rules, live } = JSON.parse(readFileSync(process.argv.at(-1), 'utf8'));
const rule = (id) => rules.find((one) => one.id === id);
const cod = kindOf(book, 'cod');
const plan = lanes(cod);
const cell = (key) => plan.cells.filter((one) => one.step.key === key).map((one) => [one.from, one.to, one.row, one.span, Boolean(one.wide)]);
console.log(JSON.stringify({
  missing: kindOf(book, 'nothing'),
  summaries: Object.fromEntries(rules.filter((one) => one.progress).map((one) => [one.id, summary(kindOf(book, one.progress.kind), one)])),
  current: Object.fromEntries(rules.filter((one) => one.progress).map((one) => [one.id, current(kindOf(book, one.progress.kind), one)])),
  dots: dots(cod, rule('talks')).map((one) => one.state),
  steps: stepsOf(cod, rule('early')).map((one) => [one.key, one.state, one.events.length]),
  trilogue: stepsOf(cod, rule('talks')).find((one) => one.key === 'trilogue').events.map((one) => [one.date, Boolean(one.press)]),
  note: stepsOf(kindOf(book, 'implementing'), rule('waiting')).find((one) => one.key === 'committee').note,
  ongoing: ongoing(rules).map((one) => one.id),
  council: activity(book, rules, 'council', 5).map((one) => [one.rule.id, one.step.key]),
  parliament: activity(book, rules, 'parliament', 2).map((one) => one.event.date),
  press: activity(book, rules, 'parliament', 50).some((one) => one.event.press) || activity(book, rules, 'commission', 50).some((one) => one.event.press),
  lanes: plan.lanes, rows: plan.rows, count: cod.steps.length,
  cells: Object.fromEntries(['proposal', 'advisory', 'ep-referral', 'ep-mandate', 'council-position', 'trilogue', 'provisional', 'publication'].map((key) => [key, cell(key)])),
  noLanes: lanes(kindOf(book, 'uk-law')).cells.length,
  names: [alsoCalled('각료이사회'), alsoCalled('유럽감사원'), alsoCalled(''), shortName({ name: '의회: 협상 입장' }), shortName({ name: '3자 협상' })],
  nav: [groupOf('procedure').key, groupOf('procedure').views, SCREENS.procedure.name],
  live: live.filter((one) => one.progress).map((one) => {
    const kind = kindOf(book, one.progress.kind);
    return [one.id, summary(kind, one).length > 0, dots(kind, one).length === one.progress.total, stepsOf(kind, one).every((step) => step.events.every(Boolean))];
  }),
  liveBoard: ongoing(live).length + live.filter((one) => one.progress && one.progress.finished).length === live.filter((one) => one.progress).length,
}));
"""

PATH = {"cod": ["집행위 제안", "의회·이사회 입장", "3자 협상", "채택·공포", "시행"], "implementing": ["준비", "초안 의견수렴", "채택·공포", "시행"]}


def sample(rule_id, kind, at, events, kinds, **fields):
    """표본 규제를 사이트에 싣는 모양으로. events는 (날짜, 단계[, 언론 보도인가])의 목록이다."""
    rule = {"id": rule_id, "name": rule_id, "procedure": kind, "path": PATH[kind], "at": at,
            "timeline": [{"date": row[0], "text": f"{row[0]}의 일입니다.", "step": row[1], "basis": "press" if len(row) > 2 and row[2] else "stored"} for row in events], **fields}
    public = {"id": rule_id, "name": rule_id, "timeline": [{"date": event["date"], "text": event["text"], **({"press": True} if event["basis"] == "press" else {})} for event in rule["timeline"]]}
    return {**public, "progress": rule_steps.progress(rule, kinds[kind])}


@unittest.skipUnless(shutil.which("node"), "node가 없으면 화면의 셈은 시험하지 않는다")
class ProcedureViewTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = read_json(procedures.SOURCE)
        kinds = procedures.kinds_by_key(source)
        rules = [
            # 3자 협상 중: 협상의 기록은 언론 보도뿐이다
            sample("talks", "cod", 2, [("2026-01-10", "proposal"), ("2026-02-10", "ep-referral"), ("2026-03-10", "council-position"), ("2026-04-10", "ep-committee"),
                                       ("2026-05-10", "ep-mandate"), ("2026-06-10", "trilogue", True)], kinds, stepNow=["trilogue"]),
            # 제안 뒤: 의회 위원회와 이사회가 같은 때에 다루고 있다
            sample("early", "cod", 0, [("2026-07-01", "proposal"), ("2026-08-01", "ep-referral")], kinds, stepNow=["ep-committee", "council-position"]),
            # 끝난 절차
            sample("done", "cod", 4, [("2025-01-10", "proposal"), ("2025-06-10", "ep-adoption"), ("2025-07-10", "council-adoption"), ("2025-08-10", "publication")], kinds),
            # 채택되어 발효를 기다리는 이행규정: 위원회의 의견은 날짜 없이 확인된 사실이다
            sample("waiting", "implementing", 2, [("2026-05-01", "feedback"), ("2026-11-05", "adoption"), ("2026-11-16", "publication")], kinds,
                   stepNotes={"committee": {"text": "위원회는 의견을 내지 않았습니다.", "evidence": {}}}),
            {"id": "plain", "name": "plain", "timeline": []},   # 절차가 적히지 않은 규제
        ]
        live = regulations.public(read_json(regulations.SOURCE), [])["regulations"]
        with tempfile.NamedTemporaryFile("w", suffix=".json", encoding="utf-8", delete=False) as handle:
            json.dump({"book": procedures.public(source), "rules": rules, "live": live}, handle, ensure_ascii=False)
        done = subprocess.run(["node", "--input-type=module", "-e", SCRIPT, handle.name], capture_output=True, text=True)
        pathlib.Path(handle.name).unlink()
        if done.returncode:
            raise AssertionError(done.stderr[-1500:])
        cls.seen = json.loads(done.stdout)
        cls.rules = {rule["id"]: rule for rule in rules}

    def test_the_summary_says_where_a_rule_stands(self):
        seen, rules = self.seen, self.rules
        talks = rules["talks"]["progress"]
        self.assertEqual(seen["summaries"]["talks"], f"주요 단계 {talks['total']}개 가운데 {talks['passed']}개를 지났습니다. 지금은 ‘3자 협상’ 단계입니다.")
        self.assertEqual(seen["summaries"]["done"], f"이 절차의 주요 단계 {rules['done']['progress']['total']}개를 모두 지났습니다.")
        self.assertEqual(seen["current"]["early"], {"label": "지금", "names": ["의회: 위원회 심의와 표결", "이사회: 협상 입장"]})   # 같은 때에 나아가는 두 갈래
        self.assertIn("다음 단계는 ‘발효와 적용’입니다.", seen["summaries"]["waiting"])                    # 진행 중인 일이 없으면 기다리는 단계를 말한다
        self.assertEqual(seen["current"]["done"], {"label": "", "names": []})
        self.assertIsNone(seen["missing"])

    def test_steps_carry_their_state_events_and_dateless_facts(self):
        seen = self.seen
        self.assertEqual(len(seen["dots"]), self.rules["talks"]["progress"]["total"])                     # 꼭 있는 단계마다 점 하나
        self.assertEqual(seen["dots"].count("now"), 1)
        states = {row[0]: row[1] for row in seen["steps"]}
        self.assertNotIn("advisory", states)                                                             # 기록이 없는 선택 단계는 싣지 않는다
        self.assertEqual((states["ep-committee"], states["ep-mandate"], states["council-position"]), ("now", "todo", "now"))   # 이사회의 갈래가 나아가도 의회의 갈래는 남아 있다
        self.assertEqual(seen["trilogue"], [["2026-06-10", True]])
        self.assertIn("의견을 내지 않았습니다", seen["note"])

    def test_the_board_lists_unfinished_rules_and_institutions_show_what_they_did(self):
        seen = self.seen
        self.assertEqual(seen["ongoing"], ["talks", "early", "waiting"])                                 # 끝난 규제와 절차가 적히지 않은 규제는 싣지 않는다
        self.assertEqual(seen["council"], [["talks", "council-position"], ["done", "council-adoption"]])   # 새 것부터
        self.assertEqual(seen["parliament"], ["2026-08-01", "2026-05-10"])
        self.assertFalse(seen["press"])                                                                  # 기관이 한 일에는 언론 보도로만 아는 일을 싣지 않는다

    def test_the_lane_figure_puts_parallel_tracks_side_by_side(self):
        seen = self.seen
        self.assertEqual(seen["lanes"], ["commission", "parliament", "council"])
        cells = seen["cells"]
        self.assertEqual(cells["proposal"][0][:2], [1, 2])                                               # 집행위원회의 줄
        self.assertTrue(cells["advisory"][0][4])                                                         # 줄에 없는 기관이 하는 일은 모든 줄을 가로지른다
        referral, mandate, council = cells["ep-referral"][0], cells["ep-mandate"][0], cells["council-position"][0]
        self.assertEqual(referral[2], council[2])                                                        # 의회의 첫 단계와 이사회의 단계가 같은 높이에서 시작한다
        self.assertEqual(council[3], mandate[2] - referral[2] + 1)                                       # 이사회의 칸이 의회의 세 단계만큼 내려온다
        self.assertEqual(cells["trilogue"][0][:2], [1, 4])                                               # 세 기관이 함께하는 단계
        self.assertEqual(cells["provisional"][0][:2], [2, 4])
        self.assertEqual(seen["rows"], seen["count"] - 1)                                               # 이사회의 단계가 의회의 단계 옆에 놓여 줄 하나가 준다
        self.assertEqual(seen["noLanes"], 5)                                                             # 줄이 없는 절차는 단계마다 한 줄씩(그림은 그리지 않는다)

    def test_names_and_the_place_in_the_menu(self):
        self.assertEqual(self.seen["names"], ["각료이사회라고도 부릅니다", "유럽감사원이라고도 부릅니다", "", "협상 입장", "3자 협상"])
        self.assertEqual(self.seen["nav"], ["rules", ["rules", "procedure"], "입법 절차"])
        page = pathlib.Path("site/index.html").read_text(encoding="utf-8")
        self.assertIn('<link rel="stylesheet" href="css/procedure.css">', page)
        steps = pathlib.Path("site/js/views/rules/steps.js").read_text(encoding="utf-8")
        self.assertIn("#procedure-${kind.key}.${step.key}", steps)                                       # 세부 절차의 단계가 절차 안내의 그 단계로 이어진다

    def test_the_published_rules_go_through_the_same_sums(self):
        self.assertTrue(self.seen["live"])                                                               # 실린 규제 가운데 세부 절차를 가진 것이 있다
        for rule_id, has_summary, dots_match, events_found in self.seen["live"]:
            self.assertTrue(has_summary and dots_match and events_found, rule_id)
        self.assertTrue(self.seen["liveBoard"])                                                          # 한눈에 보기는 끝나지 않은 규제를 빠짐없이 싣는다


if __name__ == "__main__":
    unittest.main()
