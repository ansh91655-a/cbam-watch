"""EC가 올린 원문 문서를 받아 판을 관리한다.

저장소 맨 위에서 `python -m tools.originals.run`으로 돌린다. `--full`을 주면 모든 문서를 다시 받아 해시를 비교한다.
평소에는 새로 보인 문서만 받고, 월요일(한국 시각)에는 전체를 다시 받는다.
"""
import pathlib
import sys
import time

from tools.collect import feed
from tools.common.htmltext import decode
from tools.common.jsonio import now_kst, read_json, stamp, today, write_json
from tools.common.net import fetch, header, sha256_hex
from tools.originals import diff, discover, textify

STATE_PATH = "originals/state.json"
PAGES = [
    ("ec-guidance", "https://taxation-customs.ec.europa.eu/carbon-border-adjustment-mechanism/cbam-legislation-and-guidance_en"),
    ("ec-verification", "https://taxation-customs.ec.europa.eu/carbon-border-adjustment-mechanism/cbam-verification_en"),
]
MAX_BYTES = 60 * 1024 * 1024
SOURCE_CODE = "ec-documents"


def _suffix(filename):
    return ("." + filename.rsplit(".", 1)[-1].lower()) if "." in filename else ".bin"


def _store_version(doc, body, moment):
    """새 판을 파일로 남기고 판 정보를 돌려준다."""
    digest = sha256_hex(body)
    short = digest[:12]
    file_path = pathlib.Path(f"originals/files/{doc['id']}/{short}{_suffix(doc['filename'])}")
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_bytes(body)
    text, pages = textify.extract(file_path)
    version = {"sha256": digest, "date": today(moment), "bytes": len(body), "pages": pages, "file": str(file_path), "text": "", "chars": 0}
    if text is not None:
        text_path = pathlib.Path(f"originals/text/{doc['id']}/{short}.txt")
        text_path.parent.mkdir(parents=True, exist_ok=True)
        text_path.write_text(text, encoding="utf-8")
        version.update({"text": str(text_path), "chars": len(text)})
    return version


def _read_text(version):
    if not version or not version.get("text"):
        return None
    path = pathlib.Path(version["text"])
    return path.read_text(encoding="utf-8") if path.exists() else None


def _write_diff(doc_id, old_version, new_version):
    """두 판의 본문이 다 있으면 비교 결과를 파일로 남기고 (경로, 건수)를 돌려준다."""
    old_text, new_text = _read_text(old_version), _read_text(new_version)
    if old_text is None or new_text is None:
        return "", None
    result = diff.compare(old_text, new_text)
    result.update({"doc": doc_id, "from": old_version["sha256"][:12], "to": new_version["sha256"][:12], "fromDate": old_version["date"], "toDate": new_version["date"]})
    path = f"originals/diffs/{doc_id}/{old_version['sha256'][:12]}-{new_version['sha256'][:12]}.json"
    write_json(path, result)
    return path, result["stats"]


def _discover(moment):
    found, page_notes = {}, []
    for code, url in PAGES:
        status, headers, body, error = fetch(url)
        if status != 200 or len(body) < 800:
            page_notes.append(f"{code}: 읽지 못함({status} {error[:80]})")
            continue
        for doc in discover.documents(decode(body, header(headers, "Content-Type")), url):
            doc["page"] = code
            found.setdefault(doc["id"], doc)
    return found, page_notes


def main(argv):
    moment = now_kst()
    full = "--full" in argv or moment.weekday() == 0
    state = read_json(STATE_PATH, {"docs": {}, "baseline": ""})
    docs = state["docs"]
    first_run = not docs
    found, notes = _discover(moment)
    if not found:
        state.update({"checkedAt": stamp(moment), "notes": notes + ["문서 링크를 하나도 찾지 못해 아무것도 바꾸지 않음"]})
        write_json(STATE_PATH, state)
        print("문서 링크 없음:", notes)
        return 0

    items = []
    families = {discover.family(doc["filename"]): doc_id for doc_id, doc in docs.items() if not doc.get("linked", True) or doc_id not in found}
    for doc_id, info in found.items():
        known = docs.get(doc_id)
        if known and not full:
            known.update({"linked": True, "lastSeen": today(moment), "url": info["url"], "label": info["label"]})
            continue
        status, headers, body, error = fetch(info["url"], timeout=180)
        time.sleep(1)
        if status != 200 or not body or len(body) > MAX_BYTES:
            notes.append(f"{info['filename']}: 받지 못함({status} {error[:60]}, {len(body)}바이트)")
            if known:
                known.update({"linked": True, "lastSeen": today(moment)})
            continue
        digest = sha256_hex(body)
        if known:
            known.update({"linked": True, "lastSeen": today(moment), "lastChecked": stamp(moment), "url": info["url"], "label": info["label"], "filename": info["filename"]})
            latest = known["versions"][-1]
            if latest["sha256"] == digest:
                continue
            version = _store_version(known, body, moment)
            diff_path, stats = _write_diff(doc_id, latest, version)
            version["diff"] = diff_path
            known["versions"].append(version)
            items.append({"id": feed.item_id(SOURCE_CODE, f"{doc_id}:{digest[:12]}"), "source": SOURCE_CODE, "kind": "document", "change": "new-version", "doc": doc_id,
                          "url": info["url"], "text": f"문서의 새 판: {info['filename']}", "diff": diff_path, "stats": stats, "textPath": version["text"], "seenAt": stamp(moment)})
            continue
        doc = {"id": doc_id, "filename": info["filename"], "label": info["label"], "url": info["url"], "lang": info["lang"], "page": info["page"],
               "firstSeen": today(moment), "lastSeen": today(moment), "lastChecked": stamp(moment), "linked": True, "versions": [], "replaces": ""}
        version = _store_version(doc, body, moment)
        doc["versions"].append(version)
        item = {"id": feed.item_id(SOURCE_CODE, f"{doc_id}:new"), "source": SOURCE_CODE, "kind": "document", "change": "new-document", "doc": doc_id,
                "url": info["url"], "text": f"새 문서: {info['filename']}", "textPath": version["text"], "seenAt": stamp(moment)}
        old_id = families.get(discover.family(info["filename"]))
        if old_id and old_id != doc_id and docs.get(old_id, {}).get("versions"):
            doc["replaces"] = old_id
            diff_path, stats = _write_diff(doc_id, docs[old_id]["versions"][-1], version)
            version["diff"] = diff_path
            item.update({"change": "replaced-document", "replaces": old_id, "diff": diff_path, "stats": stats, "text": f"문서가 새 파일로 바뀜: {info['filename']}"})
        docs[doc_id] = doc
        if not first_run:
            items.append(item)

    for doc_id, doc in docs.items():
        if doc_id not in found and doc.get("linked", True):
            doc["linked"] = False
            doc["unlinkedAt"] = today(moment)
            if not first_run:
                items.append({"id": feed.item_id(SOURCE_CODE, f"{doc_id}:unlinked"), "source": SOURCE_CODE, "kind": "document", "change": "unlinked", "doc": doc_id,
                              "url": doc.get("url", ""), "text": f"문서 링크가 화면에서 사라짐: {doc['filename']}", "seenAt": stamp(moment)})

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
