"""검증을 기다리는 항목을 고른다: 데이터베이스의 items 가운데 verdicts에 판정이 없는 것.

쓰는 법: python -m tools.run.pending_items --db-dir /tmp/run/db --out /tmp/run/pending.json
"""
import argparse
import sys

from tools.common.jsonio import write_json
from tools.run import dbdump


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("--db-dir", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args(argv)
    items = dbdump.docs(args.db_dir, "items")
    judged = dbdump.ids(args.db_dir, "verdicts")
    pending = [item for item_id, item in sorted(items.items()) if item_id not in judged]
    write_json(args.out, {"pending": pending[:args.limit], "waiting": max(0, len(pending) - args.limit)})
    print(f"검증 대기 {len(pending)}건(이번에 다룰 것 {min(len(pending), args.limit)}건)")
    for item in pending[:args.limit]:
        print(f"  {item.get('id')} [{item.get('sourceCode')}/{item.get('tier')}] {item.get('title', '')[:70]}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
