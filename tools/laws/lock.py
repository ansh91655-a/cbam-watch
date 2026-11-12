"""번역 실행이 겹치지 않게 하는 자물쇠.

「번역」은 여러 예약 작업이 시각을 엇갈려 돌린다(예약 작업 하나는 한 시간에 한 번까지만 돌 수 있다). 앞의 실행이 아직 도는데
다음 실행이 시작하면 같은 문단을 두 번 옮기고, 올리다가 서로 부딪친다. 그래서 실행은 시작할 때 main에 자물쇠 파일을 올려 잡고,
끝날 때 지워서 푼다. 올리기는 먼저 한 쪽만 받아들여지므로 두 실행이 함께 잡을 수 없다.

- 잡은 지 STALE_MINUTES가 지난 자물쇠는 멈춘 실행의 것으로 보고 다음 실행이 걷어 내고 잡는다.
  다만 그 사이에도 번역이 올라오고 있으면(마지막 번역 커밋이 QUIET_SECONDS 안쪽) 아직 도는 것으로 본다.
- 자물쇠 파일은 어느 자동 실행(GitHub Actions)의 경로에도 들지 않는 곳에 둔다. 잡고 푸는 커밋이 검사나 배포를 돌리지 않게 하려는 것이다.

쓰는 법(저장소 맨 위에서)
  python3 -m tools.laws.lock take <실행 id>     잡는다. 0: 잡음, 2: 다른 실행이 도는 중(이 실행은 아무것도 하지 않고 끝낸다), 1: 올리지 못함
  python3 -m tools.laws.lock release <실행 id>  푼다(자기가 잡은 것일 때만 지운다)
  python3 -m tools.laws.lock status             누가 언제 잡았는지
"""
import argparse
import datetime
import json
import pathlib
import subprocess
import sys

PATH = "locks/translating.json"
STALE_MINUTES = 12     # 실행 하나는 이 안에 끝나게 되어 있다(절차서가 10분이 넘으면 새 묶음을 시작하지 않는다)
QUIET_SECONDS = 180    # 번역이 이 안에 올라왔으면 자물쇠가 낡았어도 아직 도는 것으로 본다(묶음 하나는 90초쯤 걸린다)
TRIES = 3
WATCHED = ("data/laws-ko", "language/translation-checks.json")  # 번역 실행이 올리는 것
AUTHOR = ("-c", "user.name=cbam-watch-run", "-c", "user.email=noreply@users.noreply.github.com")
KST = datetime.timezone(datetime.timedelta(hours=9))


def _git(root, *args, check=True):
    return subprocess.run(["git", *AUTHOR, *args], cwd=root, capture_output=True, text=True, check=check, timeout=150)


def read(root="."):
    """자물쇠 파일의 내용. 없거나 깨졌으면 None."""
    try:
        return json.loads((pathlib.Path(root) / PATH).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _last_work(root):
    """번역 실행이 마지막으로 올린 커밋의 시각(초). 없으면 0."""
    done = _git(root, "log", "-1", "--format=%ct", "--", *WATCHED, check=False)
    return int(done.stdout.strip() or 0)


def holder(lock, at, last_work=0):
    """자물쇠를 쥐고 아직 도는 실행의 이름. 쥔 실행이 없거나 멈춘 것으로 보이면 빈 글."""
    if not lock or not lock.get("run"):
        return ""
    try:
        since = datetime.datetime.fromisoformat(str(lock.get("since", "")))
    except ValueError:
        return ""
    fresh = (at - since).total_seconds() < STALE_MINUTES * 60
    working = at.timestamp() - last_work < QUIET_SECONDS
    return str(lock["run"]) if fresh or working else ""


def _sync(root):
    _git(root, "pull", "-q", "--rebase", "origin", "main")


def take(run_id, root=".", at=None, between=None):
    """자물쇠를 잡는다. 돌려주는 값: ("taken", ""), ("busy", 쥐고 있는 실행), ("failed", 까닭).

    between은 시험에서만 쓴다: 자물쇠를 커밋하고 올리기 전에 부른다(그 사이에 다른 실행이 잡는 경우를 만든다).
    """
    why = ""
    for _ in range(TRIES):
        try:
            _sync(root)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
            why = f"저장소를 받지 못함: {str(getattr(error, 'stderr', '') or error).strip()[:120]}"
            continue
        now = at or datetime.datetime.now(KST)
        other = holder(read(root), now, _last_work(root))
        if other and other != run_id:
            return "busy", other
        path = pathlib.Path(root) / PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"run": run_id, "since": now.isoformat(timespec="seconds")}, ensure_ascii=False) + "\n", encoding="utf-8")
        _git(root, "add", PATH)
        if not _git(root, "status", "--porcelain", "--", PATH).stdout.strip():
            return "taken", ""  # 이미 이 실행이 같은 시각으로 잡아 둔 것
        _git(root, "commit", "-q", "-m", f"번역 실행 시작: {run_id}")
        if between:
            between()
        pushed = _git(root, "push", "-q", "origin", "HEAD:main", check=False)
        if pushed.returncode == 0:
            return "taken", ""
        why = f"올리지 못함: {pushed.stderr.strip()[:120]}"
        _git(root, "reset", "-q", "--hard", "HEAD~1")  # 내 자물쇠를 거두고, 받아서 다시 본다(다른 실행이 먼저 잡았을 수 있다)
    return "failed", why


def release(run_id, root="."):
    """자기가 잡은 자물쇠를 푼다. 돌려주는 값: "released", "not-mine"(다른 실행의 것이거나 없음), "failed"."""
    for _ in range(TRIES):
        try:
            _sync(root)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            continue
        lock = read(root)
        if not lock or lock.get("run") != run_id:
            return "not-mine"
        _git(root, "rm", "-q", PATH)
        _git(root, "commit", "-q", "-m", f"번역 실행 끝: {run_id}")
        if _git(root, "push", "-q", "origin", "HEAD:main", check=False).returncode == 0:
            return "released"
        _git(root, "reset", "-q", "--hard", "HEAD~1")
    return "failed"


def main(argv):
    parser = argparse.ArgumentParser(description="번역 실행이 겹치지 않게 하는 자물쇠")
    parser.add_argument("what", choices=["take", "release", "status"])
    parser.add_argument("run", nargs="?", default="")
    args = parser.parse_args(argv)
    if args.what == "status":
        lock = read()
        now = datetime.datetime.now(KST)
        who = holder(lock, now, _last_work("."))
        print(f"자물쇠: {who}이(가) {lock.get('since', '')}부터 도는 중" if who else ("자물쇠: 낡은 것이 남아 있음" if lock else "자물쇠: 없음"))
        return 0
    if not args.run:
        parser.error("실행 id를 적어 주세요")
    if args.what == "take":
        outcome, detail = take(args.run)
        print({"taken": "잡음", "busy": f"다른 실행이 도는 중: {detail}", "failed": f"잡지 못함: {detail}"}[outcome])
        return {"taken": 0, "busy": 2, "failed": 1}[outcome]
    outcome = release(args.run)
    print({"released": "풂", "not-mine": "풀 것이 없음(다른 실행의 것이거나 이미 풀림)", "failed": "풀지 못함"}[outcome])
    return 1 if outcome == "failed" else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
