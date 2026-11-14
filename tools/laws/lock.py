"""번역 실행이 겹치지 않게 하는 자물쇠.

「번역」은 여러 예약 작업이 시각을 엇갈려 돌린다(예약 작업 하나는 한 시간에 한 번까지만 돌 수 있다). 앞의 실행이 아직 도는데
다음 실행이 시작하면 같은 문단을 두 번 옮기고, 올리다가 서로 부딪친다. 그래서 실행은 시작할 때 main에 자물쇠 파일을 올려 잡고,
끝날 때 지워서 푼다. 올리기는 먼저 한 쪽만 받아들여지므로 두 실행이 함께 잡을 수 없다.

- 잡은 지 STALE_MINUTES가 지난 자물쇠는 멈춘 실행의 것으로 보고 다음 실행이 걷어 내고 잡는다.
  다만 그 사이에도 번역이 올라오고 있으면(마지막 번역 커밋이 QUIET_SECONDS 안쪽) 아직 도는 것으로 본다.
- 자물쇠 파일은 어느 자동 실행(GitHub Actions)의 경로에도 들지 않는 곳에 둔다. 자물쇠만 바뀐 커밋이 검사나 배포를 돌리지 않게 하려는 것이다.
- 번역은 묶음마다 올라오지만 사이트는 실행이 끝날 때 한 번만 다시 싣는다. 풀 때, 지난번에 실은 뒤로 올라온 번역이 있으면
  표(STAMP)를 고쳐 같은 커밋에 담고, 사이트 배포와 화면 점검이 그 파일을 보고 돈다(번역 파일만 바뀐 커밋에는 돌지 않는다).
  여러 실행이 15분마다 묶음을 올리면 배포가 한 시간에 스무 번쯤 되는데, GitHub Pages가 권하는 횟수(한 시간에 열 번)를 넘기 때문이다.
  풀지 못하고 멈춘 실행이 올려 둔 번역은 다음에 푸는 실행의 표에 함께 담긴다.
- 할 일이 없으면 잡지 않는다(끝나는 값 3). 번역이 다 끝난 뒤의 실행이 날마다 빈 커밋 한 쌍을 남기지 않게 하려는 것이다.
  번역과 검수는 서로 다른 예약 작업(다른 모델)이 한다. 그래서 잡을 때 무슨 일을 하려는지 적는다(--work): 번역하는 실행은 옮길 문단이,
  검수하는 실행은 검수할 문단이 있을 때만 잡는다. 적지 않으면 둘 가운데 하나라도 있으면 잡는다.

쓰는 법(저장소 맨 위에서)
  python3 -m tools.laws.lock take <실행 id> [--work translate|verify]
                                                잡는다. 0: 잡음, 2: 다른 실행이 도는 중(이 실행은 아무것도 하지 않고 끝낸다), 3: 할 일 없음(잡지 않는다), 1: 올리지 못함
  python3 -m tools.laws.lock release <실행 id>  푼다(자기가 잡은 것일 때만 지운다)
  python3 -m tools.laws.lock status             누가 언제 잡았는지
  python3 -m tools.laws.lock work [--work translate|verify]
                                                할 일이 있는지만 본다(잡지 않고, 아무것도 쓰지 않는다). "할 일 있음"이나 "할 일 없음: <까닭>"을 찍는다.
                                                예약 작업의 지시문이 절차서를 읽기 전에 돌린다: 번역이 모두 끝난 뒤의 실행이 날마다 긴 절차서를 읽지 않게 하려는 것이다.
                                                지금 폴더의 저장소를 있는 그대로 본다. 이 명령은 저장소를 받지 않으므로 부르는 쪽이 먼저 최신으로 받아 둔다
                                                (낡은 저장소에서는 일이 남았는데도 없다고 답할 수 있다). 끝나는 값은 둘 다 0이고, 볼 수 없으면 0이 아니다.
"""
import argparse
import datetime
import json
import pathlib
import subprocess
import sys

PATH = "locks/translating.json"
STAMP = "stamps/translated.json"  # 번역을 올린 실행이 끝났다는 표. 사이트 배포와 화면 점검이 이 파일이 바뀌면 돈다
SHOWN = "data/laws-ko"            # 사이트에 보이는 번역
STALE_MINUTES = 12     # 실행 하나는 이 안에 끝나게 되어 있다(절차서가 10분이 넘으면 새 묶음을 시작하지 않는다)
QUIET_SECONDS = 300    # 번역이 이 안에 올라왔으면 자물쇠가 낡았어도 아직 도는 것으로 본다(묶음 하나는 2분 안팎, 길면 3분 넘게 걸리고, 실행은 예정보다 1~2분 늦게 시작하기도 한다)
TRIES = 3
WATCHED = ("data/laws-ko", "language/translation-checks.json")  # 번역 실행과 검수 실행이 올리는 것
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


def _unpublished(root):
    """지난번 표 뒤로 올라온 번역이 있는가(사이트에 아직 싣지 않은 번역)."""
    last = _git(root, "log", "-1", "--format=%H", "--", STAMP, check=False).stdout.strip()
    span = [f"{last}..HEAD"] if last else ["HEAD"]
    return bool(_git(root, "rev-list", "-1", *span, "--", SHOWN, check=False).stdout.strip())


def _sync(root):
    # 실행이 남긴 올리지 않은 변경이 있어도 받을 수 있게 치워 두었다가 되돌려 놓는다
    _git(root, "pull", "-q", "--rebase", "--autostash", "origin", "main")


