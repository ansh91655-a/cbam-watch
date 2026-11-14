"""해설서의 절이 가리키는 규제가 달라졌는지 보기(tools/publish/handbook_rules.py)."""
import copy
import unittest

from tools.common.jsonio import read_json
from tools.publish import handbook, handbook_rules
from tools.run import reference_health

BOOK = {"chapters": [
    {"id": "carbon-price", "sections": [
        {"id": "rules-to-come", "see": [{"href": "#rules-ir-carbon-price", "text": "탄소가격 이행규정(안)"}, {"href": "#calc", "text": "비용 추정"}]},
        {"id": "deduction", "see": [{"href": "#handbook-carbon-price.default-carbon-price", "text": "기본 탄소가격"}]}]},
    {"id": "ahead", "sections": [
        {"id": "to-come", "see": [{"href": "#rules-ir-carbon-price", "text": "탄소가격 이행규정(안)"}, {"href": "#rules-ir-declarations", "text": "신고서 이행규정(계획)"},
                                   {"href": "#rules-eu-upcoming", "text": "준비 중인 규제"}]},
        {"id": "reports"}]},
]}
RULES = [{"id": "ir-carbon-price", "name": "탄소가격 이행규정(안)", "stage": "의견수렴 종료", "timeline": [{}, {}, {}]},
         {"id": "ir-declarations", "name": "신고서 이행규정(계획)", "stage": "준비 단계", "timeline": [{}]},
         {"id": "ets-review", "name": "EU 배출권거래제 개정안", "stage": "제안 심의 중", "timeline": [{}]}]


class ChangedTest(unittest.TestCase):
    def setUp(self):
        self.seen = handbook_rules.accept(BOOK, RULES)

    def test_sections_point_at_rules_through_their_related_screens(self):
        self.assertEqual(handbook_rules.pointed(BOOK), {"ir-carbon-price": ["carbon-price.rules-to-come", "ahead.to-come"], "ir-declarations": ["ahead.to-come"],
                                                         "eu-upcoming": ["ahead.to-come"]})
        # 규제의 id를 주면 규제 묶음의 주소(#rules-eu-upcoming)는 규제로 보지 않는다
        self.assertEqual(sorted(handbook_rules.pointed(BOOK, {rule["id"] for rule in RULES})), ["ir-carbon-price", "ir-declarations"])

    def test_the_record_keeps_only_the_rules_that_are_pointed_at(self):
        self.assertEqual(self.seen["rulesSeen"], {"ir-carbon-price": {"stage": "의견수렴 종료", "events": 3}, "ir-declarations": {"stage": "준비 단계", "events": 1}})
        self.assertEqual(self.seen["chapters"], BOOK["chapters"])   # 글은 그대로다
        self.assertEqual(handbook_rules.changed(self.seen, RULES), [])

    def test_a_new_stage_or_a_new_event_is_told_with_the_sections_to_read_again(self):
        moved = copy.deepcopy(RULES)
        moved[0]["stage"] = "채택"
        moved[1]["timeline"].append({})
        self.assertEqual(handbook_rules.changed(self.seen, moved), [
            ("ir-carbon-price", "탄소가격 이행규정(안)", ["carbon-price.rules-to-come", "ahead.to-come"], "단계가 '의견수렴 종료'에서 '채택'(으)로 바뀜"),
            ("ir-declarations", "신고서 이행규정(계획)", ["ahead.to-come"], "연혁이 1줄에서 2줄로 달라짐")])
        self.assertEqual(handbook_rules.lines(self.seen, moved)[0],
                         "규제 '탄소가격 이행규정(안)'이(가) 해설서를 맞춰 본 뒤에 달라짐(단계가 '의견수렴 종료'에서 '채택'(으)로 바뀜). 이 규제를 가리키는 절을 다시 볼 것: carbon-price.rules-to-come, ahead.to-come")
        self.assertEqual(handbook_rules.changed(handbook_rules.accept(self.seen, moved), moved), [])   # 다시 맞춰 보고 적으면 사라진다

    def test_only_the_named_rules_are_accepted_when_some_still_need_a_change(self):
        """다시 보니 고칠 것이 없는 규제만 넘기고, 글을 고쳐야 하는 규제는 '달라진 것'으로 남긴다."""
        moved = copy.deepcopy(RULES)
        moved[0]["stage"] = "채택"
        moved[1]["timeline"].append({})
        partly = handbook_rules.accept(self.seen, moved, {"ir-declarations"})
        self.assertEqual(partly["rulesSeen"], {"ir-carbon-price": {"stage": "의견수렴 종료", "events": 3}, "ir-declarations": {"stage": "준비 단계", "events": 2}})
        self.assertEqual([rule for rule, *_ in handbook_rules.changed(partly, moved)], ["ir-carbon-price"])
        # 적힌 것이 없던 규제는 이름을 적어 주지 않으면 적지 않는다(여전히 달라진 것으로 남는다)
        fresh = handbook_rules.accept(BOOK, RULES, {"ir-declarations"})
        self.assertEqual(sorted(fresh["rulesSeen"]), ["ir-declarations"])
        self.assertEqual([rule for rule, *_ in handbook_rules.changed(fresh, RULES)], ["ir-carbon-price"])

    def test_a_rule_without_a_record_is_told_too(self):
        self.assertEqual([(rule, why) for rule, _, _, why in handbook_rules.changed(BOOK, RULES)],
                         [("ir-carbon-price", "맞춰 본 기록이 없음"), ("ir-declarations", "맞춰 본 기록이 없음")])
        self.assertEqual(handbook_rules.changed(None, RULES), [])
        self.assertEqual(handbook_rules.changed(self.seen, []), [])   # 규제 자료를 읽지 못한 날은 알리지 않는다(주소가 없는 것은 해설서의 꼴 검사가 잡는다)


class StoredBookTest(unittest.TestCase):
    def test_the_record_names_only_rules_the_book_points_at(self):
        body = read_json(handbook.SOURCE, {})
        rules = read_json(handbook_rules.RULES, {})["regulations"]
        pointed = handbook_rules.pointed(body, {rule["id"] for rule in rules})
        self.assertGreaterEqual(len(pointed), 5)
        self.assertEqual(set(body["rulesSeen"]), set(pointed))   # 규제가 날마다 달라질 수 있으므로 값이 같은지는 보지 않는다(상태 점검이 알린다)
        for record in body["rulesSeen"].values():
            self.assertEqual(sorted(record), ["events", "stage"])

    def test_a_changed_rule_reaches_the_daily_report_as_a_section_to_read_again(self):
        body = read_json(handbook.SOURCE, {})
        rules = copy.deepcopy(read_json(handbook_rules.RULES, {})["regulations"])
        steady = handbook_rules.accept(body, rules)
        self.assertEqual(reference_health.handbook_rule_lines(steady, rules), [])
        target = next(rule for rule in rules if rule["id"] in steady["rulesSeen"])
        target["timeline"] = target["timeline"] + [{"date": "2027-01-01", "text": "새 일"}]
        self.assertEqual(reference_health.handbook_lines(steady), [])   # 문제로는 세지 않는다
        lines = reference_health.handbook_rule_lines(steady, rules)
        self.assertEqual(len(lines), 1)
        self.assertTrue(lines[0].startswith(f"해설서: 규제 '{target['name']}'이(가) 해설서를 맞춰 본 뒤에 달라짐(연혁이 "), lines[0])


if __name__ == "__main__":
    unittest.main()
