"""그날의 실행 기록을 모아 한 줄 JSON으로 요약한다. 실행 확인과 보고에 쓴다.

데이터베이스의 runs 컬렉션을 파일로 받아 둔 폴더를 읽는다.
쓰는 법: python -m tools.run.day_summary --db-dir /tmp/run/db [--date 2026-11-10]
- problems: 사람에게 알릴 문제(실행 기록이 없음, 각 실행이 적은 문제, 저장소에 올리지 못함).
  수집·작성(collect), 검증·게시(verify), 임시 작업(adhoc), 번역(translate) 실행이 적은 문제를 모은다.
  번역 실행은 보고가 나간 뒤에 돌므로 전날 것까지 본다.
- finalHolds: 사람이 봐야 하는 보류(원문과 지금 화면이 다른 것, 세 번째 검증에서도 원문을 열지 못한 것, 다시 쓴 초안이 또 보류된 것)
- retryHolds: 다음 수집·작성 실행이 다시 쓰거나(글을 고치면 풀리는 사유) 그대로 다시 낼(원문을 열지 못한 것) 보류의 수. 알리지 않는다
"""
import argparse
import datetime
import json
import sys

from tools.common.jsonio import today
from tools.run import dbdump, rechecks

SOURCE_CHANGED = "출처"  # 저장소의 글과 지금 화면이 다르다. 다시 써도, 다시 내도 풀리지 않는다
AGAIN = "다시 쓴 초안도 보류"
NO_COLLECT = "수집·작성 실행 기록이 없음"
NO_VERIFY = "검증·게시 실행 기록이 없음"
NOT_PUSHED = "게시 데이터를 저장소에 올리지 못함"
# 이 프로그램이 정해 둔 문구. 실행이 직접 적은 글과 달리 공개 보고 파일에 그대로 실어도 된다.
FIXED_PROBLEMS = {NO_COLLECT, NO_VERIFY, NOT_PUSHED}


def is_final(hold):
    """더는 자동으로 풀리지 않아 사람이 봐야 하는 보류인지."""
    if hold.get("gate") == rechecks.GATE:  # 원문을 열지 못한 것은 세 번째까지 다시 낸다
        return rechecks.is_last(hold.get("id", ""))
    return hold.get("gate") == SOURCE_CHANGED or str(hold.get("why", "")).startswith(AGAIN)


def summarize(runs, day):
    mine = [run for run in runs if str(run.get("startedAt", "")).startswith(day)]
    collect = [run for run in mine if run.get("kind") == "collect"]
    verify = [run for run in mine if run.get("kind") == "verify"]
    adhoc = [run for run in mine if run.get("kind") == "adhoc"]
    yesterday = (datetime.date.fromisoformat(day) - datetime.timedelta(days=1)).isoformat()
    translate = [run for run in runs if run.get("kind") == "translate" and str(run.get("startedAt", ""))[:10] in (day, yesterday)]
    problems = []
    if datetime.date.fromisoformat(day).weekday() < 5:
        if not collect:
            problems.append(NO_COLLECT)
        if not verify:
            problems.append(NO_VERIFY)
    for run in collect + verify + adhoc + translate:
        for problem in run.get("problems", []) or []:
            text = str(problem).strip()
            if text and text not in problems:
                problems.append(text)
    if any(run.get("pushed") is False for run in verify):
        problems.append(NOT_PUSHED)
    final_holds, retry = [], 0
    for run in verify:
        for hold in run.get("holds", []) or []:
            if not hold.get("id"):
                continue
            if is_final(hold):
                final_holds.append({"id": hold["id"], "gate": hold.get("gate", ""), "why": str(hold.get("why", ""))[:120]})
            else:
                retry += 1

    def total(group, key):
        return sum(int((run.get("counts") or {}).get(key, 0) or 0) for run in group)

    return {
        "date": day, "problems": problems, "finalHolds": final_holds, "retryHolds": retry,
        "counts": {"written": total(collect, "written") + total(collect, "rewritten"), "pass": total(verify, "pass"), "hold": total(verify, "hold"), "published": total(verify, "published")},
        "runs": {"collect": len(collect), "verify": len(verify), "adhoc": len(adhoc), "translate": len(translate)},
    }


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("--db-dir", required=True)
    parser.add_argument("--date", default="")
    args = parser.parse_args(argv)
    runs = list(dbdump.docs(args.db_dir, "runs").values())
    print(json.dumps(summarize(runs, args.date or today()), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
