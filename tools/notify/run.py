"""알릴 것을 찾아 저장소의 '운영 보고' 이슈에 댓글로 적는다. GitHub가 그 댓글을 저장소 주인에게 메일로 알린다.

쓰는 법:
  python -m tools.notify.run --event push    보고 파일이 올라왔을 때: 문제가 있는 일일 보고와 주간 보고를 적는다
  python -m tools.notify.run --event watch   평일 오전에: 오늘 보고 파일이 없으면 적는다(Claude 쪽 실행이 멈춘 경우)
  python -m tools.notify.run --event test --message "글"   알림 시험
  python -m tools.notify.run --event tests --sha <커밋> --url <실행 주소>   도구 검사가 실패했을 때
  --dry-run을 붙이면 적을 글만 출력한다.
"""
import argparse
import json
import os
import sys

from tools.common.jsonio import now_kst, today
from tools.notify import github, messages, reports
from tools.run import health


def pending(event, message, owner, sha="", url=""):
    """(표시, 글)의 목록. 표시가 이미 이슈에 있으면 다시 적지 않는다."""
    if event == "tests":
        return [(messages.marker("tests", sha[:12] or "unknown"), messages.tests_failed(sha, url, owner))]
    day = today()
    found = reports.load()
    notices = []
    if event == "test":
        key = now_kst().strftime("%Y%m%d-%H%M%S")
        return [(messages.marker("test", key), messages.test(message, owner))]
    for report in reports.recent(found, day):
        if not reports.needs_notice(report):
            continue
        body = {"daily": messages.daily, "weekly": messages.weekly}.get(report["kind"])
        text = body(report, owner) if body else messages.test(report.get("message", ""), owner)
        notices.append((messages.marker(report["kind"], report["_key"]), text))
    if event == "watch" and now_kst().weekday() < 5 and not reports.has_daily(found, day):
        notices.append((messages.marker("watch", day), messages.watch(day, health.report(), owner)))
    return notices


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("--event", choices=["push", "watch", "test", "tests"], required=True)
    parser.add_argument("--message", default="")
    parser.add_argument("--sha", default="")
    parser.add_argument("--url", default="")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    owner = os.environ.get("GITHUB_REPOSITORY_OWNER", "")
    notices = pending(args.event, args.message, owner, args.sha, args.url)
    if args.dry_run:
        for mark, text in notices:
            print(text + "\n" + mark + "\n")
        print(json.dumps({"pending": len(notices), "dryRun": True}, ensure_ascii=False))
        return 0
    if not notices:
        print(json.dumps({"pending": 0, "posted": 0}, ensure_ascii=False))
        return 0
    number, error = github.ensure_issue()
    if not number:
        print(json.dumps({"error": f"이슈를 찾거나 만들지 못함: {error}"}, ensure_ascii=False))
        return 1
    already = "\n".join(github.recent_comments(number))
    posted, failed = 0, []
    for mark, text in notices:
        if mark in already:
            continue
        ok, result = github.comment(number, text + "\n\n" + mark)
        if ok:
            posted += 1
        else:
            failed.append(str(result)[:200])
    print(json.dumps({"pending": len(notices), "posted": posted, "issue": number, "failed": failed}, ensure_ascii=False))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
