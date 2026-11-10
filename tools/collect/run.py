"""출처를 돌며 새 항목을 찾아 collected/ 아래에 적는다.

저장소 맨 위에서 `python -m tools.collect.run`으로 돌린다. 한 출처가 실패해도 나머지는 계속한다.
"""
import sys

from tools.collect import extract, feed, pages, registry, state
from tools.common.htmltext import decode
from tools.common.jsonio import now_kst, read_json, stamp, today, write_json
from tools.common.net import fetch, header, sha256_hex

STATUS_PATH = "collected/status.json"
BULK_LIMIT = 25      # 한 번에 이보다 많이 새로 보이면 화면 구조가 바뀐 것으로 본다
MIN_BODY = 800       # 이보다 작은 본문은 차단 안내나 빈 화면으로 본다


def check_source(source, keywords, moment):
    code = source["code"]
    result = {"code": code, "checkedAt": stamp(moment), "ok": False, "status": 0, "new": 0, "note": ""}
    status, headers, body, error = fetch(source["url"])
    result["status"] = status
    if status != 200 or len(body) < MIN_BODY:
        result["note"] = (error or f"본문 {len(body)}바이트")[:160]
        return result, []

    html = decode(body, header(headers, "Content-Type"))
    if source.get("tier") == "A":
        pages.save_source_text(code, html, source["url"])
    found, counts = extract.entries(source, html, keywords)
    result.update({"ok": True, "bytes": len(body), "pageHash": sha256_hex(body)[:16], "counts": counts, "entries": len(found)})

    previous = state.load(code)
    date = today(moment)
    if previous is None:  # 첫 실행: 기준선만 만든다
        state.save(code, {"code": code, "baseline": date, "checkedAt": stamp(moment), "seen": {entry["key"]: date for entry in found}})
        result["note"] = "기준선 생성"
        return result, []

    seen = previous.get("seen", {})
    fresh = [entry for entry in found if entry["key"] not in seen]
    for entry in fresh:
        seen[entry["key"]] = date
    previous.update({"checkedAt": stamp(moment), "seen": seen})
    state.save(code, previous)

    items = []
    if len(fresh) > BULK_LIMIT:
        result["note"] = f"새 항목 {len(fresh)}건: 화면 구조가 바뀐 것으로 보임"
        items.append({
            "id": feed.item_id(code, f"bulk:{date}"), "source": code, "kind": "bulk", "url": source["url"],
            "text": f"{source['name']}: 새 항목이 {len(fresh)}건 한꺼번에 보임. 화면 구조가 바뀌었는지 확인 필요", "seenAt": stamp(moment),
        })
    else:
        for entry in fresh:
            item = {"id": feed.item_id(code, entry["key"]), "source": code, "kind": entry["kind"], "url": entry["url"], "text": entry["text"], "seenAt": stamp(moment)}
            if "cells" in entry:
                item["cells"] = entry["cells"]
            if source.get("tier") == "A":
                item["textPath"] = pages.save_item_text(item) if entry["kind"] == "link" else pages.source_path(code)
            items.append(item)
    result["new"] = len(items)
    return result, items


def main():
    moment = now_kst()
    sources, keywords = registry.load()
    targets = registry.github_sources(sources)
    status = read_json(STATUS_PATH, {"sources": {}})
    codes = {source["code"] for source in targets}
    status["sources"] = {code: row for code, row in status["sources"].items() if code in codes}  # 대상에서 빠진 출처의 옛 기록은 지운다
    all_items = []
    for source in targets:
        try:
            result, items = check_source(source, keywords, moment)
        except Exception as error:  # 한 출처의 오류가 전체를 멈추지 않게 한다
            result, items = {"code": source["code"], "checkedAt": stamp(moment), "ok": False, "status": 0, "new": 0, "note": f"{type(error).__name__}: {error}"[:160]}, []
        before = status["sources"].get(source["code"], {})
        result["failCount"] = 0 if result["ok"] else int(before.get("failCount", 0)) + 1
        result["lastOk"] = result["checkedAt"] if result["ok"] else before.get("lastOk", "")
        status["sources"][source["code"]] = result
        all_items.extend(items)
        print(f"{source['code']:22} {result['status']:>3} new={result['new']:<3} {result.get('note', '')}")
    added = feed.append(today(moment), all_items, stamp(moment)) if all_items else 0
    status["checkedAt"] = stamp(moment)
    status["newItems"] = added
    write_json(STATUS_PATH, status)
    print(f"출처 {len(targets)}곳, 새 항목 {added}건")
    return 0


if __name__ == "__main__":
    sys.exit(main())
