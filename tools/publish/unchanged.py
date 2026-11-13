"""만든 사이트가 지난 배포와 같은지 본다. 같으면 다시 싣지 않는다.

수집이나 썸네일 실행이 끝날 때마다 배포가 한 번 더 도는데, 바뀐 것이 없을 때가 많다. GitHub Pages는 한 시간에 열 번까지만
다시 싣기를 권하므로, 그런 배포는 올리지 않고 끝낸다. 만든 시각(builtAt)만 다른 것은 같은 것으로 본다.
그날의 첫 배포는 같아도 싣는다(상태 점검이 '오늘 배포되었는지'를 본다).

    python3 -m tools.publish.unchanged <사이트 폴더>    # 같으면 0, 다르거나 알 수 없으면 1로 끝난다

사이트 폴더는 지난 배포를 받아 두고(git fetch) 이번에 만든 것을 모두 담아 둔(git add -A) 저장소다.
"""
import json
import pathlib
import subprocess
import sys

from tools.common.jsonio import KST, today

STAMPED = ["data/site.json", "data/documents.json"]  # 만든 시각이 적히는 파일


def _git(folder, *arguments):
    try:
        done = subprocess.run(["git", "-C", str(folder), *arguments], capture_output=True, timeout=300)
        return done.returncode == 0, done.stdout.decode("utf-8", "replace")
    except Exception:
        return False, ""


def _body(text):
    body = json.loads(text)
    body.pop("builtAt", None)
    return body


def unchanged(out, ref="origin/gh-pages", day=None):
    """지난 배포(ref)가 오늘 것이고, 만든 시각 말고는 이번에 만든 것과 같은가. 알 수 없으면 False."""
    import datetime

    out = pathlib.Path(out)
    found, when = _git(out, "log", "-1", "--format=%cI", ref)
    try:
        if not found or datetime.datetime.fromisoformat(when.strip()).astimezone(KST).date().isoformat() != (day or today()):
            return False
    except ValueError:
        return False
    if not _git(out, "diff", "--cached", "--quiet", "--no-renames", ref, "--", ".", *[f":(exclude){name}" for name in STAMPED])[0]:
        return False
    for name in STAMPED:
        found, before = _git(out, "show", f"{ref}:{name}")
        try:
            if not found or _body(before) != _body((out / name).read_text(encoding="utf-8")):
                return False
        except (OSError, ValueError, AttributeError):
            return False
    return True


if __name__ == "__main__":
    sys.exit(0 if len(sys.argv) == 2 and unchanged(sys.argv[1]) else 1)
