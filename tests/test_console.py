"""운영 콘솔이 초안의 상태를 읽는 규칙이 저장소의 도구와 같은지 견준다.

콘솔은 브라우저에서 돌아 도구의 파이썬 규칙을 불러 쓸 수 없으므로 같은 규칙을 한 벌 더 가지고 있다(console/js/state.js).
두 벌이 어긋나면 콘솔은 '다시 낼 예정'이라고 보여 주는데 실제로는 아무도 다시 내지 않는 일이 생긴다.
"""
import contextlib
import datetime
import io
import json
import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest

from tools.common.jsonio import now_kst
from tools.run import day_summary, holds_to_fix, holds_to_recheck

ROOT = pathlib.Path(__file__).resolve().parent.parent
AGAIN = "다시 쓴 초안도 보류: "


def _case(item_id, gate, old=False, **links):
    """초안 하나와 그 판정. gate가 빈 글이면 아직 판정이 없는 초안이다.
    links에는 revises(이 초안이 다시 쓴 옛 초안)나 rechecks(이 초안이 그대로 다시 낸 옛 초안)를 준다.
    """
    moment = now_kst() - datetime.timedelta(days=30 if old else 0)
    item = {"id": item_id, "title": "제목", **links}
    if not gate:
        return item, None
    again = AGAIN if links.get("revises") else ""  # 다시 쓴 초안이 또 보류되면 검증 실행이 사유 앞에 붙이는 말
    return item, {"id": item_id, "result": "hold", "gate": gate, "why": again + "사유", "at": moment.isoformat(timespec="seconds")}


# 한 데이터베이스에 함께 들어 있는 초안들. 서로 얽히지 않게 뿌리 id를 달리했고, k와 m만 뒤따르는 초안이 있다.
CASES = [
    _case("a", "확인 불가"), _case("h-c2", "확인 불가", rechecks="h"), _case("i-c3", "확인 불가", rechecks="i-c2"), _case("b", "확인 불가", old=True),
    _case("c", "근거"), _case("j-r2", "근거", revises="j"), _case("d", "출처"), _case("e-r2", "확인 불가", revises="e"),
    _case("f-c2", "문체", rechecks="f"), _case("g", "재이용"),
    _case("k", "확인 불가"), _case("k-c2", "", rechecks="k"), _case("m", "사실"), _case("m-r2", "", revises="m"),
]


