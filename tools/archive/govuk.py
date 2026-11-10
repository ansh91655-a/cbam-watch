"""영국 정부(GOV.UK)의 CBAM 자료를 모은다.

두 길로 문서를 찾는다: 국세청의 CBAM 자료 모음에 딸린 문서, 그리고 정부 전체 검색에서 제목에 CBAM이 든 문서(재무부의 협의 문서처럼 모음 밖에 있는 것).
문서마다 게시일, 갱신 기록, (협의 문서면) 의견 접수 기간을 GOV.UK의 내용 자료(JSON)에서 읽는다.
crawl은 전체를 다시 읽고, recent는 검색 첫 쪽에 새로 나온 문서만 읽어 기존 목록에 더한다(날마다 도는 것).
"""
import json
import re
import time

from tools.archive.store import ROOT, SINCE, save_index, save_text
from tools.common.jsonio import read_json
from tools.common.net import fetch

API = "https://www.gov.uk/api/content{path}"
SEARCH = "https://www.gov.uk/api/search.json?q={query}&count=50&start={start}&order=-public_timestamp&fields=title,link,public_timestamp"
COLLECTION = "/government/collections/carbon-border-adjustment-mechanism"
QUERIES = ["carbon+border+adjustment+mechanism", "CBAM"]
TITLE = re.compile(r"carbon border adjustment|\bCBAM\b", re.I)
OTHER = re.compile(r"criminal bills", re.I)  # 약자가 같은 다른 제도(Criminal Bills Assessment Manual)
PAGE = 50


def _get(url):
    status, _, body, error = fetch(url, headers={"Accept": "application/json"})
    time.sleep(0.8)
    if status != 200 or not body:
        return None, f"{status} {error[:60]}"
    try:
        return json.loads(body.decode("utf-8", "replace")), ""
    except Exception:
        return None, "자료를 풀지 못함"


def _read(path):
    return _get(API.format(path=path))


def titled(rows):
    """검색 결과에서, 제목에 CBAM이 들고 수집 시작일 뒤에 고쳐진 GOV.UK 문서의 경로만 고른다."""
    return [row["link"] for row in rows if str(row.get("link", "")).startswith("/") and TITLE.search(str(row.get("title", ""))) and not OTHER.search(str(row.get("title", "")))
            and str(row.get("public_timestamp", ""))[:10] >= SINCE]


def _search(notes, pages):
    """{문서 경로: 검색에 적힌 마지막 갱신일}"""
    found = {}
    for query in QUERIES:
        for page in range(pages):
            data, error = _get(SEARCH.format(query=query, start=page * PAGE))
            if data is None:
                notes.append(f"검색 {query} {page + 1}쪽 ({error})")
                break
            rows = data.get("results") or []
            wanted = set(titled(rows))
            for row in rows:
                if row.get("link") in wanted:
                    found.setdefault(row["link"], str(row.get("public_timestamp", ""))[:10])
            if len(rows) < PAGE or all(str(row.get("public_timestamp", ""))[:10] < SINCE for row in rows):
                break
    return found


def changes_of(document, path, via):
    """문서 하나의 갱신 기록을 줄마다 돌려준다. 협의 문서면 의견 접수 기간(opens, closes)을 함께 적는다."""
    rows = []
    title = document.get("title", "")
    details = document.get("details") or {}
    first = str(document.get("first_published_at") or "")[:10]
    extra = {"type": document.get("document_type", ""), "firstPublished": first, "via": via}
    for name, field in (("opens", "opening_date"), ("closes", "closing_date")):
        if details.get(field):
            extra[name] = str(details[field])[:10]
    for change in details.get("change_history") or []:
        date = str(change.get("public_timestamp") or "")[:10]
        if date:
            rows.append({"date": date, "title": title, "note": " ".join(str(change.get("note") or "").split()), "url": f"https://www.gov.uk{path}", **extra})
    if first and not any(row["date"] == first for row in rows):
        rows.append({"date": first, "title": title, "note": "First published.", "url": f"https://www.gov.uk{path}", **extra})
    for row in rows:
        row["key"] = f"{path}@{row['date']}"
    return rows


def _line(entry):
    period = f" | 의견 접수 {entry.get('opens', '')}~{entry.get('closes', '')}" if entry.get("closes") else ""
    return f"{entry['date']} | {entry['title']} | {entry['note']}{period} | {entry['url']}"


def _save(entries, report, incomplete=None):
    kept = sorted((entry for entry in entries if entry["date"] >= SINCE), key=lambda entry: (entry["date"], entry["url"]), reverse=True)
    path = save_text("uk-govuk/changes.txt", ["[주소] https://www.gov.uk" + COLLECTION, ""] + [_line(entry) for entry in kept])
    for entry in kept:
        entry["textPath"] = path
    save_index("uk-govuk", kept, report, incomplete)
    return kept


def _documents(paths, via, failures):
    entries = []
    for path in paths:
        document, error = _read(path)
        if document is None:
            failures.append(f"{path} ({error})")
            continue
        entries += changes_of(document, path, via)
    return entries


def crawl():
    collection, error = _read(COLLECTION)
    if collection is None:  # 읽지 못한 날은 가진 목록을 그대로 둔다
        return {"error": error}
    failures = []
    listed = [row.get("base_path") for row in (collection.get("links") or {}).get("documents") or [] if row.get("base_path")]
    searched = [path for path in _search(failures, pages=4) if path not in listed and path != COLLECTION]
    entries = changes_of(collection, COLLECTION, "collection") + _documents(listed, "collection", failures) + _documents(searched, "search", failures)
    kept = _save(entries, {"documents": len(listed), "searched": len(searched), "changes": len(entries), "failures": failures})
    return {"documents": len(listed), "searched": len(searched), "kept": len(kept), "failures": len(failures)}


def recent():
    """날마다 도는 가벼운 수집: 자료 모음과 검색 첫 쪽을 보고, 처음 보는 문서와 우리가 가진 기록보다 뒤에 고쳐진 문서만 다시 읽는다."""
    stored = read_json(ROOT / "uk-govuk.json", {})
    known = stored.get("entries", [])
    latest = {}
    for entry in known:
        latest[entry["url"]] = max(latest.get(entry["url"], ""), entry["date"])
    failures, stamps, fresh = [], {}, []
    collection, error = _read(COLLECTION)
    if collection is None:
        failures.append(f"{COLLECTION} ({error})")
    else:
        fresh += changes_of(collection, COLLECTION, "collection")
        for row in (collection.get("links") or {}).get("documents") or []:
            if row.get("base_path"):
                stamps[row["base_path"]] = (str(row.get("public_updated_at") or "")[:10], "collection")
    for path, date in _search(failures, pages=1).items():
        if path != COLLECTION:
            stamps.setdefault(path, (date, "search"))
    due = {via: [path for path, (date, how) in stamps.items() if how == via and date > latest.get(f"https://www.gov.uk{path}", "")] for via in ("collection", "search")}
    fresh += _documents(due["collection"], "collection", failures) + _documents(due["search"], "search", failures)
    reread = {entry["url"] for entry in fresh}
    report = {**stored.get("report", {}), "recent": {"reread": len(reread), "failures": failures}}
    # 가진 목록에 새로 읽은 것만 갈아 끼우므로(읽지 못한 문서의 기록은 그대로 남는다) 목록을 따로 지킬 필요가 없다
    kept = _save([entry for entry in known if entry["url"] not in reread] + fresh, report, incomplete=False)
    return {"reread": len(reread), "kept": len(kept), "failures": len(failures)}
