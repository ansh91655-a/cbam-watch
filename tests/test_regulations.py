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


if __name__ == "__main__":
    unittest.main()
