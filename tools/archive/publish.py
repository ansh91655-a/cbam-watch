"""소급 항목을 게시 데이터(data/items.json)에 더한다.

쓰는 법: python -m tools.archive.publish --drafts <초안 파일> [--dry-run]
- 초안 파일은 {"items": [...]} 꼴이다. 항목마다 원문 글의 자리를 적는다.
    sourceTextPath: 저장소에 받아 둔 원문 글 파일(collected/archive/pages/...)
    sourceEntry:    {"index": "kr-keco-cbam", "url": "..."} 처럼 목록 파일(collected/archive/<index>.json)의 한 줄.
                    글 본문을 받아 두지 않는 출처에 쓴다. 이때는 그 줄의 제목·날짜·주소가 대조할 원문이다.
- 검사(tools.archive.gate)에 걸린 항목은 싣지 않고 사유를 알려 준다. 이미 실린 id나 링크와 겹치는 항목도 싣지 않는다.
- 실린 항목에는 backfill 표시가 붙는다. 주간 요약은 이 표시가 있는 항목을 지난주의 새 소식으로 세지 않는다.
마지막 줄에 결과를 JSON으로 출력한다.
"""
import argparse
import json
import pathlib
import sys

from tools.archive import gate
from tools.archive.store import ROOT
from tools.check import term_check
from tools.common.jsonio import read_json, stamp, today, write_json
from tools.publish import topics
from tools.publish.add_items import PUBLIC_FIELDS


def source_text(item):
    """항목이 가리키는 원문 글. 없으면 None."""
    raw = str(item.get("sourceTextPath", "")).strip()
    if raw:
        path = pathlib.Path(raw)
        inside = not raw.startswith("/") and ".." not in raw
        return path.read_text(encoding="utf-8", errors="replace") if inside and path.is_file() else None
    entry = item.get("sourceEntry") or {}
    index = read_json(ROOT / f"{entry.get('index', '')}.json", {"entries": []})
    for row in index["entries"]:
        if row.get("url") and row.get("url") == entry.get("url"):
            return "\n".join(str(value) for value in row.values() if isinstance(value, (str, int, float)))
    return None


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("--drafts", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    drafts = read_json(args.drafts, {"items": []})["items"]
    data = read_json("data/items.json", {"items": []})
    known_ids = {item["id"] for item in data["items"]}
    known_links = {item["link"] for item in data["items"] if item.get("link")}
    term_index = term_check.load()
    known_topics = topics.codes()

    added, rejected, skipped, without_excerpt = [], [], [], []
    for item in drafts:
        item_id = str(item.get("id", ""))
        if item_id in known_ids or (item.get("link") in known_links and not item.get("sharedLink")):
            skipped.append(item_id)
            continue
        source = source_text(item)
        found = gate.problems(item, source, term_index, known_topics)
        if found:
            rejected.append({"id": item_id, "problems": found})
            continue
        row = {field: item[field] for field in PUBLIC_FIELDS if field in item and item[field] not in (None, "")}
        row.setdefault("impact", "")
        excerpt = gate.excerpt_of(item, source)
        if excerpt:
            row["excerpt"] = excerpt
        elif str(item.get("excerpt", "")).strip():
            without_excerpt.append(item_id)
        row.update({"listed": today(), "checkedAt": stamp(), "authoring": "자동", "backfill": True})
        data["items"].append(row)
        known_ids.add(item_id)
        if not item.get("sharedLink"):
            known_links.add(item.get("link"))
        added.append(item_id)
    if added and not args.dry_run:
        data["builtAt"] = stamp()
        write_json("data/items.json", data)
    print(json.dumps({"added": len(added), "rejected": rejected, "skipped": skipped, "withoutExcerpt": without_excerpt,
                      "total": len(data["items"]), "dryRun": args.dry_run}, ensure_ascii=False))
    return 1 if rejected else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
