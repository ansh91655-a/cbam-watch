"""의견수렴 목록의 지난 단계를 남기는 셈(tools/archive/hys.py)."""
import unittest

from tools.archive import hys

FEEDBACK = {"stage": "ISC_WORKFLOW", "feedback": "OPEN", "start": "2026/07/09 11:08:21", "end": "2026/08/06 23:59:59"}
CLOSED = {**FEEDBACK, "feedback": "CLOSED"}
ADOPTED = {"stage": "ADOPTION_WORKFLOW", "feedback": "DISABLED", "start": "2026/11/25 11:51:00", "end": ""}


def entry(statuses, earlier=None):
    row = {"id": "14132", "title": "Sale and repurchase of CBAM certificates", "reference": "Ares(2024)546926", "actType": "REG_DEL", "statuses": statuses}
    if earlier is not None:
        row["earlier"] = earlier
    return row


class Remembered(unittest.TestCase):
    def test_stage_that_left_the_list_is_kept(self):
        merged = hys.with_history([entry([ADOPTED])], [entry([CLOSED])])
        self.assertEqual(merged[0]["earlier"], [CLOSED])

    def test_same_period_with_a_new_feedback_status_is_not_an_earlier_stage(self):
        merged = hys.with_history([entry([CLOSED])], [entry([FEEDBACK])])
        self.assertEqual(merged[0]["earlier"], [])

    def test_earlier_stages_survive_later_runs_in_order(self):
        planned = {"stage": "INIT_PLANNED", "feedback": "DISABLED", "start": "2024/01/18 17:32:01", "end": ""}
        first = hys.with_history([entry([CLOSED])], [entry([planned])])
        second = hys.with_history([entry([ADOPTED])], first)
        third = hys.with_history([entry([ADOPTED])], second)
        self.assertEqual(third[0]["earlier"], [planned, CLOSED])

    def test_new_initiative_has_no_history(self):
        self.assertEqual(hys.with_history([entry([FEEDBACK])], [])[0]["earlier"], [])

    def test_text_keeps_the_feedback_dates_that_the_timeline_cites(self):
        merged = hys.with_history([entry([ADOPTED])], [entry([CLOSED])])
        text = "\n".join(hys.text_lines("https://example.test/list", merged))
        for needed in ("번호: 14132", "시작: 2026/07/09", "마감: 2026/08/06", "단계: ADOPTION_WORKFLOW", "시작: 2026/11/25"):
            self.assertIn(needed, text)
        self.assertIn("앞선 단계: ISC_WORKFLOW", text)


if __name__ == "__main__":
    unittest.main()
