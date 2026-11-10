"""그날 새로 보인 항목을 한 파일에 모은다. 같은 날 여러 번 돌려도 겹치지 않는다."""
import hashlib

from tools.common.jsonio import read_json, write_json

FEED_DIR = "collected/feed"


def item_id(source_code, key):
    return hashlib.sha1(f"{source_code}|{key}".encode("utf-8")).hexdigest()[:12]


def append(date, new_items, generated_at):
    path = f"{FEED_DIR}/{date}.json"
    feed = read_json(path, {"date": date, "items": []})
    known = {item["id"] for item in feed["items"]}
    added = 0
    for item in new_items:
        if item["id"] not in known:
            feed["items"].append(item)
            known.add(item["id"])
            added += 1
    feed["generatedAt"] = generated_at
    feed["count"] = len(feed["items"])
    write_json(path, feed)
    return added
