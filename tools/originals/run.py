"""EC가 올린 원문 문서를 받아 판을 관리한다.

저장소 맨 위에서 `python -m tools.originals.run`으로 돌린다. `--full`을 주면 건수 제한 없이 모든 문서를 다시 받는다.

- 문서를 찾아볼 화면은 출처 대장(sources/registry.json)에서 documents가 참인 곳이다.
- 화면을 처음 보는 날에는 그 화면의 문서를 소식 없이 기준선으로만 등록한다.
- 한 번에 받는 건수가 정해져 있다(tools/originals/queue.py). 처음 보는 문서를 먼저 받고,
  남는 몫으로 가장 오래 확인하지 않은 문서부터 다시 받아 바뀌었는지 본다.
"""
import sys
import time

from tools.collect import feed, registry
from tools.common.jsonio import now_kst, read_json, stamp, today, write_json
from tools.common.net import fetch, sha256_hex
from tools.originals import discover, naming, queue, versions

STATE_PATH = "originals/state.json"
MAX_BYTES = 60 * 1024 * 1024
SOURCE_CODE = "ec-documents"
PAUSE = 3          # 문서 사이에 쉬는 초
BLOCK_LIMIT = 2    # 받지 못한 응답이 이만큼 이어지면 접속 제한으로 보고 이번 실행에서는 그만 받는다


def _sources():
    sources, _ = registry.load()
    return [source for source in sources if source.get("documents") and source.get("collector") == "github"]


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


def _download(order, found, docs, pending, families, moment, notes):
    """차례대로 문서를 받아 등록하거나 판을 견준다. 소식 항목의 목록을 돌려준다."""
    items, blocked, done = [], 0, 0
    for doc_id in order:
        info = found[doc_id]
        if done:
            time.sleep(PAUSE)
        done += 1
        status, headers, body, error = fetch(info["url"], timeout=180, retries=0)
        if status != 200 or not body or len(body) > MAX_BYTES:
            blocked += 1
            reason = f"{status} {error[:60]}".strip() if status != 200 else f"크기 {len(body)}바이트"
            if doc_id in pending:
                pending[doc_id].update({"tries": pending[doc_id]["tries"] + 1, "lastError": reason, "lastTried": stamp(moment)})
            else:  # 확인 시각을 적어 다음 실행에서는 다른 문서가 먼저 오게 한다
                docs[doc_id].update({"lastError": reason, "lastChecked": stamp(moment)})
            if blocked >= BLOCK_LIMIT:
                notes.append(f"받지 못한 응답이 {blocked}번 이어져 이번 실행에서는 그만 받음(남은 {len(order) - done}건은 다음 실행에서)")
                break
            continue
        blocked = 0
        filename = naming.choose(info["filename"], headers, doc_id)
        if doc_id in pending:
            item = _add_new(docs, families, info, filename, body, moment)
            if pending.pop(doc_id).get("quiet"):
                item = None  # 기준선: 원래 있던 문서이므로 소식으로 내지 않는다
        else:
            docs[doc_id].pop("lastError", None)
            item = _check_known(docs[doc_id], info, filename, body, moment)
        if item:
            items.append(item)
    return items


def main(argv):
    moment = now_kst()
    full = "--full" in argv
    state = read_json(STATE_PATH, {"docs": {}, "baseline": "", "pages": {}, "pending": {}})
    docs = state["docs"]
    known_pages = state.setdefault("pages", {})
    pending = state.setdefault("pending", {})
    first_run = not docs and not pending
    found, notes, read_codes = discover.scan(_sources())
    if not found:
        state.update({"checkedAt": stamp(moment), "notes": notes + ["문서 링크를 하나도 찾지 못해 아무것도 바꾸지 않음"]})
        write_json(STATE_PATH, state)
        print("문서 링크 없음:", notes)
        return 0

    for doc_id, info in found.items():
        if doc_id in docs:
            docs[doc_id].update({"linked": True, "lastSeen": today(moment), "url": info["url"], "label": info["label"]})
    new_pages = {code for code in read_codes if code not in known_pages}
    queue.note_new_links(pending, found, docs, new_pages, first_run, today(moment))
    queue.drop_vanished(pending, found, read_codes)
    families = {discover.family(doc["filename"]): doc_id for doc_id, doc in docs.items() if not doc.get("linked", True) or doc_id not in found}
    order = queue.build(found, docs, pending, full, moment.weekday() == 0)
    items = _download(order, found, docs, pending, families, moment, notes)

    for doc_id, doc in docs.items():
        if doc_id not in found and doc.get("linked", True) and doc.get("page") in read_codes:
            doc["linked"] = False
            doc["unlinkedAt"] = today(moment)
            items.append(_item(doc_id, "unlinked", "unlinked", f"문서 링크가 화면에서 사라짐: {doc['filename']}", doc.get("url", ""), moment))

    for code in read_codes:
        known_pages.setdefault(code, today(moment))
    if first_run:
        state["baseline"] = today(moment)
    waiting = len(pending)
    stuck = [doc_id[:8] for doc_id, entry in pending.items() if entry["tries"] >= queue.GIVE_UP]
    if stuck:
        notes.append(f"여러 번 받지 못한 문서 {len(stuck)}건: {', '.join(stuck[:6])}")
    state.update({"checkedAt": stamp(moment), "full": full, "notes": notes, "docCount": len(docs), "pendingCount": waiting, "checkedThisRun": len(order)})
    write_json(STATE_PATH, state)
    added = feed.append(today(moment), items, stamp(moment)) if items else 0
    print(f"문서 링크 {len(found)}건, 이번에 받은 차례 {len(order)}건, 아직 받지 못한 문서 {waiting}건, 새 소식 {added}건, 특이사항 {len(notes)}건")
    for note in notes:
        print("  ", note)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
