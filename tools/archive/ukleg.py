"""영국 법령 누리집(legislation.gov.uk)에서 영국 CBAM 법령의 목록과 제정·시행 날짜를 모은다.

제목에 'carbon border adjustment'가 든 법령을 찾고, 법령마다 제정문(made) 화면의 앞부분을 남긴다.
근거 법률(Finance Act 2026)은 차례 화면에서 CBAM을 다루는 편을 찾아 그 차례를 남긴다.
"""
import re
import time

from tools.archive.store import save_index, save_text
from tools.common.htmltext import decode, parse
from tools.common.net import fetch, header

SEARCH = "https://www.legislation.gov.uk/all?title=carbon%20border%20adjustment"
ACT = "https://www.legislation.gov.uk/ukpga/2026/11/contents"
ITEM = re.compile(r"^https://www\.legislation\.gov\.uk/(uksi|ukpga|ukdsi)/(\d{4})/(\d+)/contents(/made)?$")
DATED = re.compile(r"^(Made|Laid before the House of Commons|Laid before Parliament|Coming into force)\b")
HEAD_LINES, LINE_LIMIT = 90, 600


def page(url):
    status, headers, body, error = fetch(url, retries=1)
    time.sleep(1.5)
    if status != 200 or not body:
        return None, [], f"{status} {error[:60]}"
    links, lines, _ = parse(decode(body, header(headers, "Content-Type")), url)
    return links, lines, ""


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
        entries.append({"title": label, "number": f"{match.group(2)} No. {match.group(3)}", "dates": dates_of(kept), "url": made,
                        "textPath": save_text(f"uk-legislation/{match.group(1)}-{match.group(2)}-{match.group(3)}.txt",
                                              [f"[주소] {made}", ""] + [line[:LINE_LIMIT] for line in kept])})
        report["stored"] += 1
    _, text, error = page(ACT)
    if text:
        title = next((line for line in text if line.startswith("Finance Act 2026")), "")
        part = [index for index, line in enumerate(text) if re.search(r"carbon border adjustment mechanism", line, re.I)]
        if title and part:
            kept = text[max(0, part[0] - 2):part[0] + 60]
            entries.append({"title": title, "number": "2026 c. 11", "dates": {}, "url": ACT,
                            "textPath": save_text("uk-legislation/ukpga-2026-11.txt", [f"[주소] {ACT}", "", title, ""] + [line[:LINE_LIMIT] for line in kept])})
            report["stored"] += 1
        else:
            report["failures"].append(f"근거 법률 차례에서 CBAM 편을 찾지 못함(제목 '{title[:40]}')")
    else:
        report["failures"].append(f"근거 법률 차례 ({error})")
    save_index("uk-legislation", entries, report)
    return report
