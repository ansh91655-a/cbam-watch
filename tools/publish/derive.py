"""저장소의 수집 결과에서 사이트용 데이터를 만든다: 출처 목록, 원문 대장, 사이트 정보."""
from tools.common.jsonio import read_json, stamp

REPO_BLOB = "https://github.com/ansh91655-a/cbam-watch/blob/main/"


def sources():
    registry = read_json("sources/registry.json", {"sources": []})
    status = read_json("collected/status.json", {"sources": {}}).get("sources", {})
    claude = read_json("collected/claude-status.json", {"sources": {}}).get("sources", {})
    rows = []
    for source in registry["sources"]:
        # 확인 방법에 맞는 기록만 쓴다: 자동 수집은 수집 실행의 기록, 자동 열람은 정리 실행의 기록
        book = {"github": status, "claude": claude}.get(source["collector"], {})
        state = book.get(source["code"]) or {}
        rows.append({
            "no": source["no"], "code": source["code"], "name": source["name"], "group": source["group"], "url": source["url"],
            "tier": source["tier"], "collector": source["collector"], "note": source.get("note", ""),
            "lastChecked": state.get("lastOk") or "", "ok": state.get("ok") if state else None, "failCount": int(state.get("failCount", 0) or 0),
        })
    return {"builtAt": stamp(), "sources": rows}


def documents():
    state = read_json("originals/state.json", {"docs": {}})
    rows, diffs = [], []
    for doc in state["docs"].values():
        versions = []
        for version in doc.get("versions", []):
            diff_path = version.get("diff", "")
            if diff_path:
                diffs.append(diff_path)
            versions.append({
                "date": version["date"], "sha": version["sha256"][:12], "bytes": version["bytes"], "pages": version.get("pages", 0), "chars": version.get("chars", 0),
                "file": REPO_BLOB + version["file"] if version.get("file") else "",
                "text": REPO_BLOB + version["text"] if version.get("text") else "",
                "diff": ("data/diffs/" + diff_path.split("originals/diffs/", 1)[1]) if diff_path else "",
            })
        title = doc["filename"].rsplit(".", 1)[0]
        rows.append({"id": doc["id"], "title": title, "filename": doc["filename"], "label": doc.get("label", ""), "url": doc.get("url", ""), "page": doc.get("page", ""),
                     "firstSeen": doc.get("firstSeen", ""), "lastChecked": doc.get("lastChecked", ""), "linked": doc.get("linked", True), "replaces": doc.get("replaces", ""), "versions": versions})
    # 자동으로 받지 못해 사본을 두지 못한 문서 링크의 수(화면별). 사이트가 원문 대장에 한 줄로 알린다.
    unreachable = {}
    for entry in state.get("pending", {}).values():
        if int(entry.get("tries", 0) or 0) > 0:
            unreachable[entry.get("page", "")] = unreachable.get(entry.get("page", ""), 0) + 1
    return {"builtAt": stamp(), "checkedAt": state.get("checkedAt", ""), "unreachable": unreachable, "documents": rows}, diffs


def site(counts):
    config = read_json("site/site.config.json", {})
    status = read_json("collected/status.json", {})
    config.update({"builtAt": stamp(), "lastCollected": status.get("checkedAt", ""), "counts": counts})
    return config
