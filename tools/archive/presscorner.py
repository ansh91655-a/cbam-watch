"""EU 집행위원회 보도자료 창구(Press corner)에서 CBAM을 다룬 자료를 모은다.

목록을 새 것부터 넘겨 보며 2025년 1월까지 거슬러 올라간다. 제목이 관련 낱말을 담은 자료와 일일 소식(Daily News)의 본문을 열어,
본문이 CBAM을 말하는 것만 남긴다. 일일 소식은 CBAM을 말하는 문단과 그 앞뒤 문단만 남긴다.
"""
import json
import re
import time

from tools.archive.store import ROOT, SINCE, save_index, save_text
from tools.common.htmltext import parse
from tools.common.jsonio import read_json
from tools.common.net import fetch

LIST = "https://ec.europa.eu/commission/presscorner/api/search?language=en&pagesize=50&pagenumber={page}"
DOCUMENT = "https://ec.europa.eu/commission/presscorner/api/documents?reference={reference}&language=en"
DETAIL = "https://ec.europa.eu/commission/presscorner/detail/en/{name}"
TITLE = re.compile(r"CBAM|carbon border|emissions trading|\bETS\b|carbon market|carbon pric|carbon leakage|decarboni|omnibus|simplif"
                   r"|steel|alumini|fertili|cement|clean industrial|industrial accelerator|climate|2040|\btrade\b|tariff|summit|joint statement"
                   r"|United Kingdom|\bUK\b|United States|\bUS\b|India|Norway|Iceland|own resources|multiannual financial", re.I)
MENTION = re.compile(r"CBAM|carbon border adjustment", re.I)
MAX_PAGES, MAX_LINES, LINE_LIMIT, PAUSE = 260, 260, 900, 0.25
RECENT_PAGES, SEEN_LIMIT = 8, 4000


def listing(page):
    status, _, body, error = fetch(LIST.format(page=page), headers={"Accept": "application/json"}, retries=1)
    time.sleep(PAUSE)
    if status != 200 or not body:
        return None, f"{status} {error[:60]}"
    try:
        return json.loads(body.decode("utf-8", "replace")).get("docuLanguageListResources") or [], ""
    except Exception as problem:
        return None, f"목록을 풀지 못함: {problem}"


def document(reference):
    """자료 하나의 (제목, 본문 줄 목록)을 돌려준다."""
    status, _, body, _ = fetch(DOCUMENT.format(reference=reference), headers={"Accept": "application/json"}, retries=1)
    time.sleep(PAUSE)
    if status != 200 or not body:
        return "", []
    try:
        resource = json.loads(body.decode("utf-8", "replace")).get("docuLanguageResource") or {}
    except Exception:
        return "", []
    _, lines, _ = parse("<html><body>" + (resource.get("htmlContent") or "") + "</body></html>", DETAIL.format(name=""))
    return resource.get("title") or "", lines


def around(lines):
    """CBAM을 말하는 줄과 그 앞뒤 한 줄씩만 남긴다(일일 소식용)."""
    keep = set()
    for index, line in enumerate(lines):
        if MENTION.search(line):
            keep.update({index - 1, index, index + 1})
    return [lines[index] for index in sorted(keep) if 0 <= index < len(lines)]


def recent(deadline=None):
    """평일 자동 실행용: 목록의 앞쪽 몇 쪽만 보고, 전에 모은 것에 새 자료를 더한다."""
    return crawl(deadline, pages=RECENT_PAGES, merge=True)


def crawl(deadline=None, pages=MAX_PAGES, merge=False):
    before = read_json(ROOT / "ec-press.json", {}) if merge else {}
    seen = set(before.get("report", {}).get("seen", [])) | {entry["reference"] for entry in before.get("entries", [])}
    entries, report = [], {"pages": 0, "listed": 0, "opened": 0, "kept": 0, "failures": []}
    previous_first, done = None, False
    for page in range(1, pages + 1):
        if deadline and time.monotonic() > deadline:
            report["stoppedAt"] = f"목록 {page}쪽"
            break
        rows, error = listing(page)
        if rows is None:
            report["failures"].append(f"목록 {page}쪽: {error}")
            break
        if not rows or rows[0].get("refCode") == previous_first:
            report["stoppedAt"] = f"목록 {page}쪽에서 새 자료가 없음"
            break
        previous_first = rows[0].get("refCode")
        report["pages"] += 1
        for row in rows:
            date, reference, title = row.get("eventDate") or "", row.get("refCode") or "", row.get("title") or ""
            if date and date < SINCE:
                done = True
                break
            report["listed"] += 1
            kind = (row.get("docutype") or {}).get("code") or ""
            if not reference or reference in seen or not (kind == "MEX" or TITLE.search(title) or TITLE.search(row.get("leadText") or "")):
                continue
            seen.add(reference)
            _, lines = document(reference)
            report["opened"] += 1
            count = sum(len(MENTION.findall(line)) for line in lines)
            if not count:
                continue
            kept = around(lines) if kind == "MEX" else lines
            name = reference.lower().replace("/", "_")
            url = DETAIL.format(name=name)
            entries.append({"date": date, "reference": reference, "kind": kind, "title": title, "mentions": count, "url": url,
                            "textPath": save_text(f"ec-press/{name}.txt", [f"[주소] {url}", f"[날짜] {date}", f"[제목] {title}", ""]
                                                  + [line[:LINE_LIMIT] for line in kept[:MAX_LINES]])})
            report["kept"] += 1
        if done:
            break
    entries += [entry for entry in before.get("entries", []) if entry["reference"] not in {row["reference"] for row in entries}]
    report["oldest"] = min((entry["date"] for entry in entries), default="")
    report["total"] = len(entries)
    # 열어 본 자료의 번호를 남겨, 다음 실행이 같은 자료를 다시 열지 않게 한다(목록만 남기고 화면에 찍지는 않는다)
    save_index("ec-press", sorted(entries, key=lambda entry: (entry["date"], entry["reference"]), reverse=True), {**report, "seen": sorted(seen)[-SEEN_LIMIT:]})
    return report
