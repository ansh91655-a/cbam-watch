"""영국 정부(GOV.UK)의 CBAM 자료 모음에서 문서별 게시일과 갱신 기록을 모은다. GOV.UK의 내용 자료(JSON)를 읽는다."""
import json
import time

from tools.archive.store import SINCE, save_index, save_text
from tools.common.net import fetch

API = "https://www.gov.uk/api/content{path}"
COLLECTION = "/government/collections/carbon-border-adjustment-mechanism"


def _read(path):
    status, _, body, error = fetch(API.format(path=path), headers={"Accept": "application/json"})
    time.sleep(0.8)
    if status != 200 or not body:
        return None, f"{status} {error[:60]}"
    try:
        return json.loads(body.decode("utf-8", "replace")), ""
    except Exception:
        return None, "자료를 풀지 못함"


def _changes(document, path):
    rows = []
    title = document.get("title", "")
    first = str(document.get("first_published_at") or "")[:10]
    for change in (document.get("details") or {}).get("change_history") or []:
        date = str(change.get("public_timestamp") or "")[:10]
        if date:
            rows.append({"date": date, "title": title, "note": " ".join(str(change.get("note") or "").split()), "url": f"https://www.gov.uk{path}",
                         "type": document.get("document_type", ""), "firstPublished": first})
    if first and not any(row["date"] == first for row in rows):
        rows.append({"date": first, "title": title, "note": "First published.", "url": f"https://www.gov.uk{path}", "type": document.get("document_type", ""), "firstPublished": first})
    return rows


def crawl():
    collection, error = _read(COLLECTION)
    if collection is None:
        save_index("uk-govuk", [], {"error": error})
        return {"error": error}
    entries, failures = _changes(collection, COLLECTION), []
    paths = [row.get("base_path") for row in (collection.get("links") or {}).get("documents") or [] if row.get("base_path")]
    for path in paths:
        document, error = _read(path)
        if document is None:
            failures.append(f"{path} ({error})")
            continue
        entries += _changes(document, path)
    kept = sorted((entry for entry in entries if entry["date"] >= SINCE), key=lambda entry: (entry["date"], entry["url"]), reverse=True)
    lines = ["[주소] https://www.gov.uk" + COLLECTION, ""] + [f"{entry['date']} | {entry['title']} | {entry['note']} | {entry['url']}" for entry in kept]
    path = save_text("uk-govuk/changes.txt", lines)
    for entry in kept:
        entry["textPath"] = path
    save_index("uk-govuk", kept, {"documents": len(paths), "changes": len(entries), "failures": failures})
    return {"documents": len(paths), "kept": len(kept), "failures": len(failures)}
