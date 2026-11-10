"""유럽의회 입법 관측소(Legislative Observatory)의 절차 기록에서 주요 사건(Key events)을 모은다."""
import time

from tools.archive.store import SINCE, iso_from_numbers, save_index, save_text
from tools.common.htmltext import decode, parse
from tools.common.net import fetch, header

PAGE = "https://oeil.europarl.europa.eu/oeil/en/procedure-file?reference={reference}"
# CBAM을 고치는 입법 절차. 새 절차가 생기면 여기에 더한다.
PROCEDURES = ["2025/0039(COD)", "2025/0419(COD)", "2026/0212(COD)"]
HEAD = ["Date", "Event", "Reference", "Summary"]


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
    entries, report = [], {"procedures": {}}
    for reference in PROCEDURES:
        url = PAGE.format(reference=reference)
        status, headers, body, error = fetch(url)
        time.sleep(1.5)
        if status != 200 or not body:
            report["procedures"][reference] = f"읽지 못함({status} {error[:60]})"
            continue
        _, lines, rows = parse(decode(body, header(headers, "Content-Type")), url)
        title, found = events_of(lines, rows, reference)
        name = reference.replace("/", "-").replace("(", "-").replace(")", "")
        path = save_text(f"ep-oeil/{name}.txt", [f"[주소] {url}", ""] + lines + ["", "[표의 행]"] + [" | ".join(cells) for cells in rows])
        for entry in found:
            entry.update({"url": url, "textPath": path})
        entries += [entry for entry in found if entry["date"] >= SINCE]
        report["procedures"][reference] = {"title": title, "events": len(found)}
    save_index("ep-oeil", sorted(entries, key=lambda entry: (entry["date"], entry["procedure"])), report)
    return report
