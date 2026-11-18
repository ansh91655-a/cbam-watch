"""규제의 세부 절차(tools.publish.rule_steps): 단계마다의 상태 셈, 자료의 검사, 큰 단계와의 맞춤, 고치는 명령."""
import argparse
import copy
import unittest
from unittest import mock

from tools.common.jsonio import read_json
from tools.publish import regulations, rule_edit, rule_steps

STORED = "collected/archive/pages/eu-primary/tfeu-288.txt"
KIND = {"key": "cod", "steps": [
    {"key": "prepare", "optional": True},
    {"key": "proposal", "reach": 0},
    {"key": "ep-committee", "track": "parliament"},
    {"key": "ep-plenary", "track": "parliament", "reach": 1},
    {"key": "council-position", "track": "council", "reach": 1},
    {"key": "trilogue", "reach": 2},
    {"key": "adoption", "reach": 3},
    {"key": "entry", "reach": 4},
]}
PATH = ["제안", "입장", "협상", "채택", "시행"]


def event(date, step=None, **more):
    made = {"date": date, "text": f"{date}의 일입니다.", "source": "기록", "link": "https://example.eu/a", "basis": "web", "checkedOn": "2026-11-18", **more}
    return {**made, "step": step} if step else made


def rule(at, steps, **more):
    """steps: [(날짜, 단계)] 차례의 연혁."""
    return {"id": "sample", "path": PATH, "at": at, "procedure": "cod", "timeline": [event(date, step) for date, step in steps], **more}


def states(made):
    return {row["key"]: row["state"] for row in rule_steps.progress(made, KIND)["steps"]}


class ProgressTest(unittest.TestCase):
    def test_parallel_tracks_do_not_pass_each_other(self):
        made = rule(0, [("2026-01-01", "proposal")], stepNow=["ep-committee", "council-position"])
        self.assertEqual(states(made), {"prepare": "none", "proposal": "done", "ep-committee": "now", "ep-plenary": "todo", "council-position": "now",
                                        "trilogue": "todo", "adoption": "todo", "entry": "todo"})
        seen = rule_steps.progress(made, KIND)
        self.assertEqual((seen["passed"], seen["total"], seen["now"], seen["next"], seen["finished"]), (1, 7, ["ep-committee", "council-position"], "", False))

    def test_a_later_step_on_the_shared_line_passes_every_track(self):
        made = rule(2, [("2026-01-01", "proposal"), ("2026-03-01", "ep-plenary"), ("2026-05-01", "trilogue")], stepNow=["trilogue"])
        self.assertEqual(states(made), {"prepare": "none", "proposal": "done", "ep-committee": "none", "ep-plenary": "done", "council-position": "none",
                                        "trilogue": "now", "adoption": "todo", "entry": "todo"})
        self.assertEqual(rule_steps.progress(made, KIND)["steps"][5]["events"], [2])              # 진행 중인 단계에도 그 사건이 붙는다

    def test_waiting_marks_the_next_step_and_a_finished_rule_closes_the_rest(self):
        waiting = rule(3, [("2026-01-01", "proposal"), ("2026-06-01", "adoption")])
        self.assertEqual(states(waiting)["entry"], "next")
        self.assertEqual(rule_steps.progress(waiting, KIND)["next"], "entry")
        done = rule(4, [("2026-01-01", "proposal"), ("2026-06-01", "adoption")])
        self.assertEqual((states(done)["entry"], states(done)["trilogue"]), ("done", "none"))
        seen = rule_steps.progress(done, KIND)
        self.assertEqual((seen["passed"], seen["total"], seen["finished"], seen["next"]), (7, 7, True, ""))

    def test_a_fact_without_a_date_counts_as_done_and_the_remark_travels(self):
        made = rule(3, [("2026-06-01", "adoption")], stepNotes={"trilogue": {"text": "협상이 있었습니다.", "evidence": {}}}, procedureNote="두 제안을 함께 다룹니다.")
        seen = rule_steps.progress(made, KIND)
        self.assertEqual((seen["steps"][5]["state"], seen["steps"][5]["note"], seen["note"]), ("done", "협상이 있었습니다.", "두 제안을 함께 다룹니다."))


