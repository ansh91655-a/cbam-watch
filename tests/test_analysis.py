"""규제마다의 분석 글: 꼴과 근거의 검사, 사이트용 변환, 넣고 꺼내는 도구, 뒤처진 글을 알리는 점검을 확인한다."""
import argparse
import contextlib
import io
import json
import pathlib
import tempfile
import unittest
from unittest import mock

from tools.publish import analysis, regulations, rule_edit
from tools.run import rules_health

STORED = "collected/archive/pages/ec-press/ip_25_3088.txt"  # '180'과 2028년 1월 1일이 실려 있는 보도자료


def written(**changes):
    """검사를 통과하는 분석 글 하나."""
    body = {"asOf": "2026-11-11", "basedOn": {"stage": "제안", "events": 1},
            "sections": [{"key": "background", "items": [{"text": "배경을 적은 문단입니다.", "refs": ["release"]}]},
                         {"key": "content", "items": [{"label": "더하는 품목", "text": "하류제품 180개를 2028년 1월 1일부터 더합니다.", "refs": ["release"]}]},
                         {"key": "situation", "items": [{"text": "협상이 열렸다는 보도가 있습니다.", "refs": ["news"]}]}],
            "sources": [{"key": "release", "text": "EU 집행위원회 보도자료", "url": "https://example.eu/release", "basis": "stored", "path": STORED},
                        {"key": "news", "text": "신문 보도", "url": "https://example.com/news", "basis": "press", "checkedOn": "2026-11-10"}]}
    body.update(changes)
    return body


def rule(**changes):
    body = {"id": "sample-rule", "name": "표본 규정", "stage": "제안", "timeline": [{"date": "2025-12-17"}], "analysis": written()}
    body.update(changes)
    return body


def whats(body, kinds=("format", "evidence")):
    terms = regulations.term_check.load()
    return [what for _, what in analysis.problems(body, lambda text: regulations.text_problems(text, terms), kinds)]


class AnalysisCheckTest(unittest.TestCase):
    def test_a_sound_analysis_passes_and_a_rule_without_one_is_left_alone(self):
        self.assertEqual(whats(rule()), [])
        self.assertEqual(whats(rule(analysis=None)), [])

    def test_sections_must_be_the_known_ones_in_order_and_the_first_three_are_needed(self):
        sections = written()["sections"]
        self.assertIn("'쟁점과 정세' 절이 없음", whats(rule(analysis=written(sections=sections[:2]))))
        self.assertIn("절의 차례가 정해진 차례와 다름", whats(rule(analysis=written(sections=[sections[1], sections[0], sections[2]]))))
        odd = sections + [{"key": "outlook", "items": [{"text": "전망입니다.", "refs": ["release"]}]}]
        self.assertTrue(any("가운데 하나가 아님" in what for what in whats(rule(analysis=written(sections=odd)))))

    def test_every_paragraph_points_at_a_listed_source_and_every_source_is_used(self):
        body = written()
        body["sections"][0]["items"][0]["refs"] = []
        self.assertIn("근거 자료(refs)가 없음", whats(rule(analysis=body)))
        body["sections"][0]["items"][0]["refs"] = ["nowhere"]
        self.assertTrue(any("없는 근거 자료를 가리킴" in what for what in whats(rule(analysis=body))))
        body = written()
        body["sources"].append({"key": "spare", "text": "쓰지 않은 자료", "url": "https://example.eu/spare", "basis": "web", "checkedOn": "2026-11-10"})
        self.assertTrue(any("어느 문단도 가리키지 않는 근거 자료" in what for what in whats(rule(analysis=body))))

    def test_writing_rules_apply_to_paragraphs_and_their_names(self):
        body = written()
        body["sections"][0]["items"][0]["text"] = "배경을 적은 문단이다."
        body["sections"][1]["items"][0]["label"] = "수입업체의 품목"
        found = whats(rule(analysis=body))
        self.assertTrue(any("plain-ending" in what for what in found))
        self.assertTrue(any("수입업체" in what for what in found))

    def test_a_paragraph_resting_on_the_press_must_say_so(self):
        body = written()
        body["sections"][2]["items"][0]["text"] = "협상이 열렸습니다."
        self.assertIn("언론 보도에 기댄 문단인데 글에 '보도'라는 말이 없음", whats(rule(analysis=body)))

    def test_dates_and_numbers_are_held_against_the_stored_text(self):
        body = written()
        body["sections"][1]["items"][0]["text"] = "하류제품 185개를 2028년 2월 1일부터 더합니다."
        found = whats(rule(analysis=body))
        self.assertEqual(len(found), 1)
        self.assertTrue(found[0].startswith("근거 어긋남") and "185" in found[0] and "2028-02-01" in found[0])
        # 꼴만 볼 때는 근거가 어긋난 것을 문제로 치지 않는다(사이트 만들기를 멈추지 않는다)
        self.assertEqual(whats(rule(analysis=body), kinds=("format",)), [])
        # 모아 두지 않은 자료를 함께 가리키는 문단은 글과 대조하지 않는다
        body["sources"].append({"key": "page", "text": "공식 화면", "url": "https://example.eu/page", "basis": "web", "checkedOn": "2026-11-10"})
        body["sections"][1]["items"][0]["refs"] = ["release", "page"]
        self.assertEqual(whats(rule(analysis=body)), [])

    def test_stored_sources_must_be_collected_material_that_can_be_read(self):
        body = written()
        body["sources"][0]["path"] = "README.md"
        self.assertTrue(any("모아 둔 자료를 읽지 못함" in what for what in whats(rule(analysis=body))))
        body["sources"][0] = {"key": "release", "text": "자료", "url": "https://example.eu/a", "basis": "stored"}
        self.assertTrue(any("글 파일(path)이나 목록의 줄(index, where)이 없음" in what for what in whats(rule(analysis=body))))
        body["sources"][0] = {"key": "release", "text": "자료", "url": "http://example.eu/a", "basis": "web"}
        found = whats(rule(analysis=body))
        self.assertTrue(any("주소(https)가 온전하지 않음" in what for what in found))
        self.assertTrue(any("확인한 날(checkedOn)이 없음" in what for what in found))

    def test_a_line_of_a_stored_list_can_be_the_source(self):
        body = written()
        body["sources"][0] = {"key": "release", "text": "EUR-Lex", "url": "https://example.eu/a", "basis": "stored", "index": "eur-lex",
                              "where": {"celex": "32025R2083", "date": "2025-10-17"}}
        body["sections"][1]["items"][0]["text"] = "규정은 2025년 10월 17일에 관보에 실렸습니다."
        self.assertEqual(whats(rule(analysis=body)), [])
        body["sources"][0]["where"]["date"] = "2025-10-18"
        self.assertTrue(any("모아 둔 자료를 읽지 못함" in what for what in whats(rule(analysis=body))))


