"""GitHub 이슈를 읽고 쓴다. gh 명령의 REST 호출만 쓴다(GITHUB_REPOSITORY, GH_TOKEN 환경 변수가 있어야 한다)."""
import datetime
import json
import os
import subprocess

LABEL = "ops-report"
TITLE = "운영 보고"
INTRO = (
    "자동 실행에 문제가 있을 때와 매주 월요일에 `github-actions`가 이 이슈에 댓글을 답니다. "
    "저장소 주인은 그 댓글을 GitHub 알림(메일)으로 받습니다. 사람이 글을 쓰는 곳이 아닙니다."
)


def _repo():
    return os.environ.get("GITHUB_REPOSITORY", "")


def api(method, path, body=None):
    """(성공 여부, 응답 JSON이나 오류 글)을 돌려준다."""
    command = ["gh", "api", "-X", method, path]
    if body is not None:
        command += ["--input", "-"]
    try:
        done = subprocess.run(command, input=json.dumps(body).encode("utf-8") if body is not None else None, capture_output=True, timeout=60)
    except Exception as error:
        return False, str(error)
    text = done.stdout.decode("utf-8", "replace")
    if done.returncode != 0:
        return False, (done.stderr.decode("utf-8", "replace") or text)[:300]
    try:
        return True, json.loads(text) if text.strip() else {}
    except ValueError:
        return True, {}


def ensure_issue():
    """'운영 보고' 이슈의 번호를 돌려준다. 없으면 만든다. 실패하면 (0, 오류 글)."""
    ok, found = api("GET", f"repos/{_repo()}/issues?labels={LABEL}&state=open&per_page=20")
    if not ok:
        return 0, found
    issues = sorted(issue["number"] for issue in found if "pull_request" not in issue)
    if issues:
        return issues[0], ""
    api("POST", f"repos/{_repo()}/labels", {"name": LABEL, "color": "003399", "description": "자동 실행의 운영 보고"})
    ok, made = api("POST", f"repos/{_repo()}/issues", {"title": TITLE, "body": INTRO, "labels": [LABEL]})
    return (made.get("number", 0), "") if ok else (0, made)


def recent_comments(number, days=10):
    since = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    ok, found = api("GET", f"repos/{_repo()}/issues/{number}/comments?per_page=100&since={since}")
    return [str(comment.get("body", "")) for comment in found] if ok else []


def comment(number, body):
    return api("POST", f"repos/{_repo()}/issues/{number}/comments", {"body": body})