class ProblemsTest(unittest.TestCase):
    def found(self, made, check=("format", "evidence")):
        return [what for _, what in rule_steps.problems(made, {"cod": KIND}, lambda text: [], regulations.evidence_problem, check)]

    def test_a_sound_rule_passes_and_a_rule_without_a_procedure_carries_no_steps(self):
        self.assertEqual(self.found(rule(0, [("2026-01-01", "proposal")], stepNow=["ep-committee"])), [])
        bare = rule(0, [("2026-01-01", "proposal")])
        del bare["procedure"]
        self.assertIn("절차(procedure)가 없는데 세부 단계(step, stepNow, stepNotes, procedureNote)가 적혀 있음", self.found(bare))
        self.assertEqual(self.found({"id": "plain", "timeline": [event("2026-01-01")]}), [])

    def test_names_must_belong_to_the_procedure(self):
        self.assertIn("없는 절차: nowhere", self.found({**rule(0, [("2026-01-01", "proposal")]), "procedure": "nowhere"}))
        self.assertIn("절차 cod에 없는 단계: signing", self.found(rule(0, [("2026-01-01", "signing")], stepNow=["ep-committee"])))
        self.assertTrue(any("진행 중인 단계(stepNow)" in what for what in self.found(rule(0, [("2026-01-01", "proposal")], stepNow=["signing"]))))
        self.assertIn("세부 단계의 기록이 하나도 없음(연혁의 step이나 stepNow)", self.found(rule(0, [("2026-01-01", None)])))

    def test_a_dateless_fact_needs_text_and_matching_evidence(self):
        good = {"path": STORED, "contains": ["A regulation shall have general application."]}
        self.assertEqual(self.found(rule(2, [("2026-05-01", "trilogue")], stepNow=["trilogue"], stepNotes={"proposal": {"text": "제안했습니다.", "evidence": good}})), [])
        bad = rule(2, [("2026-05-01", "trilogue")], stepNow=["trilogue"], stepNotes={"proposal": {"text": "제안했습니다.", "evidence": {"path": STORED, "contains": ["없는 말"]}}})
        self.assertTrue(self.found(bad)[0].startswith("근거 어긋남"))
        self.assertIn("근거(evidence)가 없음", self.found({**bad, "stepNotes": {"proposal": {"text": "제안했습니다."}}}, check=("format",)))
        self.assertIn("글(text)이 비어 있음", self.found({**bad, "stepNotes": {"proposal": {"text": "", "evidence": good}}}))

    def test_the_big_stage_and_the_steps_must_agree_both_ways(self):
        behind = self.found(rule(1, [("2026-01-01", "proposal"), ("2026-05-01", "trilogue")], stepNow=["trilogue"]))
        self.assertTrue(behind and behind[0].startswith(rule_steps.GAP) and "뒤처져" in behind[0])      # 세부 단계는 협상인데 큰 단계가 입장에 머물러 있다
        ahead = self.found(rule(3, [("2026-01-01", "proposal"), ("2026-05-01", "trilogue")], stepNow=["trilogue"]))
        self.assertTrue(ahead and ahead[0].startswith(rule_steps.GAP) and "따라오지" in ahead[0])       # 큰 단계는 채택인데 세부 단계에 채택의 기록이 없다
        self.assertEqual(self.found(rule(4, [("2026-01-01", "proposal"), ("2026-06-01", "adoption")])), [])   # 절차가 끝난 규제는 뒤의 단계를 따지지 않는다
        self.assertEqual(rule_edit.blocking([("규제 sample", behind[0])], "sample"), [])                 # 고치는 도중의 어긋남은 고치기를 막지 않는다

    def test_published_rules_follow_a_listed_procedure_and_agree_with_their_stage(self):
        data, kinds = read_json(regulations.SOURCE), rule_steps.load_kinds()
        followed = [made for made in data["regulations"] if made.get("procedure")]
        self.assertGreater(len(followed), 20)
        for made in followed:
            self.assertIn(made["procedure"], kinds, made["id"])
            # 근거가 받아 둔 글과 맞는지는 여기에서 보지 않는다(받아 둔 글은 날마다 다시 받는다. 어긋나면 상태 점검이 알린다)
            self.assertEqual(rule_steps.problems(made, kinds, lambda text: [], regulations.evidence_problem, check=("format",)), [], made["id"])
            seen = rule_steps.progress(made, kinds[made["procedure"]])
            self.assertTrue(seen["finished"] or seen["now"] or seen["next"], made["id"])              # 끝나지 않은 규제는 서 있는 곳이 있다
        shown = {row["id"]: row for row in regulations.public(data, [])["regulations"]}
        for made in followed:                                                                         # 진행 중이라고 적은 단계가 그대로 실린다
            self.assertEqual(shown[made["id"]]["progress"]["now"], made.get("stepNow") or [], made["id"])
        self.assertTrue(all(key not in row for row in shown.values() for key in rule_steps.FIELDS))   # 안에서만 쓰는 값은 싣지 않는다
        self.assertNotIn("collected/archive", str([row.get("progress") for row in shown.values()]))


