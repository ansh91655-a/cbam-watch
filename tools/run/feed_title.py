"""제목만 옮겨 쓴 초안의 원문 제목을 저장소의 수집 기록에서 찾는다.

등급 C 출처의 소식과, 본문을 읽지 못해 제목만 옮긴 소식(brief)은 원문 화면을 열지 않고 검증한다.
수집 프로그램이 출처 화면에서 읽은 제목과 주소가 collected/feed/<날짜>.json 에 남아 있으므로,
초안이 가리키는 후보(candidateIds)를 그 기록에서 찾아 원문 제목과 주소를 돌려준다.
초안을 쓴 실행이 옮겨 적은 값이 아니라 수집 프로그램이 적은 값과 견주게 하려는 것이다.

쓰는 법: python -m tools.run.feed_title --item-file /tmp/run/db/items/<항목 id>.json [--days 30]
마지막 줄에 JSON으로 출력한다.
- found: 후보를 수집 기록에서 찾았는가
- linkMatches: 초안의 link가 기록의 주소(또는 그 출처 화면의 주소)와 글자 그대로 같은가
- entries: 찾은 기록들(id, source, kind, text, url, feedDate). text가 출처 화면에 적혀 있던 원문 제목이다
"""
import argparse
import datetime
import json
import pathlib
import sys

from tools.collect.feed import FEED_DIR
from tools.common.jsonio import now_kst, read_json

REGISTRY = "sources/registry.json"


def _feed_files(days, today):
    """최근 days일의 수집 기록 파일을 새것부터."""
    oldest = (today - datetime.timedelta(days=days)).isoformat()
    names = sorted((path for path in pathlib.Path(FEED_DIR).glob("*.json") if path.stem >= oldest), reverse=True)
    return names


def lookup(item, days=30, today=None):
    """초안의 후보를 수집 기록에서 찾아 {"found", "linkMatches", "entries"}를 돌려준다."""
    today = today or now_kst().date()
    wanted = {str(value) for value in item.get("candidateIds", []) or [] if value}
    entries = []
    for path in _feed_files(days, today):
        for row in (read_json(path, {}) or {}).get("items", []):
            if row.get("id") in wanted and row["id"] not in {entry["id"] for entry in entries}:
                entries.append({"id": row["id"], "source": row.get("source", ""), "kind": row.get("kind", ""),
                                "text": row.get("text", ""), "url": row.get("url", ""), "feedDate": path.stem})
    pages = {source["code"]: source.get("url", "") for source in read_json(REGISTRY, {"sources": []}).get("sources", [])}
    allowed = {entry["url"] for entry in entries} | {pages.get(entry["source"], "") for entry in entries}
    link = str(item.get("link", "")).strip()
    return {"found": bool(entries), "linkMatches": bool(link) and link in allowed, "entries": entries}


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("--item-file", required=True)
    parser.add_argument("--days", type=int, default=30)
    args = parser.parse_args(argv)
    item = read_json(args.item_file, None)
    if not isinstance(item, dict):
        print(json.dumps({"found": False, "linkMatches": False, "entries": [], "error": "초안 파일을 읽지 못함"}, ensure_ascii=False))
        return 1
    print(json.dumps(lookup(item, args.days), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