class AnalysisShapeTest(unittest.TestCase):
    def test_goes_stale_when_the_stage_or_the_timeline_moves(self):
        self.assertFalse(analysis.stale(rule()))
        self.assertTrue(analysis.stale(rule(stage="채택")))
        self.assertTrue(analysis.stale(rule(timeline=[{"date": "2025-12-17"}, {"date": "2026-01-08"}])))
        self.assertFalse(analysis.stale(rule(analysis=None)))

    def test_public_copy_names_the_sections_and_keeps_internal_fields_out(self):
        out = analysis.public(rule(stage="채택"))
        self.assertEqual([section["title"] for section in out["sections"]], ["배경", "주요 내용", "쟁점과 정세"])
        self.assertEqual(out["sections"][1]["items"][0], {"label": "더하는 품목", "text": "하류제품 180개를 2028년 1월 1일부터 더합니다.", "refs": ["release"]})
        self.assertNotIn("label", out["sections"][0]["items"][0])
        self.assertEqual(out["sources"], [{"key": "release", "text": "EU 집행위원회 보도자료", "url": "https://example.eu/release"},
                                          {"key": "news", "text": "신문 보도", "url": "https://example.com/news", "press": True}])
        self.assertEqual((out["asOf"], out["stale"]), ("2026-11-11", True))
        self.assertIsNone(analysis.public(rule(analysis=None)))

    def test_the_site_data_carries_the_public_copy_only(self):
        source = {"asOf": "2026-11-11", "groups": [{"code": "g", "name": "묶음", "about": "묶음입니다."}],
                  "regulations": [dict(rule(), group="g", official="COM(2025) 1", kind="규정 제안", path=["제안", "채택"], at=0, summary="표본입니다.",
                                       status="제안 단계입니다.", links=[], related={"sources": [], "words": []}, changedOn="2026-11-11",
                                       timeline=[{"date": "2025-12-17", "text": "제안이 나왔습니다.", "source": "EUR-Lex", "link": "https://example.eu/a",
                                                  "basis": "web", "checkedOn": "2026-11-10"}])]}
        out = regulations.public(source, [])["regulations"][0]
        self.assertNotIn("changedOn", out)
        self.assertNotIn("basedOn", out["analysis"])
        self.assertNotIn("path", json.dumps(out["analysis"]["sources"]))
        self.assertFalse(out["analysis"]["stale"])

    def test_published_analyses_have_all_three_parts_and_point_at_reachable_addresses(self):
        body = json.loads(pathlib.Path(regulations.SOURCE).read_text(encoding="utf-8"))
        with_analysis = [one for one in body["regulations"] if one.get("analysis")]
        self.assertTrue(with_analysis)
        for one in with_analysis:
            keys = [section["key"] for section in one["analysis"]["sections"]]
            self.assertTrue({"background", "content", "situation"} <= set(keys), one["id"])
            self.assertTrue(all(source["url"].startswith("https://") for source in one["analysis"]["sources"]), one["id"])


