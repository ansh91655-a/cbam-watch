"""영국 법령 누리집(legislation.gov.uk)에서 영국 CBAM 법령의 목록과 제정·시행 날짜를 모은다.

제목에 'carbon border adjustment'가 든 법령을 찾고, 법령마다 제정문(made) 화면의 앞부분을 남긴다.
근거 법률(Finance Act 2026)은 차례 화면에서 CBAM을 다루는 편을 찾아 그 차례를 남긴다.
규제 분석 글의 근거로 쓰도록, 하위 법령과 근거 법률의 CBAM 편·부칙은 온전한 글도 따로 받아 둔다(-full, -part-5, -schedule-N).
"""
import re
import time

from tools.archive.store import save_index, save_text
from tools.common.htmltext import decode, parse
from tools.common.net import fetch, header

SEARCH = "https://www.legislation.gov.uk/all?title=carbon%20border%20adjustment"
ACT = "https://www.legislation.gov.uk/ukpga/2026/11/contents"
ACT_INTRODUCTION = "https://www.legislation.gov.uk/ukpga/2026/11/introduction"
ITEM = re.compile(r"^https://www\.legislation\.gov\.uk/(uksi|ukpga|ukdsi)/(\d{4})/(\d+)/contents(/made)?$")
DATED = re.compile(r"^(Made|Laid before the House of Commons|Laid before Parliament|Coming into force)\b")
HEAD_LINES, LINE_LIMIT = 90, 600
# 온전한 글을 내주는 주소(화면 한 장에 법령 전체가 들어 있다)
WHOLE = "https://www.legislation.gov.uk/{kind}/{year}/{number}/made/data.htm"
ACT_PART = "https://www.legislation.gov.uk/ukpga/2026/11/part/5/data.htm"
ACT_SCHEDULE = "https://www.legislation.gov.uk/ukpga/2026/11/schedule/{number}/data.htm"
SCHEDULE = re.compile(r"/ukpga/2026/11/schedule/(\d+)$")
FULL_LINES, FULL_LINE_LIMIT = 6000, 2400


def page(url):
    status, headers, body, error = fetch(url, retries=1)
    time.sleep(1.5)
    if status != 200 or not body:
        return None, [], f"{status} {error[:60]}"
    links, lines, _ = parse(decode(body, header(headers, "Content-Type")), url)
    return links, lines, ""


def whole(url, name):
    """법령의 온전한 글을 받아 둔다. (저장 경로, 받지 못한 사유)를 돌려준다."""
    _, lines, error = page(url)
    kept = [line[:FULL_LINE_LIMIT] for line in lines if line.strip()][:FULL_LINES]
    if len(kept) < 20:
        return "", error or f"글이 너무 짧음({len(kept)}줄)"
    return save_text(f"uk-legislation/{name}.txt", [f"[주소] {url}", ""] + kept), ""


def dates_of(lines):
    """제정문 앞머리의 'Made', 'Laid before…', 'Coming into force'와 그 다음 줄(날짜)을 묶는다."""
    found = {}
    for index, line in enumerate(lines[:80]):
        match = DATED.match(line.strip())
        if match and index + 1 < len(lines):
            rest = line.strip()[len(match.group(1)):].strip(" -–:")
            found.setdefault(match.group(1), rest or lines[index + 1].strip())
    return found


def crawl():
    entries, report = [], {"found": 0, "stored": 0, "failures": []}
    links, lines, error = page(SEARCH)
    if links is None:
        save_index("uk-legislation", [], {"error": error})
        return {"error": error}
    seen = []
    for url, label in links:
        match = ITEM.match(url)
        if match and url not in [row[0] for row in seen]:
            seen.append((url, label, match))
    report["found"] = len(seen)
    for url, label, match in seen:
        made = f"https://www.legislation.gov.uk/{match.group(1)}/{match.group(2)}/{match.group(3)}/made"
        _, text, error = page(made)
        if not text:
            report["failures"].append(f"{label[:60]} ({error})")
            continue
        start = next((index for index, line in enumerate(text) if line.strip() in ("Statutory Instruments", "Draft Statutory Instruments")), 0)
        kept = text[start:start + HEAD_LINES]
        name = f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
        entry = {"title": label, "number": f"{match.group(2)} No. {match.group(3)}", "dates": dates_of(kept), "url": made,
                 "textPath": save_text(f"uk-legislation/{name}.txt", [f"[주소] {made}", ""] + [line[:LINE_LIMIT] for line in kept])}
        full, why = whole(WHOLE.format(kind=match.group(1), year=match.group(2), number=match.group(3)), f"{name}-full")
        if full:
            entry["fullTextPath"] = full
        else:
            report["failures"].append(f"{label[:60]} 전문 ({why})")
        entries.append(entry)
        report["stored"] += 1
    act_links, text, error = page(ACT)
    if text:
        title = next((line for line in text if line.startswith("Finance Act 2026")), "")
        part = [index for index, line in enumerate(text) if re.search(r"carbon border adjustment mechanism", line, re.I)]
        if title and part:
            kept = text[max(0, part[0] - 2):part[0] + 60]
            # 법률의 머리글(제정일이 적혀 있다)도 함께 남긴다
            _, opening, _ = page(ACT_INTRODUCTION)
            start = next((index for index, line in enumerate(opening) if line.strip().startswith("2026 CHAPTER")), None)
            if start is not None:
                kept = ["[머리글] " + ACT_INTRODUCTION] + opening[start:start + 6] + ["", "[차례]"] + kept
            entry = {"title": title, "number": "2026 c. 11", "dates": {}, "url": ACT,
                     "textPath": save_text("uk-legislation/ukpga-2026-11.txt", [f"[주소] {ACT}", "", title, ""] + [line[:LINE_LIMIT] for line in kept])}
            # CBAM을 다루는 편과, 차례에서 CBAM이라고 적힌 부칙의 온전한 글
            wanted = [(ACT_PART, "ukpga-2026-11-part-5")]
            for url, label in act_links or []:
                found = SCHEDULE.search(url)
                if found and re.search(r"CBAM|carbon border", label, re.I):
                    wanted.append((ACT_SCHEDULE.format(number=found.group(1)), f"ukpga-2026-11-schedule-{found.group(1)}"))
            entry["fullTextPaths"] = []
            for url, name in wanted:
                full, why = whole(url, name)
                if full:
                    entry["fullTextPaths"].append(full)
                else:
                    report["failures"].append(f"근거 법률 {name} ({why})")
            entries.append(entry)
            report["stored"] += 1
        else:
            report["failures"].append(f"근거 법률 차례에서 CBAM 편을 찾지 못함(제목 '{title[:40]}')")
    else:
        report["failures"].append(f"근거 법률 차례 ({error})")
    save_index("uk-legislation", entries, report)
    return report
