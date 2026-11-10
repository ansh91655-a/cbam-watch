"""주간 작업이 다룰 지난주의 게시 항목을 고른다.

지난주는 오늘이 속한 주의 바로 앞 주(월요일부터 일요일, 한국 시각)다.
쓰는 법: python -m tools.run.week_items --out /tmp/run/week.json [--audit 5] [--date 2026-11-16]
- week.json: 기간, 그 주에 이 사이트에 오른 항목, 다시 대조할 표본(audit)
- 지난 소식을 한꺼번에 채운 항목(backfill 표시)은 그 주의 새 소식이 아니므로 주간 요약의 대상에서 뺀다.
  다시 대조할 표본은 이 항목들에서도 따로 뽑는다(--audit-backfill 10 --db-dir /tmp/run/db).
  데이터베이스에서 받아 둔 audits 기록에 있는 항목은 이미 대조한 것으로 보고 건너뛴다.
- 같은 폴더의 week.txt: 그 항목들의 제목과 요약을 이어 붙인 글. 주간 요약의 수치와 날짜를 대조하는 데 쓴다.
"""
import argparse
import datetime
import hashlib
import pathlib
import sys

from tools.common.jsonio import now_kst, read_json, write_json
from tools.run import dbdump

LONG_SUMMARY = 120  # 이보다 짧은 요약은 제목만 옮긴 한 줄짜리로 본다


def last_week(day):
    """그 날짜가 속한 주의 바로 앞 주의 (월요일, 일요일)."""
    monday = day - datetime.timedelta(days=day.weekday())
    return monday - datetime.timedelta(days=7), monday - datetime.timedelta(days=1)


def backfill_sample(everything, week_id, size, db_dir):
    """한꺼번에 채운 지난 소식 가운데 아직 다시 대조하지 않은 것을 size건 고른다. 주마다 다르게, 같은 주에는 늘 같게 뽑는다.

    중요도가 높은 것, 요약이 긴 것(제목만 옮긴 한 줄짜리가 아닌 것)을 먼저 뽑는다.
    db_dir는 데이터베이스의 audits 컬렉션을 받아 둔 폴더다(없으면 모두 대조하지 않은 것으로 본다).
    """
    if size <= 0:
        return []
    done = {str(doc.get("itemId", "")) for doc in dbdump.docs(db_dir, "audits").values()} if db_dir else set()
    left = [item for item in everything if item.get("backfill") and item["id"] not in done and item.get("authoring") == "자동"]
    left.sort(key=lambda item: (item.get("importance") != "높음", len(item.get("summary", "")) < LONG_SUMMARY,
                                hashlib.sha1(f"{week_id}|{item['id']}".encode("utf-8")).hexdigest()))
    return left[:size]


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--audit", type=int, default=5)
    parser.add_argument("--audit-backfill", type=int, default=0)
    parser.add_argument("--db-dir", default="")
    parser.add_argument("--date", default="")
    args = parser.parse_args(argv)
    day = datetime.date.fromisoformat(args.date) if args.date else now_kst().date()
    start, end = last_week(day)
    everything = [item for item in read_json("data/items.json", {"items": []})["items"] if not item.get("withdrawn")]
    items = [item for item in everything
             if start.isoformat() <= str(item.get("listed", "")) <= end.isoformat() and not item.get("backfill")]
    week_id = f"{start.isoformat()}_{end.isoformat()}"
    # 표본은 주마다 달라지되 같은 주에는 늘 같게 뽑는다. 사람이 고친 항목은 빼고, 중요도가 높은 것을 먼저 넣는다.
    auto = [item for item in items if item.get("authoring") == "자동"]
    auto.sort(key=lambda item: (item.get("importance") != "높음", hashlib.sha1(f"{week_id}|{item['id']}".encode("utf-8")).hexdigest()))
    audit = [item["id"] for item in auto[:max(0, args.audit)]]
    older = backfill_sample(everything, week_id, args.audit_backfill, args.db_dir)
    out = pathlib.Path(args.out)
    write_json(out, {"id": week_id, "from": start.isoformat(), "to": end.isoformat(), "items": items, "audit": audit,
                     "auditBackfill": [item["id"] for item in older], "backfillItems": older})
    text = "\n\n".join(f"{item.get('title', '')}\n{item.get('summary', '')}\n{item.get('impact', '')}" for item in items)
    out.with_suffix(".txt").write_text(text + "\n", encoding="utf-8")
    print(f"지난주 {start} ~ {end}: 오른 항목 {len(items)}건, 다시 대조할 표본 {len(audit)}건, 지난 소식 표본 {len(older)}건")
    for item in items:
        mark = "*" if item["id"] in audit else " "
        print(f" {mark} {item['id']} [{item.get('kind')}/{item.get('importance')}] {item.get('title', '')[:70]}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
