"""규제별 진행 상황 자료의 검사와 사이트용 변환을 확인한다."""
import unittest

from tools.publish import regulations
from tools.common.jsonio import read_json


def body(**changes):
    rule = {"id": "sample-rule", "group": "g", "name": "표본 규정", "official": "COM(2025) 1", "kind": "규정 제안", "path": ["제안", "채택"], "at": 0,
            "stage": "제안", "summary": "표본입니다.", "status": "제안 단계입니다.",
            "timeline": [{"date": "2025-12-17", "text": "제안이 나왔습니다.", "source": "EUR-Lex", "link": "https://example.eu/a", "basis": "web", "checkedOn": "2026-11-10"}],
            "links": [{"text": "원문", "url": "https://example.eu/a"}], "related": {"sources": ["src-a"], "words": ["표본"]}}
    rule.update(changes)
    return {"asOf": "2026-11-10", "groups": [{"code": "g", "name": "묶음", "about": "묶음입니다."}], "regulations": [rule]}


class RegulationsTest(unittest.TestCase):
    def setUp(self):
        self.terms = regulations.term_check.load()

    def whats(self, data):
        return [what for _, what in regulations.problems(data, self.terms)]

    def test_good_body_passes(self):
        self.assertEqual(self.whats(body()), [])

    def test_plain_ending_and_avoided_term_are_caught(self):
        found = self.whats(body(status="제안 단계이다.", summary="수입업체가 대상입니다."))
        self.assertTrue(any("plain-ending" in what for what in found))
        self.assertTrue(any("수입업체" in what for what in found))

    def test_step_position_and_order(self):
        self.assertIn("단계 위치(at)가 단계 목록(path) 밖임", self.whats(body(at=5)))
        late_first = [{"date": "2026-01-01", "text": "뒤입니다.", "source": "S", "link": "https://example.eu/b", "basis": "web", "checkedOn": "2026-11-10"},
                      {"date": "2025-01-01", "text": "앞입니다.", "source": "S", "link": "https://example.eu/b", "basis": "web", "checkedOn": "2026-11-10"}]
        self.assertIn("연혁이 날짜순이 아님", self.whats(body(timeline=late_first)))

    def test_press_events_must_say_so(self):
        event = {"date": "2026-10-20", "text": "협상이 열렸습니다.", "source": "신문", "link": "https://example.com/n", "basis": "press", "checkedOn": "2026-11-10"}
        self.assertTrue(any("보도" in what for what in self.whats(body(timeline=[event]))))
        event["text"] = "협상이 열렸다는 보도가 있었습니다."
        self.assertEqual(self.whats(body(timeline=[event])), [])

    def test_stored_event_needs_matching_evidence(self):
        event = {"date": "2025-10-17", "text": "관보에 실렸습니다.", "source": "EUR-Lex", "link": "https://example.eu/c", "basis": "stored",
                 "evidence": {"index": "eur-lex", "where": {"celex": "32025R2083", "date": "2025-10-17"}}}
        self.assertEqual(self.whats(body(timeline=[event])), [])
        event["evidence"]["where"]["date"] = "2025-10-18"
        found = regulations.problems(body(timeline=[event]), self.terms)
        self.assertTrue(found and found[0][1].startswith("근거 어긋남"))
        # 꼴만 볼 때는 근거가 어긋난 것을 문제로 치지 않는다(사이트 만들기를 멈추지 않는다)
        self.assertEqual(regulations.problems(body(timeline=[event]), self.terms, kinds=("format",)), [])
        self.assertEqual(len(regulations.problems(body(timeline=[event]), self.terms, kinds=("evidence",))), 1)

    def test_evidence_file_must_be_collected_material(self):
        self.assertIn("모아 둔 자료가 아님", regulations.evidence_problem({"path": "README.md", "contains": ["CBAM"]}, ""))

    def test_public_shape_hides_internal_fields_and_adds_related_items(self):
        items = [{"id": "a", "sourceCode": "src-a", "title": "무관", "summary": "", "published": "2026-01-02"},
                 {"id": "b", "sourceCode": "x", "title": "표본 소식", "summary": "", "published": "2026-03-01"},
                 {"id": "c", "sourceCode": "x", "title": "다른 소식", "summary": "", "published": "2026-04-01"}]
        press = {"date": "2026-10-20", "text": "협상이 열렸다는 보도가 있었습니다.", "source": "신문", "link": "https://example.com/n", "basis": "press", "checkedOn": "2026-11-10"}
        out = regulations.public(body(timeline=[press]), items)["regulations"][0]
        self.assertEqual(out["relatedItems"], ["b", "a"])
        self.assertNotIn("related", out)
        self.assertEqual(out["timeline"], [{"date": "2026-10-20", "text": press["text"], "source": "신문", "link": press["link"], "press": True}])

    def test_published_data_is_clean(self):
        data = read_json(regulations.SOURCE)
        self.assertEqual(regulations.problems(data, self.terms, kinds=("format",)), [])
        self.assertGreaterEqual(len(data["regulations"]), 20)


class RuleEventsTest(unittest.TestCase):
    def test_next_dates_become_calendar_events_unless_switched_off(self):
        from tools.publish import derive
        data = body(next="표결이 잡혀 있습니다.", nextDate="2026-12-14")
        rows = derive.rule_events(data)
        self.assertEqual([(row["date"], row["title"], row["kind"], row["note"], row["link"]) for row in rows],
                         [("2026-12-14", "표본 규정", "입법", "표결이 잡혀 있습니다.", "https://example.eu/a")])
        self.assertEqual(derive.rule_events(body(next="표결이 잡혀 있습니다.", nextDate="2026-12-14", calendar=False)), [])
        self.assertEqual(derive.rule_events(body(next="표결이 잡혀 있습니다.")), [])
        merged = derive.events([{"date": "2026-12-01", "title": "기존 일정"}], {}, data)
        self.assertEqual([row["date"] for row in merged], ["2026-12-01", "2026-12-14"])


