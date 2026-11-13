"""저장소의 수집 결과에서 사이트용 데이터를 만든다: 출처 목록, 원문 대장, 일정, 사이트 정보."""
import re
import urllib.parse

from tools.common.jsonio import read_json, stamp

# 문서 사본은 사이트 안의 files/ 아래에 싣는다(빌드가 originals/files/에서 복사한다). 원문 대장이 이 주소로 문서를 보여 주고 내려받게 한다.
STORE = "originals/files/"
PUBLIC_FILES = "files/"


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
    if str(version.get("file", "")).startswith(STORE):
        return PUBLIC_FILES + urllib.parse.quote(version["file"][len(STORE):])
    return doc.get("url", "")


def stored_files():
    """사이트에 실을 문서 사본의 목록: [(저장소 안의 경로, 사이트 안의 경로)]"""
    state = read_json("originals/state.json", {"docs": {}})
    return [(version["file"], PUBLIC_FILES + version["file"][len(STORE):])
            for doc in state["docs"].values() for version in doc.get("versions", []) if str(version.get("file", "")).startswith(STORE)]


def document_pages(codes):
    """문서가 걸려 있는 화면의 이름과 주소(원문 대장이 문서를 화면별로 묶는 데 쓴다).

    살펴보는 출처의 목록은 사이트에 싣지 않는다. 여기에는 문서를 실제로 내려받은 화면만 들어간다.
    """
    registry = read_json("sources/registry.json", {"sources": []})
    return {source["code"]: {"name": source["name"], "url": source["url"], "order": index}
            for index, source in enumerate(registry["sources"]) if source["code"] in codes}


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
    pages = document_pages({row["page"] for row in rows})
    return {"builtAt": stamp(), "checkedAt": state.get("checkedAt", ""), "unreachable": unreachable, "pages": pages, "documents": rows}, diffs


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


def rule_events(rules):
    """규제별 진행 상황에 적힌 다음 일정을 일정으로 만든다. 규제에 "calendar": false가 있으면 만들지 않는다(이미 일정에 있는 날짜).

    일정의 이름은 규제의 nextTitle(그 날 있을 일을 적은 짧은 구)이고, 없으면 규제 이름이다.
    """
    rows = []
    for rule in (rules or {}).get("regulations", []):
        date = str(rule.get("nextDate", ""))
        links = rule.get("links") or [{}]
        if len(date) != 10 or rule.get("calendar") is False or not rule.get("next"):
            continue
        rows.append({"date": date, "title": rule.get("nextTitle") or rule.get("name", ""), "kind": "입법", "note": rule["next"], "sourceName": links[0].get("text", ""),
                     "link": links[0].get("url", ""), "derived": True, "rule": rule.get("id", "")})
    return rows


def events(listed, prices, rules=None):
    """게시 데이터의 일정에 가격표의 게시일과 규제의 다음 일정을 더한다. 같은 날의 가격 일정이 겹치면 가격표에서 만든 것을 남긴다."""
    derived = price_events(prices)
    price_days = {row["date"] for row in derived}
    kept = [row for row in listed if not (row.get("date") in price_days and "가격" in str(row.get("title", "")))]
    return sorted(kept + derived + rule_events(rules), key=lambda row: (str(row.get("date", "")), str(row.get("title", ""))))


def menu(rules, listed, items=None, topics=None):
    """주 메뉴의 펼침 목록에 쓰는 값: 규제가 하나라도 든 규제 묶음(차례대로), 일정이 있는 해, 소식이 하나라도 있는 주제, 국내 공지·자료의 수.

    제목이 곧 내용인 국내 공지·자료(brief)는 화면(js/news/notices.js)이 주제별 소식에서 빼고 따로 모으므로, 여기에서도 주제를 셀 때 빼고 수만 따로 적는다.

    화면이 처음 뜰 때 읽는 site.json에 실어, 메뉴를 그리려고 큰 자료(규제, 일정, 소식)를 따로 읽지 않게 한다.
    주제 목록(topics)을 넘기면 목록에 없는 주제의 소식은 화면과 같이 '기타'(etc)로 센다.
    """
    used = {rule.get("group") for rule in (rules or {}).get("regulations", [])}
    groups = [{"code": group["code"], "name": group.get("name", ""), "icon": group.get("icon", "")}
              for group in (rules or {}).get("groups", []) if group.get("code") in used]
    years = sorted({int(str(row.get("date", ""))[:4]) for row in listed or [] if str(row.get("date", ""))[:4].isdigit()})
    known = {topic.get("code") for topic in topics or []}
    notices = [item for item in items or [] if item.get("brief") and not item.get("withdrawn")]
    news = [item for item in items or [] if not (item.get("brief") and not item.get("withdrawn"))]
    used_topics = sorted({str(item.get("topic") or "") if not known or item.get("topic") in known else "etc" for item in news} - {""})
    return {"rules": groups, "years": years, "topics": used_topics, "notices": len(notices)}


def site(counts, rules=None, listed=None, items=None, topics=None):
    config = read_json("site/site.config.json", {})
    status = read_json("collected/status.json", {})
    config.update({"builtAt": stamp(), "lastCollected": status.get("checkedAt", ""), "counts": counts, "menu": menu(rules, listed, items, topics)})
    return config
