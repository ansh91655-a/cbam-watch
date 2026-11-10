"""보고 파일을 만드는 도구와 알림 글을 임시 폴더에서 확인한다."""
import contextlib
import io
import json
import os
import pathlib
import tempfile
import unittest

from tools.notify import messages, reports
from tools.run import write_report


def _write(path, value):
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


class ReportTests(unittest.TestCase):
    def setUp(self):
        self.old = os.getcwd()
        self.tmp = tempfile.TemporaryDirectory()
        os.chdir(self.tmp.name)

    def tearDown(self):
        os.chdir(self.old)
        self.tmp.cleanup()

    def _run(self, argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = write_report.main(argv)
        return code, json.loads(out.getvalue().strip().splitlines()[-1])

    def test_daily_normal_has_no_notice(self):
        _write("h.json", {"today": "2026-11-11", "problems": [], "publishedItems": 20})
        _write("d.json", {"date": "2026-11-11", "problems": [], "finalHolds": [], "retryHolds": 1, "counts": {"published": 2}})
        code, result = self._run(["daily", "--health", "h.json", "--day", "d.json"])
        self.assertEqual(code, 0)
        self.assertEqual(result["status"], "정상")
        self.assertEqual(result["notify"], "")
        self.assertIn("새 게시 2건(누적 20건)", result["answer"])
        self.assertIn("다시 쓸 초안 1건", result["answer"])
        saved = json.loads(pathlib.Path("reports/daily/2026-11-11.json").read_text(encoding="utf-8"))
        self.assertEqual(saved["status"], "정상")
        self.assertFalse(reports.needs_notice(saved))

    def test_daily_problem_keeps_private_text_out_of_public_file(self):
        _write("h.json", {"today": "2026-11-11", "problems": ["출처 자동 수집이 오늘 돌지 않음(마지막 없음)"], "publishedItems": 20})
        _write("d.json", {
            "date": "2026-11-11",
            "problems": ["검증·게시 실행 기록이 없음", "초안 x의 요약에 2027년 3월이라는 틀린 날짜가 있음"],
            "finalHolds": [{"id": "20261111-ec-news-aaaaaa", "gate": "출처", "why": "원문에 없는 수치 12.5"}],
            "retryHolds": 0, "counts": {"published": 0},
        })
        code, result = self._run(["daily", "--health", "h.json", "--day", "d.json"])
        self.assertEqual(result["status"], "문제")
        self.assertIn("원문에 없는 수치 12.5", result["answer"])
        self.assertLessEqual(len(result["notify"]), 200)
        self.assertTrue(result["notify"].startswith("문제 보고"))
        text = pathlib.Path("reports/daily/2026-11-11.json").read_text(encoding="utf-8")
        self.assertNotIn("12.5", text)
        self.assertNotIn("틀린 날짜", text)
        saved = json.loads(text)
        self.assertEqual(saved["runProblems"], 1)
        self.assertEqual(len(saved["problems"]), 2)
        body = messages.daily(saved, "someone")
        self.assertTrue(body.startswith("@someone "))
        self.assertIn("문제 3건", body)
        self.assertIn("20261111-ec-news-aaaaaa", body)

    def test_weekly_is_always_noticed(self):
        _write("h.json", {"originalsUnreachable": 11, "publishedItems": 30, "withdrawn": 1})
        _write("run.json", {"week": "2026-11-09_2026-11-15", "counts": {"items": 7, "digest": 1, "audited": 5, "match": 4, "mismatch": 1}, "mismatches": [{"id": "a-1", "why": "날짜가 다름"}], "problems": []})
        code, result = self._run(["weekly", "--health", "h.json", "--run-file", "run.json"])
        self.assertEqual(code, 0)
        self.assertIn("a-1: 날짜가 다름", result["answer"])
        saved = json.loads(pathlib.Path("reports/weekly/2026-11-15.json").read_text(encoding="utf-8"))
        self.assertNotIn("날짜가 다름", json.dumps(saved, ensure_ascii=False))
        self.assertTrue(reports.needs_notice(saved))
        self.assertIn("2026-11-09 ~ 2026-11-15", messages.weekly(saved, ""))

    def test_recent_and_missing_daily(self):
        _write("reports/daily/2026-11-10.json", {"kind": "daily", "date": "2026-11-10", "status": "문제"})
        _write("reports/daily/2026-11-01.json", {"kind": "daily", "date": "2026-11-01", "status": "문제"})
        _write("reports/daily/broken.json", ["not a report"])
        found = reports.load()
        self.assertEqual(len(found), 2)
        self.assertEqual([r["date"] for r in reports.recent(found, "2026-11-11")], ["2026-11-10"])
        self.assertFalse(reports.has_daily(found, "2026-11-11"))
        self.assertTrue(reports.has_daily(found, "2026-11-10"))


class TestsFailedNoticeTest(unittest.TestCase):
    def test_a_failed_check_is_reported_once_per_commit(self):
        from tools.notify import run
        notices = run.pending("tests", "", "owner", sha="0832b3d4c5e6f7a8", url="https://github.com/o/r/actions/runs/1")
        self.assertEqual(len(notices), 1)
        mark, text = notices[0]
        self.assertIn("tests:0832b3d4c5e6", mark)
        self.assertIn("도구 검사가 실패", text)
        self.assertIn("`0832b3d`", text)
        self.assertIn("https://github.com/o/r/actions/runs/1", text)


if __name__ == "__main__":
    unittest.main()
