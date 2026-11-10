"""EC가 올린 원문 문서를 받아 판을 관리한다.

저장소 맨 위에서 `python -m tools.originals.run`으로 돌린다. `--full`을 주면 모든 문서를 다시 받아 해시를 비교한다.
평소에는 새로 보인 문서만 받고, 월요일(한국 시각)에는 전체를 다시 받는다.

문서를 찾아볼 화면은 출처 대장(sources/registry.json)에서 documents가 참인 곳이다.
화면을 처음 보는 날에는 그 화면의 문서를 소식 없이 기준선으로만 등록한다.
"""
import sys
import time

from tools.collect import feed, registry
from tools.common.jsonio import now_kst, read_json, stamp, today, write_json
from tools.common.net import fetch, sha256_hex
from tools.originals import discover, naming, versions

STATE_PATH = "originals/state.json"
MAX_BYTES = 60 * 1024 * 1024
SOURCE_CODE = "ec-documents"


def _pages():
    sources, _ = registry.load()
    return [(source["code"], source["url"]) for source in sources if source.get("documents") and source.get("collector") == "github"]


def _item(doc_id, key, change, text, url, moment, **extra):
    item = {"id": feed.item_id(SOURCE_CODE, f"{doc_id}:{key}"), "source": SOURCE_CODE, "kind": "document", "change": change, "doc": doc_id,
            "url": url, "text": text, "seenAt": stamp(moment)}
    item.update(extra)
    return item


def _check_known(doc, info, filename, body, moment):
    """이미 아는 문서를 다시 받았을 때. 본문이 바뀐 새 판이면 소식 항목을, 아니면 None을 돌려준다."""
    doc.update({"linked": True, "lastSeen": today(moment), "lastChecked": stamp(moment), "url": info["url"], "label": info["label"], "filename": filename})
    latest = doc["versions"][-1]
    digest = sha256_hex(body)
    if versions.known_hash(latest, digest):
        return None
    version = versions.store(doc, body, moment)
    result = versions.compare(latest, version)
    if versions.unchanged(result):  # 파일은 달라졌으나 본문은 같다: 새 판으로 치지 않는다
        versions.discard(version)
        versions.remember_same_text(latest, digest)
        return None
    diff_path, stats = versions.write_diff(doc["id"], latest, version, result) if result else ("", None)
    version["diff"] = diff_path
    doc["versions"].append(version)
    return _item(doc["id"], digest[:12], "new-version", f"문서의 새 판: {filename}", info["url"], moment, diff=diff_path, stats=stats, textPath=version["text"])


def _add_new(docs, families, info, filename, body, moment):
    """처음 보는 문서를 등록하고 소식 항목을 돌려준다. 이름이 같은 계열의 옛 문서가 있으면 그것과 비교한다."""
    doc_id = info["id"]
    doc = {"id": doc_id, "filename": filename, "label": info["label"], "url": info["url"], "lang": info["lang"], "page": info["page"],
           "firstSeen": today(moment), "lastSeen": today(moment), "lastChecked": stamp(moment), "linked": True, "versions": [], "replaces": ""}
    version = versions.store(doc, body, moment)
    doc["versions"].append(version)
    item = _item(doc_id, "new", "new-document", f"새 문서: {filename}", info["url"], moment, textPath=version["text"])
    old_id = families.get(discover.family(filename))
    if old_id and old_id != doc_id and docs.get(old_id, {}).get("versions"):
        doc["replaces"] = old_id
        old_version = docs[old_id]["versions"][-1]
        result = versions.compare(old_version, version)
        diff_path, stats = versions.write_diff(doc_id, old_version, version, result) if result else ("", None)
        version["diff"] = diff_path
        item.update({"change": "replaced-document", "replaces": old_id, "diff": diff_path, "stats": stats, "text": f"문서가 새 파일로 바뀜: {filename}"})
    docs[doc_id] = doc
    return item


def main(argv):
    moment = now_kst()
    full = "--full" in argv or moment.weekday() == 0
    state = read_json(STATE_PATH, {"docs": {}, "baseline": "", "pages": {}})
    docs = state["docs"]
    known_pages = state.setdefault("pages", {})
    first_run = not docs
    found, notes, read_codes = discover.scan(_pages())
    if not found:
        state.update({"checkedAt": stamp(moment), "notes": notes + ["문서 링크를 하나도 찾지 못해 아무것도 바꾸지 않음"]})
        write_json(STATE_PATH, state)
        print("문서 링크 없음:", notes)
        return 0

    new_pages = {code for code in read_codes if code not in known_pages}
    families = {discover.family(doc["filename"]): doc_id for doc_id, doc in docs.items() if not doc.get("linked", True) or doc_id not in found}
    items = []
    for doc_id, info in found.items():
        known = docs.get(doc_id)
        if known and not full:
            known.update({"linked": True, "lastSeen": today(moment), "url": info["url"], "label": info["label"]})
            continue
        status, headers, body, error = fetch(info["url"], timeout=180)
        time.sleep(1)
        if status != 200 or not body or len(body) > MAX_BYTES:
            notes.append(f"{info['filename'] or doc_id[:8]}: 받지 못함({status} {error[:60]}, {len(body)}바이트)")
            if known:
                known.update({"linked": True, "lastSeen": today(moment)})
            continue
        filename = naming.choose(info["filename"], headers, doc_id)
        if known:
            item = _check_known(known, info, filename, body, moment)
        else:
            item = _add_new(docs, families, info, filename, body, moment)
            if first_run or info["page"] in new_pages:
                item = None  # 기준선: 원래 있던 문서이므로 소식으로 내지 않는다
        if item:
            items.append(item)

    for doc_id, doc in docs.items():
        if doc_id not in found and doc.get("linked", True) and doc.get("page") in read_codes:
            doc["linked"] = False
            doc["unlinkedAt"] = today(moment)
            if not first_run:
                items.append(_item(doc_id, "unlinked", "unlinked", f"문서 링크가 화면에서 사라짐: {doc['filename']}", doc.get("url", ""), moment))

    for code in read_codes:
        known_pages.setdefault(code, today(moment))
    if first_run:
        state["baseline"] = today(moment)
    state.update({"checkedAt": stamp(moment), "full": full, "notes": notes, "docCount": len(docs)})
    write_json(STATE_PATH, state)
    added = feed.append(today(moment), items, stamp(moment)) if items else 0
    print(f"문서 {len(found)}건 확인(전체 다시 받기: {full}), 새 소식 {added}건, 특이사항 {len(notes)}건")
    for note in notes:
        print("  ", note)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
