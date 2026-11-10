"""저장소의 수집 결과에서 사이트용 데이터를 만든다: 출처 목록, 원문 대장, 일정, 사이트 정보."""
import re
import urllib.parse

from tools.common.jsonio import read_json, stamp

# 저장소의 파일을 그대로 내려받는 주소. 원문 대장의 문서 이름을 누르면 이 주소에서 사본을 받는다.
REPO_RAW = "https://raw.githubusercontent.com/ansh91655-a/cbam-watch/main/"


# 화면에 걸린 링크 글이 'Download (1.1 MB - PDF)'처럼 문서를 알려 주지 않는 말이면 파일 이름을 문서 이름으로 쓴다.
GENERIC_LABEL = re.compile(r"^\s*(download|available|click|here|english|pdf|xlsx?|zip|open|view)\b", re.I)


def _title(doc):
    label = " ".join(str(doc.get("label", "")).split())
    if len(label) >= 8 and not GENERIC_LABEL.match(label):
        return label
    stem = doc["filename"].rsplit(".", 1)[0]
    return " ".join(stem.replace("_", " ").split())


def _download(version, doc):
    """내려받는 주소. 사본이 있으면 사본, 없으면(압축 파일, 큰 파일) 원래 올라온 곳."""
    if version.get("file"):
        return REPO_RAW + urllib.parse.quote(version["file"])
    return doc.get("url", "")


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
        versions = doc.get("versions", [])
        latest = versions[-1] if versions else {}
        diff_path = next((version["diff"] for version in reversed(versions) if version.get("diff")), "")
        if diff_path:
            diffs.append(diff_path)
        filename = doc["filename"]
        rows.append({
            "id": doc["id"], "title": _title(doc), "filename": filename, "page": doc.get("page", ""),
            "format": filename.rsplit(".", 1)[-1].upper() if "." in filename else "",
            "date": latest.get("date", ""), "bytes": latest.get("bytes", 0), "pages": latest.get("pages", 0),
            "download": _download(latest, doc), "stored": bool(latest.get("file")),
            "versions": len(versions),
            "earlier": [{"date": version["date"], "download": _download(version, doc)} for version in versions[:-1] if version.get("file")],
            "diff": ("data/diffs/" + diff_path.split("originals/diffs/", 1)[1]) if diff_path else "",
            "linked": doc.get("linked", True), "firstSeen": doc.get("firstSeen", ""),
        })
    # 자동으로 받지 못한 문서 링크의 수(화면별). 사이트가 원문 대장에 한 줄로 알린다.
    unreachable = {}
    for entry in state.get("pending", {}).values():
        if int(entry.get("tries", 0) or 0) > 0:
            unreachable[entry.get("page", "")] = unreachable.get(entry.get("page", ""), 0) + 1
    return {"builtAt": stamp(), "checkedAt": state.get("checkedAt", ""), "unreachable": unreachable, "documents": rows}, diffs


def price_events(prices):
    """가격표에 적힌 게시일을 일정으로 만든다(지난 게시일과 게시 예정일)."""
    source = prices.get("source", {})
    rows = []
    for row in prices.get("prices", []):
        if row.get("published"):
            rows.append({"date": row["published"], "title": f"{row['label']} CBAM 인증서 가격 게시", "kind": "가격", "note": f"{row['value']:.2f}유로",
                         "sourceName": source.get("name", ""), "link": source.get("url", ""), "derived": True})
    for row in prices.get("upcoming", []):
        if row.get("published"):
            rows.append({"date": row["published"], "title": f"{row['label']} CBAM 인증서 가격 게시 예정", "kind": "가격", "note": "",
                         "sourceName": source.get("name", ""), "link": source.get("url", ""), "derived": True})
    return rows


def events(listed, prices):
    """게시 데이터의 일정에 가격표의 게시일을 더한다. 같은 날의 가격 일정이 겹치면 가격표에서 만든 것을 남긴다."""
    derived = price_events(prices)
    price_days = {row["date"] for row in derived}
    kept = [row for row in listed if not (row.get("date") in price_days and "가격" in str(row.get("title", "")))]
    return sorted(kept + derived, key=lambda row: (str(row.get("date", "")), str(row.get("title", ""))))


def site(counts):
    config = read_json("site/site.config.json", {})
    status = read_json("collected/status.json", {})
    config.update({"builtAt": stamp(), "lastCollected": status.get("checkedAt", ""), "counts": counts})
    return config
