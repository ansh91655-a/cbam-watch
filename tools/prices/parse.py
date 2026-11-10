"""EU 집행위원회의 인증서 가격 화면 글에서 가격표의 행을 읽는다.

화면 글 파일(collected/pages/ec-price.txt)의 '[표의 행]' 아래에 표의 행이 '칸 | 칸 | 칸' 꼴로 있다.
행 하나는 적용 기간, 게시일, 가격으로 되어 있다(예: 'Q3 2026 | 5 October 2026 | 82.32'). 가격이 비어 있으면 아직 게시 전이다.
숫자가 있는데도 읽지 못한 행은 unparsed로 돌려준다. 표의 꼴이 바뀌었다는 신호이므로 보고 실행이 문제로 알린다.
"""
import re

from tools.prices import periods

MARK = "[표의 행]"
PRICE = re.compile(r"^(?:€|EUR)?\s*(\d{1,4}(?:[.,]\d{1,3})?)\s*(?:€|EUR)?$", re.I)


def table_rows(page_text):
    """화면 글에서 표의 행만 골라 칸의 목록으로 돌려준다."""
    if MARK not in page_text:
        return []
    rows = []
    for line in page_text.split(MARK, 1)[1].splitlines():
        if "|" in line:
            rows.append([cell.strip() for cell in line.split("|")])
    return rows


def _price(cell):
    found = PRICE.match(cell.strip())
    return float(found.group(1).replace(",", ".")) if found else None


def read_row(cells):
    """행 하나를 읽는다. 가격표의 행이 아니면(머리글 따위) None, 읽지 못하면 {'unparsed': 원문}."""
    raw = " | ".join(cells)
    if not any(char.isdigit() for char in raw):
        return None
    period = periods.read(cells[0]) if cells else None
    rest = cells[1:]
    value = None
    for cell in reversed(rest):
        if cell:
            value = _price(cell)
            break
    published = ""
    for cell in rest:
        if _price(cell) is None:
            found = periods.days(cell)
            if found:
                published = found[0].isoformat()
                break
    if period is None or (value is None and not published):
        return {"unparsed": raw}
    row = dict(period)
    row.update({"published": published, "raw": raw})
    if value is not None:
        row["value"] = value
    return row


def read(page_text):
    """(가격이 있는 행, 게시 전인 행, 읽지 못한 행)을 돌려준다."""
    priced, upcoming, unparsed = [], [], []
    for cells in table_rows(page_text):
        row = read_row(cells)
        if row is None:
            continue
        if "unparsed" in row:
            unparsed.append(row["unparsed"])
        else:
            if row.get("assumed"):
                unparsed.append("(기간을 추정함) " + row["raw"])
            (priced if "value" in row else upcoming).append(row)
    return priced, upcoming, unparsed