class TableTest(unittest.TestCase):
    def test_the_table_names_every_step_with_its_state_and_dates(self):
        made = rule(1, [("2026-01-01", "proposal"), ("2026-03-01", "ep-plenary")], stepNow=["council-position"], stepNotes={"ep-committee": {"text": "표결했습니다.", "evidence": {}}})
        lines = rule_steps.table(KIND, made)
        self.assertEqual(len(lines), len(KIND["steps"]))
        self.assertIn("마침 | proposal | reach 0 | 2026-01-01", lines[1])
        self.assertIn("(날짜 없는 사실 있음)", lines[2])
        self.assertTrue(lines[4].strip().startswith("진행 중 | council-position"))
        self.assertTrue(lines[0].strip().startswith("기록 없음 | prepare | (없을 수 있는 단계)"))
        self.assertEqual(rule_steps.table(KIND)[1].strip(), "proposal | reach 0")                      # 규제 없이 절차의 단계만

    def test_the_command_prints_a_published_rule_and_refuses_unknown_names(self):
        data = read_json(regulations.SOURCE)
        followed = next(made for made in data["regulations"] if made.get("procedure"))
        with mock.patch("builtins.print") as shown:
            self.assertEqual(rule_steps.main(["--id", followed["id"]]), 0)
            self.assertIn(f"절차 {followed['procedure']}", shown.call_args_list[0].args[0])
            self.assertEqual(rule_steps.main(["--id", "nothing"]), 1)
            self.assertEqual(rule_steps.main(["--kind", "nothing"]), 1)
            self.assertEqual(rule_steps.main(["--kind", "cod"]), 0)


