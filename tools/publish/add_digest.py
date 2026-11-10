"""주간 요약을 게시 데이터(data/digests.json)에 더한다. 같은 주의 요약이 이미 있으면 바꾼다.

쓰는 법: python -m tools.publish.add_digest --file /tmp/run/digest.json
파일의 꼴: {"from": "2026-11-09", "to": "2026-11-15", "title": "", "paragraphs": ["", ""], "itemIds": ["..."]}
형식이 맞지 않으면 아무것도 바꾸지 않고 사유를 출력한다. 마지막 줄은 결과 JSON이다.
"""
import argparse
import json
import re
import sys

from tools.common.jsonio import read_json, stamp, write_json

DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
PATH = "data/digests.json"


def problems_of(digest, known_ids):
    found = []
    if not DATE.match(str(digest.get("from", ""))) or not DATE.match(str(digest.get("to", ""))) or digest["from"] > digest["to"]:
        found.append("기간")
    title = str(digest.get("title", "")).strip()
    if not title or len(title) > 80:
        found.append("제목(80자 이내)")
    paragraphs = digest.get("paragraphs")
    if not isinstance(paragraphs, list) or not 1 <= len(paragraphs) <= 5 or any(not str(text).strip() or len(str(text)) > 400 for text in paragraphs):
        found.append("문단(1~5개, 각 400자 이내)")
    unknown = [item_id for item_id in digest.get("itemIds", []) if item_id not in known_ids]
    if unknown:
        found.append(f"게시되지 않은 항목: {', '.join(unknown[:3])}")
    return found


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True)
    args = parser.parse_args(argv)
    digest = read_json(args.file, None)
    known_ids = {item["id"] for item in read_json("data/items.json", {"items": []})["items"]}
    found = ["파일을 읽지 못함"] if not isinstance(digest, dict) else problems_of(digest, known_ids)
    if found:
        print(json.dumps({"added": False, "problems": found}, ensure_ascii=False))
        return 1
    row = {"id": f"{digest['from']}_{digest['to']}", "from": digest["from"], "to": digest["to"], "title": digest["title"].strip(),
           "paragraphs": [str(text).strip() for text in digest["paragraphs"]], "itemIds": list(digest.get("itemIds", [])), "writtenAt": stamp(), "authoring": "자동"}
    data = read_json(PATH, {"digests": []})
    data["digests"] = [old for old in data.get("digests", []) if old.get("id") != row["id"]] + [row]
    data["digests"].sort(key=lambda item: item["to"])
    write_json(PATH, data)
    print(json.dumps({"added": True, "id": row["id"], "total": len(data["digests"])}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
