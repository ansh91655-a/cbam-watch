"""검증을 통과한 항목을 게시 데이터(data/items.json, data/events.json)에 더한다.

데이터베이스에서 받아 둔 items와 verdicts를 읽어, 판정이 pass이고 아직 게시되지 않은 항목만 더한다.
쓰는 법: python -m tools.publish.add_items --db-dir /tmp/run/db

판정과 별도로 이 프로그램이 한 번 더 막는 것
- 형식: id, 제목, 요약, 종류, 중요도, 링크, 게시일의 꼴
- 사실: 저장소에 원문 글(sourceTextPath)이 있으면, 제목·요약·실무 영향에 나온 수치와 날짜가 그 글에 있어야 한다.
  검증 실행이 표기 차이라고 사유(factNote)를 적은 경우에만 넘어간다.
원문 발췌(excerpt)는 EU 공식 출처(등급 A)이고 원문 글에 그대로 있을 때만 싣는다. 아니면 발췌만 빼고 싣는다.
마지막 줄에 결과를 JSON으로 출력한다.
"""
import argparse
import json
import pathlib
import re
import sys

from tools.check import excerpt_check, fact_check
from tools.common.jsonio import read_json, stamp, today, write_json
from tools.run import dbdump

KINDS = {"법령", "가이던스", "가격", "입법", "제도 안내", "국내", "해외", "행사", "원문 변경", "소식"}
LEVELS = {"높음", "보통", "낮음"}
ID = re.compile(r"^[a-z0-9][a-z0-9-]{5,79}$")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
PUBLIC_FIELDS = ["id", "published", "title", "summary", "impact", "kind", "importance", "topics", "sourceCode", "sourceName", "link", "price"]


def format_problems(item):
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


def _source_text(item):
    """저장소 안의 원문 글. 경로가 저장소 밖을 가리키거나 파일이 없으면 None."""
    raw = str(item.get("sourceTextPath", "")).strip()
    if not raw or raw.startswith("/") or ".." in raw:
        return None
    path = pathlib.Path(raw)
    return path.read_text(encoding="utf-8", errors="replace") if path.is_file() else None


def fact_problems(item, verdict, source):
    """원문 글이 있을 때 수치와 날짜를 대조한다. 어긋나면 사유를, 아니면 빈 목록을 돌려준다."""
    if source is None or str(verdict.get("factNote", "")).strip():
        return []
    text = "\n".join(str(item.get(field, "")) for field in ("title", "summary", "impact"))
    result = fact_check.check(text, source)
    if result["ok"]:
        return []
    return ["사실 대조: 원문에서 찾지 못함 " + ", ".join(result["missingDates"] + result["missingNumbers"])[:80]]


def checked_excerpt(item, source):
    """실어도 되는 발췌면 그 글을, 아니면 빈 글을 돌려준다."""
    excerpt = str(item.get("excerpt", "")).strip()
    if not excerpt or item.get("tier") != "A" or source is None:
        return ""
    return excerpt if excerpt_check.check(excerpt, source)["ok"] else ""


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

    added, rejected, without_excerpt, with_note = [], [], [], []
    for item_id, verdict in sorted(verdicts.items()):
        item = items.get(item_id)
        if verdict.get("result") != "pass" or item is None or item_id in published:
            continue
        source = _source_text(item)
        found = format_problems(item) or fact_problems(item, verdict, source)
        if found:
            rejected.append({"id": item_id, "problems": found})
            continue
        row = {field: item[field] for field in PUBLIC_FIELDS if field in item and item[field] not in (None, "")}
        row.setdefault("published", "")
        row.setdefault("impact", "")
        excerpt = checked_excerpt(item, source)
        if excerpt:
            row["excerpt"] = excerpt
        elif str(item.get("excerpt", "")).strip():
            without_excerpt.append(item_id)
        row.update({"listed": today(), "checkedAt": verdict.get("at", stamp()), "authoring": "자동"})
        data["items"].append(row)
        added.append(item_id)
        if str(verdict.get("factNote", "")).strip():
            with_note.append(item_id)
        for event in item.get("events", []) or []:
            key = (str(event.get("date", "")), str(event.get("title", "")))
            if DATE.match(key[0]) and key[1] and key not in event_keys:
                events["events"].append({"date": key[0], "title": key[1], "note": str(event.get("note", "")), "sourceName": item.get("sourceName", ""), "link": item.get("link", "")})
                event_keys.add(key)
    if added:
        data["builtAt"] = stamp()
        write_json("data/items.json", data)
        write_json("data/events.json", events)
    print(json.dumps({"added": added, "rejected": rejected, "withoutExcerpt": without_excerpt, "withFactNote": with_note, "total": len(data["items"])}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
