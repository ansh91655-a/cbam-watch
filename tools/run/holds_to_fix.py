"""보류된 초안 가운데 한 번 다시 써 볼 것을 고른다.

검증에서 보류된 초안은 그대로 두면 영영 게시되지 않는다. 글을 고치면 풀리는 사유(용어, 문체, 사실, 근거, 의무, 형식, 재이용)로
보류된 초안은 수집·작성 실행이 보류 사유를 보고 한 번만 다시 쓴다. 다시 쓴 초안이 또 보류되면 더 손대지 않는다.
쓰는 법: python -m tools.run.holds_to_fix --db-dir /tmp/run/db --out /tmp/run/fix.json [--limit 5]
"""
import argparse
import sys

from tools.common.jsonio import write_json
from tools.run import dbdump

FIXABLE = {"용어", "문체", "사실", "근거", "의무", "형식", "재이용"}


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("--db-dir", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args(argv)
    items = dbdump.docs(args.db_dir, "items")
    verdicts = dbdump.docs(args.db_dir, "verdicts")
    already_revised = {item.get("revises") for item in items.values() if item.get("revises")}
    fix = []
    for item_id, verdict in sorted(verdicts.items()):
        item = items.get(item_id)
        if item is None or verdict.get("result") != "hold" or verdict.get("gate") not in FIXABLE:
            continue
        if item_id in already_revised or item.get("revises"):  # 이미 다시 썼거나, 다시 쓴 것이 또 보류된 경우
            continue
        fix.append({"item": item, "gate": verdict.get("gate", ""), "why": verdict.get("why", ""), "newId": f"{item_id}-r2"})
    write_json(args.out, {"fix": fix[:args.limit], "waiting": max(0, len(fix) - args.limit)})
    print(f"다시 쓸 보류 초안 {len(fix[:args.limit])}건")
    for row in fix[:args.limit]:
        print(f"  {row['item'].get('id')} [{row['gate']}] {row['why'][:80]}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
