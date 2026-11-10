"""주간 작업이 다룰 지난주의 게시 항목을 고른다.

지난주는 오늘이 속한 주의 바로 앞 주(월요일부터 일요일, 한국 시각)다.
쓰는 법: python -m tools.run.week_items --out /tmp/run/week.json [--audit 5] [--date 2026-11-16]
- week.json: 기간, 그 주에 이 사이트에 오른 항목, 다시 대조할 표본(audit)
- 같은 폴더의 week.txt: 그 항목들의 제목과 요약을 이어 붙인 글. 주간 요약의 수치와 날짜를 대조하는 데 쓴다.
"""
import argparse
import datetime
import hashlib
import pathlib
import sys

from tools.common.jsonio import now_kst, read_json, write_json


def last_week(day):
    """그 날짜가 속한 주의 바로 앞 주의 (월요일, 일요일)."""
    monday = day - datetime.timedelta(days=day.weekday())
    return monday - datetime.timedelta(days=7), monday - datetime.timedelta(days=1)


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--audit", type=int, default=5)
    parser.add_argument("--date", default="")
    args = parser.parse_args(argv)
    day = datetime.date.fromisoformat(args.date) if args.date else now_kst().date()
    start, end = last_week(day)
    items = [item for item in read_json("data/items.json", {"items": []})["items"]
             if start.isoformat() <= str(item.get("listed", "")) <= end.isoformat() and not item.get("withdrawn")]
    week_id = f"{start.isoformat()}_{end.isoformat()}"
    # 표본은 주마다 달라지되 같은 주에는 늘 같게 뽑는다. 사람이 고친 항목은 빼고, 중요도가 높은 것을 먼저 넣는다.
    auto = [item for item in items if item.get("authoring") == "자동"]
    auto.sort(key=lambda item: (item.get("importance") != "높음", hashlib.sha1(f"{week_id}|{item['id']}".encode("utf-8")).hexdigest()))
    audit = [item["id"] for item in auto[:max(0, args.audit)]]
    out = pathlib.Path(args.out)
    write_json(out, {"id": week_id, "from": start.isoformat(), "to": end.isoformat(), "items": items, "audit": audit})
    text = "\n\n".join(f"{item.get('title', '')}\n{item.get('summary', '')}\n{item.get('impact', '')}" for item in items)
    out.with_suffix(".txt").write_text(text + "\n", encoding="utf-8")
    print(f"지난주 {start} ~ {end}: 오른 항목 {len(items)}건, 다시 대조할 표본 {len(audit)}건")
    for item in items:
        mark = "*" if item["id"] in audit else " "
        print(f" {mark} {item['id']} [{item.get('kind')}/{item.get('importance')}] {item.get('title', '')[:70]}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
