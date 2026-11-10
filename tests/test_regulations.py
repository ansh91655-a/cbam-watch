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


class ThumbsTest(unittest.TestCase):
    def test_only_reusable_official_sources_are_planned_once_each(self):
        from tools.publish import thumbs
        from tools.thumbs import plan
        items = [{"link": "https://taxation-customs.ec.europa.eu/news/a_en"}, {"link": "https://taxation-customs.ec.europa.eu/news/a_en"},
                 {"link": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32025R2083"}, {"link": "https://www.gov.uk/guidance/x"},
                 {"link": "https://www.keco.or.kr/web/x"}, {"link": "https://www.consilium.europa.eu/en/press/x"}, {"link": "http://www.gov.uk/y"},
                 {"link": "https://www.federalregister.gov/d/1", "withdrawn": True}, {"link": "https://oeil.europarl.europa.eu/oeil/en/procedure-file?reference=2025/0419(COD)"}]
        jobs = plan.todo(items, {}, lambda name: False, 10)
        self.assertEqual([job["kind"] for job in jobs], ["page", "pdf", "page", "page"])
        self.assertEqual(jobs[1]["celex"], "32025R2083")
        tried = {thumbs.name_of("https://www.gov.uk/guidance/x"): {"tries": 3}}
        self.assertEqual(len(plan.todo(items, tried, lambda name: name == jobs[0]["name"], 10)), 2)

    def test_items_get_a_thumb_only_when_the_file_exists(self):
        import pathlib
        import tempfile
        from tools.publish import thumbs
        with tempfile.TemporaryDirectory() as folder:
            keep = thumbs.FOLDER
            thumbs.FOLDER = pathlib.Path(folder)
            try:
                (thumbs.FOLDER / f"{thumbs.name_of('https://a.example/x')}.webp").write_bytes(b"x")
                rows = thumbs.attach([{"id": "1", "link": "https://a.example/x"}, {"id": "2", "link": "https://a.example/y"}, {"id": "3", "link": "https://a.example/x", "withdrawn": True}])
            finally:
                thumbs.FOLDER = keep
        self.assertTrue(rows[0]["thumb"].startswith("assets/thumbs/") and rows[0]["thumb"].endswith(".webp"))
        self.assertEqual(rows[0]["thumbKind"], "page")
        self.assertEqual(thumbs.kind_of("https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32025R2083"), "pdf")
        self.assertNotIn("thumb", rows[1])
        self.assertNotIn("thumb", rows[2])

    def test_finish_crops_below_the_letterhead_and_rejects_blank_pictures(self):
        import pathlib
        import tempfile
        from PIL import Image
        from tools.thumbs import finish
        with tempfile.TemporaryDirectory() as folder:
            page = Image.new("RGB", (900, 1273), "white")
            page.paste((200, 30, 30), (0, 0, 900, 150))      # 머리 띠(잘려 나가야 한다)
            page.paste((20, 40, 120), (100, 300, 800, 420))   # 제목 자리
            source = pathlib.Path(folder) / "a.png"
            page.save(source)
            target = pathlib.Path(folder) / "out" / "a.webp"
            self.assertEqual(finish.make(source, "pdf", target), "")
            made = Image.open(target).convert("RGB")
            self.assertEqual(made.size, finish.SIZE)
            self.assertGreater(min(made.getpixel((240, 4))), 200)   # 맨 위는 흰 바탕(머리 띠가 없다)
            self.assertLess(made.getpixel((240, 110))[0], 90)      # 제목 자리의 색이 보인다
            Image.new("RGB", (960, 600), "white").save(source)
            self.assertEqual(finish.make(source, "page", target), "빈 그림")


class FeedTest(unittest.TestCase):
    def test_news_feed_lists_the_newest_items_and_skips_withdrawn_ones(self):
        import xml.etree.ElementTree as tree
        from tools.publish import feed
        items = [{"id": "a", "title": "A & B", "summary": "요약 <1>", "link": "https://x.example/a?b=1&c=2", "published": "2026-11-01", "topic": "law", "sourceName": "출처"},
                 {"id": "b", "title": "B", "summary": "내린 것", "link": "https://x.example/b", "published": "2026-11-05", "withdrawn": True},
                 {"id": "c", "title": "C", "summary": "게시일 없음", "link": "https://x.example/c", "listed": "2026-11-09"}]
        root = tree.fromstring(feed.news(items, [{"code": "law", "name": "제도·법령"}], "https://site.example/", "2026-11-10T09:00:00+09:00"))
        space = {"a": "http://www.w3.org/2005/Atom"}
        titles = [node.findtext("a:title", namespaces=space) for node in root.findall("a:entry", space)]
        self.assertEqual(titles, ["C", "A & B"])
        first = root.findall("a:entry", space)[1]
        self.assertEqual(first.find("a:link", space).get("href"), "https://x.example/a?b=1&c=2")
        self.assertEqual(first.find("a:category", space).get("term"), "제도·법령")
        self.assertIn("요약 <1>", first.findtext("a:summary", namespaces=space))

    def test_rules_feed_marks_press_reports(self):
        import xml.etree.ElementTree as tree
        from tools.publish import feed
        body = {"regulations": [{"id": "r1", "name": "규제 하나", "stage": "협상 중", "timeline": [
            {"date": "2026-10-20", "text": "첫 회의가 열렸다는 보도가 있었습니다.", "source": "매체", "link": "https://m.example/1", "basis": "press"},
            {"date": "2026-09-15", "text": "의회가 입장을 채택했습니다.", "source": "의회", "link": "https://p.example/2", "basis": "stored"}]}]}
        root = tree.fromstring(feed.rules(body, "https://site.example/", "2026-11-10T09:00:00+09:00"))
        space = {"a": "http://www.w3.org/2005/Atom"}
        entries = root.findall("a:entry", space)
        self.assertEqual(len(entries), 2)
        self.assertTrue(entries[0].findtext("a:summary", namespaces=space).startswith("[언론 보도] "))
        self.assertFalse(entries[1].findtext("a:summary", namespaces=space).startswith("[언론 보도]"))


class PositionsTest(unittest.TestCase):
    def table(self, **changes):
        book = {"asOf": "2026-11-11", "note": "세 안은 협상의 출발점입니다.",
                "parties": [{"key": "a", "name": "가 기관", "date": "2026-01-01", "source": "문서 1", "link": "https://a.example/1"},
                            {"key": "b", "name": "나 기관", "date": "2026-02-01", "source": "문서 2", "link": "https://b.example/2"}],
                "rows": [{"topic": "쟁점 하나", "a": {"text": "넣음", "evidence": {"path": "data/regulations.json", "contains": ["regulations"]}}, "b": {"text": ""}}]}
        book.update(changes)
        return {"id": "r1", "positions": book}

    def test_a_sound_table_has_no_problems_and_empty_cells_are_allowed(self):
        from tools.check import term_check
        from tools.publish import regulations
        self.assertEqual(regulations.position_problems(self.table(), term_check.load(), ("format", "evidence")), [])
        self.assertEqual(regulations.position_problems({"id": "r1"}, term_check.load(), ("format", "evidence")), [])

    def test_evidence_must_hold_and_a_missing_clause_can_be_shown_by_absence(self):
        from tools.check import term_check
        from tools.publish import regulations
        wrong = self.table(rows=[{"topic": "쟁점", "a": {"text": "넣음", "evidence": {"path": "data/regulations.json", "contains": ["이 글은 자료에 없다 zzz"]}}}])
        self.assertTrue(any("근거 어긋남" in what for _, what in regulations.position_problems(wrong, term_check.load(), ("format", "evidence"))))
        self.assertEqual(regulations.evidence_problem({"path": "data/regulations.json", "lacks": ["이 글은 자료에 없다 zzz"]}, ""), "")
        self.assertIn("없어야 할 글", regulations.evidence_problem({"path": "data/regulations.json", "lacks": ["REGULATIONS"]}, ""))
        blank = self.table(rows=[{"topic": "쟁점", "a": {"text": ""}, "b": {}}])
        self.assertTrue(any("모두 비어" in what for _, what in regulations.position_problems(blank, term_check.load(), ("format",))))

    def test_the_public_copy_keeps_the_text_and_drops_the_evidence(self):
        import json
        from tools.publish import regulations
        with open("data/regulations.json", encoding="utf-8") as handle:
            body = json.load(handle)
        shown = next(rule for rule in regulations.public(body, [])["regulations"] if rule["id"] == "cbam-downstream")
        self.assertGreaterEqual(len(shown["positions"]["rows"]), 6)
        self.assertNotIn("evidence", json.dumps(shown["positions"]))
        self.assertTrue(all(set(row) == {"topic", "commission", "council", "parliament"} for row in shown["positions"]["rows"]))

    def test_the_council_counts_in_the_table_match_the_code_list(self):
        import json
        with open("data/cn.json", encoding="utf-8") as handle:
            council = json.load(handle)["council"]
        with open("data/regulations.json", encoding="utf-8") as handle:
            rule = next(rule for rule in json.load(handle)["regulations"] if rule["id"] == "cbam-downstream")
        cell = rule["positions"]["rows"][0]["council"]["text"]
        self.assertIn(f"{len(council['added'])}개를 더하고", cell)
        self.assertIn(f"{len(council['removed'])}개를 뺌", cell)


class ReviseTest(unittest.TestCase):
    ITEMS = [
        {"id": "a", "brief": True, "kind": "국내", "published": "2026-10-01", "link": "https://k.example/view?id=1", "title": "자료 1", "summary": "올라온 자료입니다."},
        {"id": "b", "brief": True, "kind": "행사", "published": "2026-11-01", "link": "https://k.example/view?id=2", "title": "교육 안내", "summary": "안내입니다."},
        {"id": "c", "brief": True, "kind": "행사", "published": "2025-03-01", "link": "https://k.example/view?id=3", "title": "지난 교육", "summary": "안내입니다."},
        {"id": "d", "brief": True, "kind": "국내", "published": "2026-10-20", "link": "https://k.example/list", "title": "공지 1", "summary": "공지입니다."},
        {"id": "e", "brief": True, "kind": "국내", "published": "2026-10-21", "link": "https://k.example/list", "title": "공지 2", "summary": "공지입니다."},
        {"id": "f", "brief": True, "briefChecked": "2026-11-10", "kind": "국내", "published": "2026-10-25", "link": "https://k.example/view?id=6", "title": "살펴본 것", "summary": "자료입니다."},
        {"id": "g", "kind": "국내", "published": "2026-11-05", "link": "https://k.example/view?id=7", "title": "이미 요약한 것", "summary": "요약이 있습니다."},
        {"id": "h", "brief": True, "briefTries": 2, "kind": "국내", "published": "2026-11-06", "link": "https://k.example/view?id=8", "title": "두 번 실패한 것", "summary": "자료입니다."},
        {"id": "i", "brief": True, "briefTries": 1, "kind": "국내", "published": "2026-09-01", "link": "https://k.example/view?id=9", "title": "한 번 실패한 것", "summary": "자료입니다."},
        {"id": "j", "brief": True, "sourceCode": "compass", "kind": "국내", "published": "2026-11-08", "link": "https://c.example/view?idx=1", "title": "자동 읽기를 막아 둔 곳의 글", "summary": "자료입니다."},
    ]

    def test_candidates_put_materials_first_and_skip_what_cannot_or_need_not_be_redone(self):
        from tools.publish import revise
        picked = [row["id"] for row in revise.candidates(self.ITEMS, 10, now="2026-11-11")]
        self.assertEqual(picked, ["a", "i", "b"])  # 자료 먼저(한 번 실패한 것은 다시 고른다), 그다음 아직 지나지 않은 행사. 같은 주소를 쓰는 것, 지난 행사, 살펴본 것, 요약이 있는 것, 두 번 실패한 것은 빠진다

    def test_a_new_summary_must_be_polite_long_enough_and_backed_by_the_page(self):
        from tools.publish import revise
        old = self.ITEMS[0]
        source = "2026년 10월 1일 게시. 철강 제품의 내재배출량 산정 사례 12건을 담은 안내서."
        good = "한국환경공단이 철강 제품의 내재배출량 산정 사례 12건을 담은 안내서를 2026년 10월 1일에 올렸습니다. 사업장이 산정 보고서를 쓸 때 참고할 수 있는 자료입니다."
        self.assertEqual(revise.problems(old, good, "", source), [])
        self.assertTrue(any("사실 대조" in line for line in revise.problems(old, good.replace("12건", "15건"), "", source)))
        self.assertTrue(any("문체" in line for line in revise.problems(old, good.replace("올렸습니다.", "올렸다."), "", source)))
        self.assertTrue(any("길이" in line for line in revise.problems(old, "짧은 글입니다.", "", source)))
        self.assertTrue(any("비어" in line for line in revise.problems(old, good, "", "  ")))