class AnalysisEditTest(unittest.TestCase):
    def setUp(self):
        self.body = {"asOf": "2026-11-10", "groups": [], "regulations": [rule(analysis=None)]}
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.file = pathlib.Path(self.folder.name) / "analysis.json"

    def test_putting_one_in_stamps_the_day_and_the_shape_of_the_rule(self):
        self.file.write_text(json.dumps({key: written()[key] for key in ("sections", "sources")}, ensure_ascii=False), encoding="utf-8")
        with mock.patch.object(rule_edit, "today", return_value="2026-11-12"):
            rule_edit.set_analysis(self.body, argparse.Namespace(id="sample-rule", file=str(self.file)))
        stored = self.body["regulations"][0]["analysis"]
        self.assertEqual((stored["asOf"], stored["basedOn"]), ("2026-11-12", {"stage": "제안", "events": 1}))
        self.assertEqual(len(stored["sections"]), 3)
        self.assertNotIn("changedOn", self.body["regulations"][0])  # 분석을 쓴 것은 규제가 바뀐 것이 아니다

    def test_a_file_without_sections_is_refused(self):
        self.file.write_text("{}", encoding="utf-8")
        with self.assertRaises(SystemExit):
            rule_edit.set_analysis(self.body, argparse.Namespace(id="sample-rule", file=str(self.file)))
        with self.assertRaises(SystemExit):
            rule_edit.set_analysis(self.body, argparse.Namespace(id="no-such-rule", file=str(self.file)))

    def test_taking_one_out_gives_back_what_can_be_put_in_again(self):
        self.body["regulations"][0]["analysis"] = written()
        out = pathlib.Path(self.folder.name) / "out.json"
        rule_edit.show_analysis(self.body, argparse.Namespace(id="sample-rule", out=str(out)))
        again = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(sorted(again), ["sections", "sources"])
        self.assertEqual(again["sections"], written()["sections"])
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed):
            rule_edit.show_analysis(self.body, argparse.Namespace(id="sample-rule", out=""))
        self.assertEqual(json.loads(printed.getvalue()), again)

    def test_drift_in_another_rule_does_not_stop_an_edit(self):
        found = [("규제 other-rule 분석 배경 1", "근거 어긋남: 자료에서 찾지 못한 날짜 ['2026-11-11'], 수 []"),
                 ("규제 sample-rule 2026-01-08", "근거 어긋남: 기록에 없음"),
                 ("규제 other-rule", "이름이 없음"),
                 ("규제 sample-rule-2 분석 배경 1", "근거 어긋남: 자료에서 찾지 못한 날짜 [], 수 ['12']")]
        self.assertEqual(rule_edit.blocking(found, "sample-rule"), [found[1], found[2]])
        self.assertEqual(rule_edit.blocking(found, "other-rule"), [found[0], found[2]])

    def test_editing_the_rule_marks_the_day_it_changed(self):
        with mock.patch.object(rule_edit, "today", return_value="2026-11-12"):
            rule_edit.add_event(self.body, argparse.Namespace(id="sample-rule", date="2026-01-08", text="설명자료가 나왔다는 보도가 있었습니다.", source="신문",
                                                              link="https://example.com/n", basis="press", index="", where=[], path="", contains=[]))
        self.assertEqual(self.body["regulations"][0]["changedOn"], "2026-11-12")


class AnalysisHealthTest(unittest.TestCase):
    def report(self, day, **changes):
        """표본 규제 하나만 든 자료로 점검을 돌려 (알림, 집계)를 돌려준다."""
        one = dict(rule(**changes), group="g", official="COM(2025) 1", kind="규정 제안", path=["제안", "채택"], at=0, summary="표본입니다.",
                   status="제안 단계입니다.", links=[], related={"sources": [], "words": []})
        one["timeline"] = [{"date": f"2025-12-{17 + number:02d}", "text": "일이 있었습니다.", "source": "EUR-Lex", "link": "https://example.eu/a", "basis": "web",
                            "checkedOn": "2026-11-10"} for number in range(len(one["timeline"]))]
        source = {"asOf": "2026-11-11", "groups": [{"code": "g", "name": "묶음", "about": "묶음입니다."}], "regulations": [one]}
        with tempfile.TemporaryDirectory() as folder:
            path = pathlib.Path(folder) / "regulations.json"
            path.write_text(json.dumps(source, ensure_ascii=False), encoding="utf-8")
            with mock.patch.object(regulations, "SOURCE", str(path)):
                return rules_health.problems(day, False)

    def test_an_analysis_left_behind_is_reported_only_after_the_grace_days(self):
        found, counts = self.report("2026-11-20")
        self.assertEqual([what for what in found if "규제 분석" in what], [])
        self.assertEqual((counts["analyses"], counts["analysesBehind"]), (1, 0))
        moved = {"timeline": [{}, {}], "changedOn": "2026-11-18"}
        found, counts = self.report("2026-11-20", **moved)  # 이틀째: 사이트가 스스로 밝히기만 한다
        self.assertEqual([what for what in found if "규제 분석" in what], [])
        self.assertEqual(counts["analysesBehind"], 1)
        found, _ = self.report("2026-11-21", **moved)       # 사흘째부터 알린다
        self.assertTrue(any(what.startswith("규제 분석 1건이 규제가 바뀐 뒤 3일 넘게 그대로임") for what in found))


if __name__ == "__main__":
    unittest.main()