class RuleEditTest(unittest.TestCase):
    def setUp(self):
        import argparse
        from tools.publish import rule_edit
        self.edit, self.args = rule_edit, argparse.Namespace
        self.body = body()

    def test_add_event_keeps_the_timeline_in_date_order(self):
        self.edit.add_event(self.body, self.args(id="sample-rule", date="2025-01-10", text="먼저 있었던 일입니다.", source="S", link="https://example.eu/x",
                                                   basis="stored", index="eur-lex", where=["celex=32025R2083", "date=2025-10-17"], path="", contains=[]))
        rule = self.body["regulations"][0]
        self.assertEqual([event["date"] for event in rule["timeline"]], ["2025-01-10", "2025-12-17"])
        self.assertEqual(rule["timeline"][0]["evidence"], {"index": "eur-lex", "where": {"celex": "32025R2083", "date": "2025-10-17"}})
        with self.assertRaises(SystemExit):  # 같은 줄을 두 번 넣지 못한다
            self.edit.add_event(self.body, self.args(id="sample-rule", date="2025-01-10", text="먼저 있었던 일입니다.", source="S", link="https://example.eu/x",
                                                       basis="web", index="", where=[], path="", contains=[]))

    def test_set_changes_and_clears_fields(self):
        self.body["regulations"][0].update({"next": "다음입니다.", "nextDate": "2026-12-01"})
        self.edit.set_fields(self.body, self.args(id="sample-rule", stage="채택", tone="adopted", status=None, at=1, next="", next_date="", next_title=None))
        rule = self.body["regulations"][0]
        self.assertEqual((rule["stage"], rule["tone"], rule["at"], rule["status"]), ("채택", "adopted", 1, "제안 단계입니다."))
        self.assertNotIn("next", rule)
        self.assertNotIn("nextDate", rule)
        # 날짜만 바꾸면 옛 일정 이름은 지워지고, 새 이름을 주면 그 이름이 남는다
        rule.update({"next": "표결입니다.", "nextDate": "2026-12-01", "nextTitle": "옛 이름"})
        self.edit.set_fields(self.body, self.args(id="sample-rule", stage=None, tone=None, status=None, at=None, next=None, next_date="2026-12-08", next_title=None))
        self.assertEqual((rule["nextDate"], rule.get("nextTitle")), ("2026-12-08", None))
        self.edit.set_fields(self.body, self.args(id="sample-rule", stage=None, tone=None, status=None, at=None, next=None, next_date="2026-12-09", next_title="본회의 표결"))
        self.assertEqual(rule["nextTitle"], "본회의 표결")

    def test_drop_event_needs_exactly_one_match(self):
        with self.assertRaises(SystemExit):
            self.edit.drop_event(self.body, self.args(id="sample-rule", date="2025-12-17", starts="없는 글"))
        self.edit.drop_event(self.body, self.args(id="sample-rule", date="2025-12-17", starts="제안이"))
        self.assertEqual(self.body["regulations"][0]["timeline"], [])


class RulesWatchTest(unittest.TestCase):
    def test_new_changed_and_gone_entries(self):
        from tools.run import rules_watch
        before = {"의회 절차의 단계": {"2025/0419(COD)": "Awaiting Parliament's position in 1st reading", "2025/0001(COD)": "x"}, "영국 법령": {"2026 No. 802": "A"}}
        now = {"의회 절차의 단계": {"2025/0419(COD)": "Awaiting Council's 1st reading position", "2025/0418(COD)": "y"}, "영국 법령": {}}
        found = rules_watch.changes(before, now)
        self.assertIn({"group": "의회 절차의 단계", "key": "2025/0419(COD)", "before": "Awaiting Parliament's position in 1st reading", "now": "Awaiting Council's 1st reading position"}, found)
        self.assertIn({"group": "의회 절차의 단계", "key": "2025/0418(COD)", "before": None, "now": "y"}, found)
        self.assertIn({"group": "의회 절차의 단계", "key": "2025/0001(COD)", "before": "x", "now": None}, found)
        # 기록을 통째로 읽지 못한 날은 항목마다 '사라짐'으로 적지 않고 한 줄로 알린다
        self.assertIn({"group": "영국 법령", "key": "(기록 전체)", "before": "1건", "now": None}, found)

    def test_snapshot_covers_the_tracked_records(self):
        from tools.run import rules_watch
        now = rules_watch.snapshot()
        self.assertIn("2025/0419(COD)", now["의회 절차의 단계"])
        self.assertIn("62023CJ0512", now["법원 사건 문서"])
        self.assertEqual(rules_watch.changes(now, now), [])


class RulesHealthTest(unittest.TestCase):
    def test_reports_nothing_on_a_clean_day_and_flags_a_passed_date(self):
        import json
        import pathlib
        from tools.run import rules_health
        found, counts = rules_health.problems("2026-11-10", False)
        self.assertEqual([what for what in found if "다음 일정" in what or "꼴" in what], [])
        self.assertGreaterEqual(counts["regulations"], 20)
        # 다음 일정이 사흘 넘게 지난 날에는 알린다
        late, _ = rules_health.problems("2026-12-05", False)
        self.assertTrue(any("다음 일정(2026-11-30)이 지났는데 그대로임" in what for what in late))
        self.assertTrue(json.loads(pathlib.Path("data/rules-seen.json").read_text(encoding="utf-8"))["seen"])


if __name__ == "__main__":
    unittest.main()
