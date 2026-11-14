"""보고 실행의 결과를 정리한다: 마지막 답변 글, 알림 한 줄, 저장소에 올리는 보고 파일.

쓰는 법:
  python -m tools.run.write_report daily --health H.json --day D.json
  python -m tools.run.write_report weekly --run-file <주간 실행 기록>.json --health H.json
출력은 한 줄 JSON이다: {"status", "answer", "notify", "file"}.
- answer: 실행의 마지막 답변으로 그대로 쓰는 글(운영자만 본다)
- notify: 알림 도구에 넣는 한 줄(200자 이내). 알릴 것이 없으면 빈 글
- file: 저장소에 쓴 보고 파일. 저장소가 공개이므로 초안의 내용, 보류 사유, 실행이 직접 적은 글은 넣지 않는다.
  이 파일이 올라오면 '운영 알림' 워크플로가 읽고, 알릴 것이 있으면 저장소의 '운영 보고' 이슈에 적는다.
"""
import argparse
import json
import sys

from tools.common.jsonio import read_json, stamp, today, write_json
from tools.common.siteinfo import site_url
from tools.run.day_summary import FIXED_PROBLEMS

SITE = site_url()
NOTIFY_LIMIT = 200
UNREACHABLE_SHOWN = 4   # 주간 보고에 이름을 적는, 자동으로 받지 못하는 문서의 수