class EditTest(unittest.TestCase):
    def setUp(self):
        self.rule = rule(0, [("2026-01-01", None), ("2026-02-01", None)])
        del self.rule["procedure"]

    def test_set_tag_and_note(self):
        ask = argparse.Namespace
        rule_steps.set_fields(self.rule, ask(procedure="cod", step_now="ep-committee, council-position", procedure_note="두 제안을 함께 다룹니다."))
        self.assertEqual((self.rule["procedure"], self.rule["stepNow"], self.rule["procedureNote"]), ("cod", ["ep-committee", "council-position"], "두 제안을 함께 다룹니다."))
        rule_steps.tag(self.rule, ask(date="2026-01-01", starts="2026-01-01의", step="proposal"))
        self.assertEqual(self.rule["timeline"][0]["step"], "proposal")
        with self.assertRaises(SystemExit):
            rule_steps.tag(self.rule, ask(date="2026-03-01", starts="없는 줄", step="proposal"))
        rule_steps.note(self.rule, ask(step="trilogue", text="협상이 있었습니다.", index="", where=[], path=STORED, contains=["x"]))
        self.assertEqual(self.rule["stepNotes"]["trilogue"]["evidence"], {"path": STORED, "contains": ["x"]})
        rule_steps.note(self.rule, ask(step="adoption", text="채택했습니다.", index="ep-oeil", where=["procedure=2025/0039(COD)", "date=2025-09-29"], path="", contains=[]))
        self.assertEqual(self.rule["stepNotes"]["adoption"]["evidence"], {"index": "ep-oeil", "where": {"procedure": "2025/0039(COD)", "date": "2025-09-29"}})
        rule_steps.note(self.rule, ask(step="trilogue", text="", index="", where=[], path="", contains=[]))
        rule_steps.note(self.rule, ask(step="adoption", text="", index="", where=[], path="", contains=[]))
        self.assertNotIn("stepNotes", self.rule)
        rule_steps.tag(self.rule, ask(date="2026-01-01", starts="2026-01-01의", step=""))
        self.assertNotIn("step", self.rule["timeline"][0])
        rule_steps.set_fields(self.rule, ask(procedure=None, step_now="", procedure_note=""))
        self.assertTrue("stepNow" not in self.rule and "procedureNote" not in self.rule and self.rule["procedure"] == "cod")
        self.rule["timeline"][1]["step"] = "proposal"
        rule_steps.set_fields(self.rule, ask(procedure="", step_now=None, procedure_note=None))    # 절차를 지우면 세부 단계도 모두 지운다
        self.assertTrue("procedure" not in self.rule and all("step" not in row for row in self.rule["timeline"]))

    def test_the_command_line_takes_the_step_options(self):
        # 실린 규제는 날마다 바뀌므로 표본 자료로 명령을 돌려 본다(절차의 단계는 실린 절차 자료의 것이다)
        sample = {"id": "sample-rule", "group": "g", "name": "표본 규정안", "official": "COM(2026) 1", "kind": "규정 제안", "path": PATH, "at": 0, "stage": "제안",
                  "summary": "표본입니다.", "status": "제안 단계입니다.", "links": [{"text": "원문", "url": "https://example.eu/a"}], "related": {"sources": ["src-a"], "words": ["표본"]},
                  "timeline": [event("2026-01-01"), event("2026-02-01")]}
        data = {"asOf": "2026-11-10", "groups": [{"code": "g", "name": "묶음", "about": "묶음입니다."}], "regulations": [sample]}
        written = {}
        with mock.patch.object(rule_edit, "read_json", side_effect=lambda *args: copy.deepcopy(written.get("body", data))), \
                mock.patch.object(rule_edit, "write_json", side_effect=lambda path, value: written.update(body=copy.deepcopy(value))), mock.patch("builtins.print"):
            self.assertEqual(rule_edit.main(["set", "--id", "sample-rule", "--procedure", "cod", "--step-now", "council-position"]), 0)
            self.assertEqual(rule_edit.main(["step", "--id", "sample-rule", "--date", "2026-01-01", "--starts", "2026-01-01의", "--step", "proposal"]), 0)
            self.assertEqual(rule_edit.main(["step", "--id", "sample-rule", "--date", "2026-02-01", "--starts", "2026-02-01의", "--step", "nothing"]), 1)   # 절차에 없는 단계는 막는다
            self.assertEqual(rule_edit.main(["reword", "--id", "sample-rule", "--date", "2026-02-01", "--starts", "2026-02-01의", "--text", "정정본이 나왔습니다."]), 0)
        made = written["body"]["regulations"][0]
        self.assertEqual((made["procedure"], made["stepNow"]), ("cod", ["council-position"]))
        self.assertEqual([row.get("step") for row in made["timeline"]], ["proposal", None])              # 막힌 명령은 아무것도 남기지 않는다
        self.assertEqual(made["timeline"][1]["text"], "정정본이 나왔습니다.")
        self.assertTrue(made["changedOn"])                                                              # 연혁의 글을 고친 것은 규제가 바뀐 것이다
        kept = copy.deepcopy(written["body"])
        with mock.patch.object(rule_edit, "read_json", side_effect=lambda *args: copy.deepcopy(kept)), \
                mock.patch.object(rule_edit, "write_json", side_effect=lambda path, value: written.update(body=copy.deepcopy(value))), mock.patch("builtins.print"):
            kept["regulations"][0].pop("changedOn")
            self.assertEqual(rule_edit.main(["step", "--id", "sample-rule", "--date", "2026-02-01", "--starts", "정정본이", "--step", "proposal"]), 0)
        self.assertNotIn("changedOn", written["body"]["regulations"][0])                                 # 세부 단계를 고친 것은 규제가 바뀐 것이 아니다


if __name__ == "__main__":
    unittest.main()
