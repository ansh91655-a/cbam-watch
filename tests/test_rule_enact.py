"""준비 중이던 하위 법령이 관보에 실렸을 때 규제 자료를 '나온 법령'의 모습으로 바꾸는 일을 확인한다."""
import argparse
import contextlib
import io
import unittest

from tools.laws import catalog
from tools.publish import regulations, rule_edit, rule_enact


def rule(rule_id, group, **changes):
    made = {"id": rule_id, "group": group, "name": f"{rule_id} 규정", "official": "COM(2025) 1", "kind": "이행규정", "path": ["준비", "채택", "발효", "시행"], "at": 3,
            "stage": "시행 중", "tone": "live", "summary": "표본입니다.", "status": "시행 중입니다.",
            "timeline": [{"date": "2025-12-17", "text": "관보에 실렸습니다.", "source": "EUR-Lex", "link": "https://example.eu/a", "basis": "web", "checkedOn": "2026-11-10"}],
            "links": [{"text": "원문", "url": "https://example.eu/a"}], "related": {"sources": ["src-a"], "words": ["표본"]}}
    made.update(changes)
    return made


def body():
    draft = rule("draft", "eu-upcoming", name="표본 차감 이행규정(안)", kind="이행규정(안)", official="의견수렴 14830 · Ares(2024)1", at=1, stage="채택 대기", tone="progress",
                 status="채택을 기다리고 있습니다.", links=[{"text": "EU 집행위원회 의견수렴 14830", "url": "https://example.eu/consult"}])
    return {"asOf": "2026-11-10",
            "groups": [{"code": "eu-upcoming", "name": "준비 중인 하위 법령", "about": "준비 중입니다."}, {"code": "eu-acts", "name": "시행 중인 하위 법령", "about": "시행 중입니다."},
                       {"code": "trade", "name": "분쟁", "about": "분쟁입니다."}],
            "regulations": [draft, rule("live-a", "eu-acts"), rule("live-b", "eu-acts"), rule("old", "eu-acts", tone="ended", stage="종료"), rule("case", "trade")]}


def ask(**given):
    return argparse.Namespace(**{"id": "draft", "celex": "32026R2498", "name": None, "kind": None, "after": None, **given})


class RuleEnactTest(unittest.TestCase):
    def setUp(self):
        self.body = body()
        self.rule = self.body["regulations"][0]

    def order(self):
        return [old["id"] for old in self.body["regulations"]]

    def test_a_draft_becomes_an_act_with_its_number_link_and_word(self):
        rule_enact.enact(self.body, ask())
        made = self.rule
        self.assertEqual((made["group"], made["name"], made["kind"]), ("eu-acts", "표본 차감 이행규정", "이행규정"))
        self.assertEqual(made["official"], "Implementing Regulation (EU) 2026/2498")
        self.assertEqual(made["links"][0], {"text": "이행규정 원문(EUR-Lex)", "url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32026R2498"})
        self.assertEqual(made["links"][1]["text"], "EU 집행위원회 의견수렴 14830")   # 옛 링크는 뒤에 남는다
        self.assertEqual(made["related"]["words"], ["표본", "2026/2498"])
        self.assertTrue(made["changedOn"])
        # 단계, 설명, 연혁은 그대로다
        self.assertEqual((made["stage"], made["at"], made["status"], len(made["timeline"])), ("채택 대기", 1, "채택을 기다리고 있습니다.", 1))
        # 법령 전문 화면이 이 번호로 규제를 찾는다
        self.assertEqual(catalog.rule_ids(self.body)["32026R2498"], "draft")
        self.assertEqual([what for _, what in regulations.problems(self.body, kinds=("format",))], [])

    def test_it_is_put_before_the_acts_that_ended_or_after_the_one_named(self):
        rule_enact.enact(self.body, ask())
        self.assertEqual(self.order(), ["live-a", "live-b", "draft", "old", "case"])
        again = body()
        rule_enact.enact(again, ask(after="live-a"))
        self.assertEqual([old["id"] for old in again["regulations"]], ["live-a", "draft", "live-b", "old", "case"])
        with self.assertRaises(SystemExit):
            rule_enact.enact(body(), ask(after="nowhere"))

    def test_a_group_with_only_ended_acts_or_no_acts_still_takes_it(self):
        only_ended = body()
        only_ended["regulations"] = [old for old in only_ended["regulations"] if old["id"] not in ("live-a", "live-b")]
        rule_enact.enact(only_ended, ask())
        self.assertEqual([old["id"] for old in only_ended["regulations"]], ["draft", "old", "case"])
        empty = body()
        empty["regulations"] = [old for old in empty["regulations"] if old["group"] != "eu-acts"]
        rule_enact.enact(empty, ask())
        self.assertEqual([old["id"] for old in empty["regulations"]], ["case", "draft"])

    def test_a_delegated_act_and_a_planned_one_and_a_short_number(self):
        self.rule.update({"name": "인증서 판매·환매 위임규정(계획)", "kind": "위임규정(계획)"})
        rule_enact.enact(self.body, ask(celex="32027R0045"))
        self.assertEqual((self.rule["name"], self.rule["kind"], self.rule["official"]), ("인증서 판매·환매 위임규정", "위임규정", "Delegated Regulation (EU) 2027/45"))
        self.assertEqual(self.rule["links"][0]["text"], "위임규정 원문(EUR-Lex)")
        self.assertEqual(self.rule["related"]["words"][-1], "2027/45")
        self.assertEqual(catalog.rule_ids(self.body)["32027R0045"], "draft")

    def test_the_name_and_the_kind_can_be_given(self):
        self.rule.update({"kind": "하위 법령(안)"})
        with self.assertRaises(SystemExit):   # 종류를 알 수 없으면 묻는다
            rule_enact.enact(self.body, ask())
        rule_enact.enact(self.body, ask(kind="이행규정", name="제3국 탄소가격 차감 이행규정"))
        self.assertEqual((self.rule["name"], self.rule["kind"]), ("제3국 탄소가격 차감 이행규정", "이행규정"))

    def test_wrong_numbers_and_a_second_run_are_refused(self):
        for wrong in ("2026/2498", "52025PC0989", "32026L0001", "32026R249", ""):
            with self.assertRaises(SystemExit):
                rule_enact.enact(body(), ask(celex=wrong))
        with self.assertRaises(SystemExit):
            rule_enact.enact(self.body, ask(id="nobody"))
        rule_enact.enact(self.body, ask())
        before = self.order()
        with self.assertRaises(SystemExit):   # 같은 법령으로 두 번 바꾸지 않는다
            rule_enact.enact(self.body, ask())
        self.assertEqual(self.order(), before)
        self.assertEqual(len(self.rule["links"]), 2)

    def test_the_command_line_knows_it(self):
        with contextlib.redirect_stderr(io.StringIO()) as said, self.assertRaises(SystemExit):   # --celex가 없으면 argparse가 멈춘다
            rule_edit.main(["enact", "--id", "draft"])
        self.assertIn("--celex", said.getvalue())


if __name__ == "__main__":
    unittest.main()