WORKS = ("translate", "verify")  # 번역하는 실행의 일(옮길 문단, 청해 둔 견주기 시험)과 검수하는 실행의 일(검수할 문단)


def anything_left(work=""):
    """그 일이 남았는가(지금 폴더의 저장소에서 본다). work가 "translate"이면 옮길 문단이나 청해 둔 견주기 시험, "verify"이면 검수할 문단,
    빈 글이면 둘 가운데 하나라도."""
    from tools.laws import plan, todo, verify  # 자물쇠만 쓰는 곳에서 글 전체를 읽지 않게 여기서 들인다
    if work != "verify" and (pathlib.Path("trials/request.json").exists() or any(todo.pick(runner=name)[0] for name in plan.runners())):
        return True
    return work != "translate" and bool(verify.pending())


def take(run_id, root=".", at=None, between=None, work=None):
    """자물쇠를 잡는다. 돌려주는 값: ("taken", ""), ("busy", 쥐고 있는 실행), ("idle", ""), ("failed", 까닭).

    work는 할 일이 남았는지 알려 주는 함수다. 주면 저장소를 받은 뒤에 물어보고, 없다고 하면 잡지 않는다("idle").
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
        if work is not None and not work():
            return "idle", ""
        path = pathlib.Path(root) / PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"run": run_id, "since": now.isoformat(timespec="seconds")}, ensure_ascii=False) + "\n", encoding="utf-8")
        _git(root, "add", PATH)
        if not _git(root, "status", "--porcelain", "--", PATH).stdout.strip():
            return "taken", ""  # 이미 이 실행이 같은 시각으로 잡아 둔 것
        _git(root, "commit", "-q", "-m", f"번역 실행 시작: {run_id}", "--", PATH)  # 자물쇠만 담는다(다른 변경이 섞이지 않게)
        if between:
            between()
        pushed = _git(root, "push", "-q", "origin", "HEAD:main", check=False)
        if pushed.returncode == 0:
            return "taken", ""
        why = f"올리지 못함: {pushed.stderr.strip()[:120]}"
        _git(root, "reset", "-q", "--hard", "HEAD~1")  # 내 자물쇠를 거두고, 받아서 다시 본다(다른 실행이 먼저 잡았을 수 있다)
    return "failed", why


def release(run_id, root=".", at=None):
    """자기가 잡은 자물쇠를 푼다. 돌려주는 값: "released", "not-mine"(다른 실행의 것이거나 없음), "failed".

    싣지 않은 번역이 있으면 표를 고쳐 함께 올린다(사이트가 다시 실린다).
    """
    for _ in range(TRIES):
        try:
            _sync(root)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            continue
        lock = read(root)
        if not lock or lock.get("run") != run_id:
            return "not-mine"
        _git(root, "rm", "-q", PATH)
        changed = [PATH]
        if _unpublished(root):
            stamp = pathlib.Path(root) / STAMP
            stamp.parent.mkdir(parents=True, exist_ok=True)
            now = at or datetime.datetime.now(KST)
            stamp.write_text(json.dumps({"run": run_id, "at": now.isoformat(timespec="seconds")}, ensure_ascii=False) + "\n", encoding="utf-8")
            _git(root, "add", STAMP)
            changed.append(STAMP)
        _git(root, "commit", "-q", "-m", f"번역 실행 끝: {run_id}", "--", *changed)  # 자물쇠와 표만 담는다
        if _git(root, "push", "-q", "origin", "HEAD:main", check=False).returncode == 0:
            return "released"
        _git(root, "reset", "-q", "--hard", "HEAD~1")
    return "failed"


def main(argv):
    parser = argparse.ArgumentParser(description="번역 실행이 겹치지 않게 하는 자물쇠")
    parser.add_argument("what", choices=["take", "release", "status", "work"])
    parser.add_argument("run", nargs="?", default="")
    parser.add_argument("--work", default="", choices=["", *WORKS], help="잡으려는 실행이 하는 일. 그 일이 없으면 잡지 않는다")
    args = parser.parse_args(argv)
    if args.what == "status":
        lock = read()
        now = datetime.datetime.now(KST)
        who = holder(lock, now, _last_work("."))
        print(f"자물쇠: {who}이(가) {lock.get('since', '')}부터 도는 중" if who else ("자물쇠: 낡은 것이 남아 있음" if lock else "자물쇠: 없음"))
        return 0
    nothing = {"translate": "옮길 문단이 없음", "verify": "검수할 문단이 없음"}.get(args.work, "옮길 문단도 검수할 문단도 없음")
    if args.what == "work":
        print("할 일 있음" if anything_left(args.work) else f"할 일 없음: {nothing}")
        return 0
    if not args.run:
        parser.error("실행 id를 적어 주세요")
    if args.what == "take":
        outcome, detail = take(args.run, work=lambda: anything_left(args.work))
        print({"taken": "잡음", "busy": f"다른 실행이 도는 중: {detail}", "idle": f"할 일 없음: {nothing}", "failed": f"잡지 못함: {detail}"}[outcome])
        return {"taken": 0, "busy": 2, "idle": 3, "failed": 1}[outcome]
    outcome = release(args.run)
    print({"released": "풂", "not-mine": "풀 것이 없음(다른 실행의 것이거나 이미 풀림)", "failed": "풀지 못함"}[outcome])
    return 1 if outcome == "failed" else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
