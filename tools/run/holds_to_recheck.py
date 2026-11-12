"""원문을 열지 못해 보류된 초안을, 글은 그대로 두고 다시 검증에 낸다.

검증·게시 실행이 원문을 열지 못하면(웹 읽기 도구의 거절, 사이트의 일시 장애) 그 초안은 '확인 불가'로 보류된다.
판정이 붙은 초안은 다시 검증되지 않으므로 그대로 두면 영영 게시되지 않는다. 그래서 id만 바꾼 사본을 새 초안으로 낸다.
두 번까지 다시 내고(-c2, -c3), 세 번째에도 열지 못하면 사람이 볼 보류로 남는다(규칙은 tools/run/rechecks.py).
쓰는 법: python -m tools.run.holds_to_recheck --db-dir /tmp/run/db --out-dir /tmp/run/out --run-id collect-20261112-0705
사본은 <out-dir>/items/<새 id>.json 으로 쓰인다. 수집·작성 실행이 다른 초안과 함께 데이터베이스에 올린다.
"""
import argparse
import datetime
import json
import pathlib
import sys

from tools.common.jsonio import now_kst, stamp, write_json
from tools.run import dbdump, rechecks

MAX_AGE_DAYS = 7  # 이보다 오래된 보류는 다시 내지 않는다(묵은 소식을 뒤늦게 싣지 않으려는 것)


def _too_old(verdict, moment):
    try:
        judged = datetime.datetime.fromisoformat(str(verdict.get("at", "")))
    except ValueError:
        return False  # 판정 시각을 읽지 못하면 막지 않는다
    if judged.tzinfo is None:
        judged = judged.replace(tzinfo=moment.tzinfo)
    return moment - judged > datetime.timedelta(days=MAX_AGE_DAYS)


def pick(items, verdicts, moment):
    """다시 낼 (초안, 새 id)의 목록. 이미 다시 낸 것, 세 번째까지 간 것, 오래된 것은 뺀다."""
    resubmitted = {item.get("rechecks") for item in items.values() if item.get("rechecks")}
    rows = []
    for item_id, verdict in sorted(verdicts.items()):
        item = items.get(item_id)
        if item is None or verdict.get("result") != "hold" or verdict.get("gate") != rechecks.GATE:
            continue
        new_id = rechecks.next_id(item_id)
        if not new_id or item_id in resubmitted or new_id in items or _too_old(verdict, moment):
            continue
        rows.append((item, new_id))
    return rows


def copy_of(item, new_id, run_id, moment):
    return {**item, "id": new_id, "rechecks": item.get("id", ""), "writtenAt": stamp(moment), "runId": run_id}


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("--db-dir", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args(argv)
    moment = now_kst()
    rows = pick(dbdump.docs(args.db_dir, "items"), dbdump.docs(args.db_dir, "verdicts"), moment)
    chosen = rows[:args.limit]
    for item, new_id in chosen:
        write_json(pathlib.Path(args.out_dir) / "items" / f"{new_id}.json", copy_of(item, new_id, args.run_id, moment))
    print(json.dumps({
        "resubmitted": [{"id": new_id, "rechecks": item.get("id", ""), "turn": rechecks.attempt(new_id)} for item, new_id in chosen],
        "waiting": max(0, len(rows) - args.limit),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
