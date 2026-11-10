"""검증을 통과한 항목을 게시 데이터(data/items.json, data/events.json)에 더한다.

데이터베이스에서 받아 둔 items와 verdicts를 읽어, 판정이 pass이고 아직 게시되지 않은 항목만 더한다.
쓰는 법: python -m tools.publish.add_items --db-dir /tmp/run/db
형식이 맞지 않는 항목은 더하지 않고 사유를 출력한다. 마지막 줄에 더한 건수를 JSON으로 출력한다.
"""
import argparse
import json
import re
import sys

from tools.common.jsonio import read_json, stamp, today, write_json
from tools.run import dbdump

KINDS = {"법령", "가이던스", "가격", "입법", "제도 안내", "국내", "해외", "행사", "원문 변경", "소식"}
LEVELS = {"높음", "보통", "낮음"}
ID = re.compile(r"^[a-z0-9][a-z0-9-]{5,79}$")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
PUBLIC_FIELDS = ["id", "published", "title", "summary", "impact", "kind", "importance", "topics", "sourceCode", "sourceName", "link", "price"]


def problems_of(item):
    found = []
    if not ID.match(str(item.get("id", ""))):
        found.append("id 형식")
    if not str(item.get("title", "")).strip() or len(item["title"]) > 120:
        found.append("제목")
    if not str(item.get("summary", "")).strip() or len(item["summary"]) > 900:
        found.append("요약")
    if item.get("kind") not in KINDS:
        found.append("종류")
    if item.get("importance") not in LEVELS:
        found.append("중요도")
    if not str(item.get("link", "")).startswith("https://"):
        found.append("링크")
    if item.get("published") and not DATE.match(str(item["published"])):
        found.append("게시일 형식")
    return found


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("--db-dir", required=True)
    args = parser.parse_args(argv)
    items = dbdump.docs(args.db_dir, "items")
    verdicts = dbdump.docs(args.db_dir, "verdicts")
    data = read_json("data/items.json", {"items": []})
    published = {item["id"] for item in data["items"]}
    events = read_json("data/events.json", {"events": []})
    event_keys = {(event["date"], event["title"]) for event in events["events"]}

    added, rejected = [], []
    for item_id, verdict in sorted(verdicts.items()):
        item = items.get(item_id)
        if verdict.get("result") != "pass" or item is None or item_id in published:
            continue
        found = problems_of(item)
        if found:
            rejected.append({"id": item_id, "problems": found})
            continue
        row = {field: item[field] for field in PUBLIC_FIELDS if field in item and item[field] not in (None, "")}
        row.setdefault("published", "")
        row.setdefault("impact", "")
        row.update({"listed": today(), "checkedAt": verdict.get("at", stamp()), "authoring": "자동"})
        data["items"].append(row)
        added.append(item_id)
        for event in item.get("events", []) or []:
            key = (str(event.get("date", "")), str(event.get("title", "")))
            if DATE.match(key[0]) and key[1] and key not in event_keys:
                events["events"].append({"date": key[0], "title": key[1], "note": str(event.get("note", "")), "sourceName": item.get("sourceName", ""), "link": item.get("link", "")})
                event_keys.add(key)
    if added:
        data["builtAt"] = stamp()
        write_json("data/items.json", data)
        write_json("data/events.json", events)
    print(json.dumps({"added": added, "rejected": rejected, "total": len(data["items"])}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