def _number(value):
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _cut(text, limit):
    text = " ".join(str(text).split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def daily(health, day):
    date = day.get("date") or health.get("today") or today()
    health_problems = [str(line) for line in health.get("problems", []) or []]
    day_problems = [str(line) for line in day.get("problems", []) or []]
    holds = [hold for hold in day.get("finalHolds", []) or [] if hold.get("id")]
    published = _number((day.get("counts") or {}).get("published"))
    total = _number(health.get("publishedItems"))
    retry = _number(day.get("retryHolds"))
    problems = health_problems + day_problems
    trouble = bool(problems or holds)
    tail = f"새 게시 {published}건(누적 {total}건)."
    # 해설서의 절이 가리킨 규제가 달라져 그 절을 다시 봐야 하는 것. 문제가 아니므로 '정상'을 바꾸지 않는다(주간 작업이 다시 보고 기록을 고친다)
    review = [str(line) for line in health.get("handbookToReview", []) or []]

    if trouble:
        lines = [f"문제 보고: {date} CBAM 규제동향 사이트"]
        if problems:
            lines.append(f"- 문제 {len(problems)}건")
            lines += [f"  - {line}" for line in problems]
        if holds:
            lines.append(f"- 보류 {len(holds)}건")
            lines += [f"  - {hold['id']}: {hold.get('gate', '')} {hold.get('why', '')}".rstrip() for hold in holds]
        if review:
            lines.append(f"- 해설서에서 다시 볼 절 {len(review)}건(문제 아님)")
            lines += [f"  - {line}" for line in review]
        lines.append(f"{tail} 사이트 {SITE}")
        answer = "\n".join(lines)
        first = problems[0] if problems else f"{holds[0]['id']} 보류"
        notify = _cut(f"문제 보고: CBAM 사이트 {date} 문제 {len(problems)}건, 보류 {len(holds)}건. {first}", NOTIFY_LIMIT)
    else:
        answer = f"정상: {date} {tail} 보고할 문제 없음." + (f" 다시 쓸 초안 {retry}건." if retry else "")
        if review:
            answer += "\n" + "\n".join([f"해설서에서 다시 볼 절 {len(review)}건(문제 아님. 주간 작업이 다시 봄)"] + [f"- {line}" for line in review])
        notify = ""

    public = {
        "kind": "daily", "date": date, "writtenAt": stamp(), "status": "문제" if trouble else "정상",
        "problems": health_problems + [line for line in day_problems if line in FIXED_PROBLEMS],
        "runProblems": sum(1 for line in day_problems if line not in FIXED_PROBLEMS),
        "holds": [{"id": hold["id"], "gate": hold.get("gate", "")} for hold in holds],
        "counts": {"published": published, "total": total, "retryHolds": retry},
        "handbookToReview": review,
    }
    path = f"reports/daily/{date}.json"
    write_json(path, public)
    return {"status": public["status"], "answer": answer, "notify": notify, "file": path}


def weekly(run, health):
    week = str(run.get("week", ""))
    start, _, end = week.partition("_")
    counts = {key: _number((run.get("counts") or {}).get(key)) for key in ("items", "digest", "audited", "match", "mismatch", "unknown", "withdrawn")}
    mismatches = [row for row in run.get("mismatches", []) or [] if row.get("id")]
    problems = [str(line) for line in run.get("problems", []) or []]
    unreachable = _number(health.get("originalsUnreachable"))

    lines = [
        f"주간 작업: {start} ~ {end}",
        f"새 소식 {counts['items']}건, 주간 요약 {'실음' if counts['digest'] else '싣지 않음'}. "
        f"다시 대조 {counts['audited']}건: 일치 {counts['match']}, 어긋남 {counts['mismatch']}, 확인 불가 {counts['unknown']}",
    ]
    if mismatches:
        lines.append("- 어긋나서 요약을 내린 항목")
        lines += [f"  - {row['id']}: {row.get('why', '')}".rstrip() for row in mismatches]
    if problems:
        lines.append("- 문제")
        lines += [f"  - {line}" for line in problems]
    # 무엇을 받지 못하는지 이름을 몇 개 적는다(원문 사이트가 자동 열람에 내주지 않는 문서. 사람이 원문 화면에서 볼 수 있다)
    named = [str(name) for name in health.get("originalsUnreachableNames", []) or [] if str(name).strip()]
    which = f"({', '.join(named[:UNREACHABLE_SHOWN])}{f' 외 {len(named) - UNREACHABLE_SHOWN}건' if len(named) > UNREACHABLE_SHOWN else ''})" if named else ""
    lines.append(f"자동으로 받지 못하는 문서 링크 {unreachable}건{which}. 사이트 {SITE}")
    notify = _cut(
        f"주간 작업 {start}~{end}: 새 소식 {counts['items']}건, 다시 대조 어긋남 {counts['mismatch']}건, 문제 {len(problems)}건", NOTIFY_LIMIT
    )

    public = {
        "kind": "weekly", "from": start, "to": end, "date": today(), "writtenAt": stamp(),
        "status": "문제" if (mismatches or problems) else "정상",
        "counts": counts,
        "withdrawnIds": [row["id"] for row in mismatches],
        "runProblems": len(problems),
        "unreachableDocs": unreachable,
        "publishedTotal": _number(health.get("publishedItems")),
        "withdrawnTotal": _number(health.get("withdrawn")),
    }
    path = f"reports/weekly/{end or today()}.json"
    write_json(path, public)
    return {"status": public["status"], "answer": "\n".join(lines), "notify": notify, "file": path}


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("kind", choices=["daily", "weekly"])
    parser.add_argument("--health", required=True)
    parser.add_argument("--day", default="")
    parser.add_argument("--run-file", default="")
    args = parser.parse_args(argv)
    health = read_json(args.health, None)
    if health is None:
        print(json.dumps({"error": "health 파일을 읽지 못함"}, ensure_ascii=False))
        return 1
    if args.kind == "daily":
        day = read_json(args.day, None)
        if day is None:
            print(json.dumps({"error": "day 파일을 읽지 못함"}, ensure_ascii=False))
            return 1
        result = daily(health, day)
    else:
        run = read_json(args.run_file, None)
        if run is None:
            print(json.dumps({"error": "실행 기록 파일을 읽지 못함"}, ensure_ascii=False))
            return 1
        result = weekly(run, health)
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
