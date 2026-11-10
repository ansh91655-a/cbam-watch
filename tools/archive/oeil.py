"""유럽의회 입법 관측소(Legislative Observatory)의 절차 기록에서 주요 사건(Key events)을 모은다."""
import time

from tools.archive.store import ROOT, SINCE, iso_from_numbers, save_index, save_text
from tools.common.htmltext import decode, parse
from tools.common.jsonio import read_json
from tools.common.net import fetch, header

PAGE = "https://oeil.europarl.europa.eu/oeil/en/procedure-file?reference={reference}"
# CBAM을 고치거나 CBAM과 맞물린 입법 절차. 새 절차가 생기면 여기에 더한다.
PROCEDURES = ["2025/0039(COD)", "2025/0419(COD)", "2025/0418(COD)", "2026/0212(COD)", "2025/0574(CNS)"]
# 이 문서들의 글에 적힌 절차 번호도 함께 읽는다(tools/archive/docs.py가 받아 둔 문서)
FOLLOW = {"52026PC0619"}
HEAD = ["Date", "Event", "Reference", "Summary"]
FORECAST_HEAD = ["Date", "Subject"]


def procedures():
    """읽을 절차 번호. 정해 둔 것에, 받아 둔 문서에서 찾은 번호를 더한다."""
    found = list(PROCEDURES)
    for entry in read_json(ROOT / "eur-lex-docs.json", {}).get("entries", []):
        if entry.get("celex") in FOLLOW:
            found += [reference for reference in entry.get("procedures", []) if reference not in found]
    return found


def status_of(lines):
    """화면의 'Status' 다음 줄(절차의 현재 단계)."""
    for index, line in enumerate(lines):
        if line == "Status" and index + 1 < len(lines):
            return lines[index + 1]
    return ""


def forecasts_of(rows):
    """'Forecasts' 표(예정 일정)의 행."""
    found, inside = [], False
    for cells in rows:
        if cells[:2] == FORECAST_HEAD and len(cells) == 2:
            inside = True
            continue
        if inside:
            date = iso_from_numbers(cells[0]) if cells else ""
            if not date:
                break
            found.append({"date": date, "subject": cells[1] if len(cells) > 1 else ""})
    return found


def events_of(lines, rows, reference):
    """화면의 글과 표에서 (절차의 이름, 주요 사건 목록)을 뽑는다."""
    title = ""
    for index, line in enumerate(lines):
        if line == "Full procedure" and index + 1 < len(lines):
            title = lines[index + 1]
            break
    found, inside = [], False
    for cells in rows:
        if cells[:4] == HEAD:
            inside = True
            continue
        if not inside:
            continue
        date = iso_from_numbers(cells[0]) if cells else ""
        if not date:
            break
        found.append({"date": date, "event": cells[1] if len(cells) > 1 else "", "reference": cells[2] if len(cells) > 2 else "",
                      "procedure": reference, "procedureTitle": title})
    return title, found


def crawl():
    before = read_json(ROOT / "ep-oeil.json", {})
    entries, report = [], {"procedures": {}, "failures": []}
    for reference in procedures():
        url = PAGE.format(reference=reference)
        status, headers, body, error = fetch(url)
        time.sleep(1.5)
        if status != 200 or not body:
            # 읽지 못한 절차는 앞에 모아 둔 기록과 상태를 그대로 둔다(기록이 없어진 것으로 보지 않는다)
            report["failures"].append(f"{reference}: 읽지 못함({status} {error[:60]})")
            known = before.get("report", {}).get("procedures", {}).get(reference)
            report["procedures"][reference] = known if isinstance(known, dict) else f"읽지 못함({status} {error[:60]})"
            entries += [entry for entry in before.get("entries", []) if entry.get("procedure") == reference]
            continue
        _, lines, rows = parse(decode(body, header(headers, "Content-Type")), url)
        title, found = events_of(lines, rows, reference)
        name = reference.replace("/", "-").replace("(", "-").replace(")", "")
        path = save_text(f"ep-oeil/{name}.txt", [f"[주소] {url}", ""] + lines + ["", "[표의 행]"] + [" | ".join(cells) for cells in rows])
        for entry in found:
            entry.update({"url": url, "textPath": path})
        entries += [entry for entry in found if entry["date"] >= SINCE]
        report["procedures"][reference] = {"title": title, "events": len(found), "status": status_of(lines), "forecasts": forecasts_of(rows), "url": url}
    save_index("ep-oeil", sorted(entries, key=lambda entry: (entry["date"], entry["procedure"])), report)
    return report
