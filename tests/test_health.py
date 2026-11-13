"""상태 점검(tools.run.health)이 배포된 사이트에서 보는 것: 국문 PDF 나란히 보기가 빠졌는지, 배포가 밀렸는지."""
import datetime
import unittest
from unittest import mock

from tools.common.jsonio import KST
from tools.run import health


class PdfTest(unittest.TestCase):
    def test_a_full_listing_is_no_problem(self):
        self.assertEqual(health._pdf_problems({"docs": {"a": {}, "b": {}}, "wanted": 2, "failed": [], "tools": True}), [])
        self.assertEqual(health._pdf_problems({"docs": {}}), [])   # 실을 수를 적기 전의 배포는 가리지 않는다
        self.assertEqual(health._pdf_problems(None), [])

    def test_missing_documents_are_reported(self):
        found = health._pdf_problems({"docs": {"a": {}}, "wanted": 3, "failed": ["b"], "tools": True})
        self.assertEqual(len(found), 1)
        self.assertIn("3건 가운데 1건만 실림", found[0])

    def test_documents_kept_from_the_last_deployment_are_reported_with_the_cause(self):
        found = health._pdf_problems({"docs": {"a": {}, "b": {}}, "wanted": 2, "failed": [], "tools": False, "kept": ["a", "b"]})
        self.assertEqual(len(found), 1)
        self.assertIn("지난 배포의 것을 그대로 실음(a, b)", found[0])
        self.assertIn("도구 설치가 실패", found[0])


class LagTest(unittest.TestCase):
    NOW = datetime.datetime(2026, 11, 13, 15, 0, tzinfo=KST)

    def _lag(self, changed, deployed):
        with mock.patch.object(health, "_git", return_value=changed), mock.patch.object(health, "now_kst", return_value=self.NOW):
            return health._lag_problem(deployed)

    def test_a_deployment_older_than_the_last_change_is_reported_after_some_hours(self):
        found = self._lag("2026-11-13T10:00:00+09:00", "2026-11-13T00:30:00+00:00")  # 바뀐 것 10:00, 배포 09:30, 지금 15:00
        self.assertEqual(len(found), 1)
        self.assertIn("11-13 10:00에 올라갔으나 마지막 배포는 11-13 09:30", found[0])

    def test_a_fresh_change_or_a_later_deployment_is_fine(self):
        self.assertEqual(self._lag("2026-11-13T14:00:00+09:00", "2026-11-13T00:30:00+00:00"), [])   # 올라간 지 한 시간
        self.assertEqual(self._lag("2026-11-13T10:00:00+09:00", "2026-11-13T01:30:00+00:00"), [])   # 그 뒤에 배포됨
        self.assertEqual(self._lag("", "2026-11-13T01:30:00+00:00"), [])                              # 기록이 얕아 알 수 없음


class UnchangedTest(unittest.TestCase):
    """오늘 이미 실은 것과 같은 사이트는 다시 싣지 않는다(tools.publish.unchanged)."""

    def _git(self, folder, *arguments, when=None):
        import os
        import subprocess
        subprocess.run(["git", "-C", str(folder), "-c", "user.name=t", "-c", "user.email=t@example.com", *arguments], check=True, capture_output=True,
                       env={**os.environ, **({"GIT_COMMITTER_DATE": when, "GIT_AUTHOR_DATE": when} if when else {})})

    def _site(self, folder, built, title="소식", extra=None):
        import json
        import pathlib
        folder = pathlib.Path(folder)
        (folder / "data").mkdir(parents=True, exist_ok=True)
        (folder / "data/site.json").write_text(json.dumps({"builtAt": built, "name": "사이트"}), encoding="utf-8")
        (folder / "data/documents.json").write_text(json.dumps({"builtAt": built, "docs": [1, 2]}), encoding="utf-8")
        (folder / "data/items.json").write_text(json.dumps({"items": [title]}), encoding="utf-8")
        for name, body in (extra or {}).items():
            (folder / name).write_text(body, encoding="utf-8")
        return folder

    def _pair(self, folder, when, **new):
        """지난 배포(when에 올린 것)와, 그것을 받아 둔 새 사이트 폴더."""
        import pathlib
        last = self._site(pathlib.Path(folder) / "last", "2026-11-13T09:00:00+09:00")
        self._git(last, "init", "-q", "-b", "gh-pages")
        self._git(last, "add", "-A")
        self._git(last, "commit", "-q", "-m", "last", when=when)
        out = self._site(pathlib.Path(folder) / "site", "2026-11-13T11:00:00+09:00", **new)
        self._git(out, "init", "-q", "-b", "gh-pages")
        self._git(out, "remote", "add", "origin", str(last))
        self._git(out, "fetch", "-q", "origin", "gh-pages")
        self._git(out, "add", "-A")
        return out

    def test_only_the_build_time_differs(self):
        import tempfile
        from tools.publish import unchanged
        with tempfile.TemporaryDirectory() as folder:
            out = self._pair(folder, "2026-11-13T09:01:00+09:00")
            self.assertTrue(unchanged.unchanged(out, day="2026-11-13"))
            self.assertFalse(unchanged.unchanged(out, day="2026-11-14"))   # 그날의 첫 배포는 같아도 싣는다

    def test_a_changed_or_added_file_is_a_change(self):
        import tempfile
        from tools.publish import unchanged
        with tempfile.TemporaryDirectory() as folder:
            self.assertFalse(unchanged.unchanged(self._pair(folder, "2026-11-13T09:01:00+09:00", title="새 소식"), day="2026-11-13"))
        with tempfile.TemporaryDirectory() as folder:
            self.assertFalse(unchanged.unchanged(self._pair(folder, "2026-11-13T09:01:00+09:00", extra={"new.txt": "x"}), day="2026-11-13"))

    def test_without_a_last_deployment_nothing_is_skipped(self):
        import tempfile
        from tools.publish import unchanged
        with tempfile.TemporaryDirectory() as folder:
            out = self._site(folder, "2026-11-13T11:00:00+09:00")
            self._git(out, "init", "-q", "-b", "gh-pages")
            self._git(out, "add", "-A")
            self.assertFalse(unchanged.unchanged(out, day="2026-11-13"))


if __name__ == "__main__":
    unittest.main()