@unittest.skipUnless(shutil.which("node"), "node가 없으면 콘솔의 규칙은 시험하지 않는다")
class ConsoleStateTest(unittest.TestCase):
    def _console_states(self, cases):
        """콘솔이 데이터베이스를 읽어 상태를 붙이는 것과 같은 차례로(console/js/model.js의 load) 상태를 구한다."""
        with tempfile.TemporaryDirectory() as folder:
            path = pathlib.Path(folder) / "cases.json"
            path.write_text(json.dumps([{"item": item, "verdict": verdict} for item, verdict in cases], ensure_ascii=False), encoding="utf-8")
            script = ("import('./console/js/state.js').then(async (m) => { const fs = await import('node:fs');"
                      "const rows = JSON.parse(fs.readFileSync(process.argv[1], 'utf8'));"
                      "const revised = new Set(rows.map((row) => row.item.revises).filter(Boolean));"
                      "const resubmitted = new Set(rows.map((row) => row.item.rechecks).filter(Boolean));"
                      "console.log(JSON.stringify(rows.map((row) => m.stateOf(row.item, row.verdict, revised, resubmitted)))); })")
            done = subprocess.run(["node", "-e", script, str(path)], capture_output=True, text=True, check=True, cwd=ROOT)
        return json.loads(done.stdout)

    def test_console_and_tools_agree_on_what_happens_to_a_hold(self):
        states = dict(zip((item["id"] for item, _ in CASES), self._console_states(CASES)))
        items = {item["id"]: item for item, _ in CASES}
        verdicts = {verdict["id"]: verdict for _, verdict in CASES if verdict}
        resubmit = {item["id"] for item, _ in holds_to_recheck.pick(items, verdicts, now_kst())}
        with tempfile.TemporaryDirectory() as folder:
            for kind, docs in (("items", items), ("verdicts", verdicts)):
                for name, body in docs.items():
                    target = pathlib.Path(folder) / kind / f"{name}.json"
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text(json.dumps(body, ensure_ascii=False), encoding="utf-8")
            fix_file = pathlib.Path(folder) / "fix.json"
            with contextlib.redirect_stdout(io.StringIO()):
                holds_to_fix.main(["--db-dir", folder, "--out", str(fix_file), "--limit", "50"])
            rewrite = {row["item"]["id"] for row in json.loads(fix_file.read_text(encoding="utf-8"))["fix"]}
        self.assertEqual(resubmit, {"a", "h-c2", "e-r2"})
        self.assertEqual(rewrite, {"c", "f-c2", "g"})
        for name, state in states.items():
            with self.subTest(item=name):
                self.assertEqual(state == "보류(다시 낼 예정)", name in resubmit)
                self.assertEqual(state == "보류(다시 쓸 예정)", name in rewrite)
        self.assertEqual({name: states[name] for name in ("k", "k-c2", "m", "m-r2")},
                         {"k": "보류(다시 냄)", "k-c2": "검증 대기", "m": "보류(다시 씀)", "m-r2": "검증 대기"})
        # 그날의 요약이 '사람이 볼 보류'로 세는 것은 콘솔에서도 '확인 필요'다.
        # 요약은 그날 보류된 것만 다루므로 오래된 보류(b)와 이미 뒤따르는 초안이 있는 보류(k, m)는 견주지 않는다.
        for name, verdict in verdicts.items():
            if name not in ("b", "k", "m"):
                with self.subTest(final=name):
                    self.assertEqual(day_summary.is_final(verdict), states[name] == "보류(확인 필요)")
        self.assertEqual(states["b"], "보류(확인 필요)")

    def test_superseded_holds_are_shown_as_handled(self):
        script = ("import('./console/js/state.js').then((m) => { const hold = { result: 'hold', gate: '확인 불가', at: new Date().toISOString() };"
                  "console.log(JSON.stringify([m.stateOf({ id: 'a' }, hold, new Set(), new Set(['a'])), m.stateOf({ id: 'a' }, { result: 'hold', gate: '근거' }, new Set(['a']), new Set()),"
                  "m.stateOf({ id: 'a' }, null, new Set(), new Set()), m.stateOf({ id: 'a' }, { result: 'pass' }, new Set(), new Set()), m.turnOf('a-r2-c3')])); })")
        done = subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True, cwd=ROOT)
        self.assertEqual(json.loads(done.stdout), ["보류(다시 냄)", "보류(다시 씀)", "검증 대기", "통과", 3])


@unittest.skipUnless(shutil.which("node"), "node가 없으면 콘솔의 모듈은 시험하지 않는다")
class ConsoleBuildTest(unittest.TestCase):
    """콘솔 폴더를 만들었을 때 화면의 모듈들이 서로 맞물리는가.

    콘솔은 공개 사이트의 화면 도우미(site/js/ui/dom.js, format.js)를 복사해 쓴다.
    사이트 쪽에서 함수 하나를 빼면 콘솔은 첫 줄에서 멈춰 아무것도 그리지 못한다(2026-11-11에 viewHead가 그렇게 빠졌다).
    """

    def _link(self, folder):
        return subprocess.run(["node", "--experimental-vm-modules", "tools/dev/modlink.mjs", str(pathlib.Path(folder) / "js" / "app.js")],
                              capture_output=True, text=True, cwd=ROOT)

    def _build(self, folder):
        from tools.publish import build_console
        here = pathlib.Path.cwd()
        try:
            os.chdir(ROOT)
            with contextlib.redirect_stdout(io.StringIO()):
                build_console.main([str(folder)])
        finally:
            os.chdir(here)

    def test_built_console_modules_link(self):
        with tempfile.TemporaryDirectory() as folder:
            out = pathlib.Path(folder) / "console"
            self._build(out)
            done = self._link(out)
        self.assertEqual(done.returncode, 0, done.stdout)

    def test_a_missing_export_is_caught(self):
        with tempfile.TemporaryDirectory() as folder:
            out = pathlib.Path(folder) / "console"
            self._build(out)
            head = out / "js" / "ui" / "head.js"
            head.write_text(head.read_text(encoding="utf-8").replace("export function viewHead", "function viewHead"), encoding="utf-8")
            done = self._link(out)
        self.assertEqual(done.returncode, 1)
        self.assertIn("viewHead", done.stdout)


if __name__ == "__main__":
    unittest.main()
