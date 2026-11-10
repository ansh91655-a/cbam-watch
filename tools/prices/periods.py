"""가격표의 '적용 기간' 칸을 읽어 기간의 종류와 시작일, 끝일을 정한다.

2026년은 분기('Q1 2026')다. 2027년부터는 주 단위인데 표의 꼴이 아직 공개되지 않아, 흔한 꼴 세 가지를 읽는다:
주 번호('Week 1 2027', '2027-W01'), 날짜 범위('4 January 2027 - 10 January 2027', '4-10 January 2027'), 날짜 하나.
읽지 못하면 None을 돌려준다.
"""
import datetime
import re

from tools.check import dates

QUARTER = re.compile(r"\bQ\s*([1-4])\s*[-/ ]?\s*(20\d\d)\b|\b(20\d\d)\s*[-/ ]?\s*Q\s*([1-4])\b", re.I)
WEEK = re.compile(r"\bW(?:eek)?\s*\.?\s*(\d{1,2})\b[^0-9]{0,12}(20\d\d)|\b(20\d\d)\s*[-/ ]?\s*W(?:eek)?\s*(\d{1,2})\b", re.I)
SHORT_RANGE = re.compile(r"\b(\d{1,2})\s*[-–—]\s*(\d{1,2})\s+([A-Za-z]{3,9})\s+(20\d\d)\b")
QUARTER_END = {1: (3, 31), 2: (6, 30), 3: (9, 30), 4: (12, 31)}


def _iso(value):
    return value.isoformat()


def days(text):
    """글에서 읽은 날짜를 이른 것부터 돌려준다."""
    found, _ = dates.find(str(text))
    result = []
    for year, month, dayno in sorted(found):
        try:
            result.append(datetime.date(year, month, dayno))
        except ValueError:
            continue
    return result


def quarter(year, number):
    start = datetime.date(year, 3 * number - 2, 1)
    month, day = QUARTER_END[number]
    return {"period": f"{year}-Q{number}", "kind": "quarter", "label": f"{year}년 {number}분기", "from": _iso(start), "to": _iso(datetime.date(year, month, day))}


def week(year, number):
    try:
        start = datetime.date.fromisocalendar(year, number, 1)
    except ValueError:
        return None
    return span(start, start + datetime.timedelta(days=6))


def span(start, end):
    """날짜 범위. 여드레 이하면 주간 가격으로 본다."""
    if end < start:
        return None
    kind = "week" if (end - start).days <= 7 else "range"
    iso = start.isocalendar()
    label = f"{iso[0]}년 {iso[1]}주({start.month}월 {start.day}일~{end.month}월 {end.day}일)" if kind == "week" else f"{_iso(start)} ~ {_iso(end)}"
    return {"period": _iso(start), "kind": kind, "label": label, "from": _iso(start), "to": _iso(end)}


def read(cell):
    text = " ".join(str(cell).split())
    found = QUARTER.search(text)
    if found:
        number, year = (found.group(1), found.group(2)) if found.group(1) else (found.group(4), found.group(3))
        return quarter(int(year), int(number))
    found = WEEK.search(text)
    if found:
        number, year = (found.group(1), found.group(2)) if found.group(1) else (found.group(4), found.group(3))
        return week(int(year), int(number))
    found = SHORT_RANGE.search(text)
    if found:
        starts = days(f"{found.group(1)} {found.group(3)} {found.group(4)}")
        ends = days(f"{found.group(2)} {found.group(3)} {found.group(4)}")
        if starts and ends:
            return span(starts[0], ends[0])
    found_days = days(text)
    if len(found_days) >= 2:
        return span(found_days[0], found_days[-1])
    if len(found_days) == 1:
        # 날짜가 하나뿐이면 그날부터 한 주로 본다. 추정이므로 표시를 남긴다.
        guessed = span(found_days[0], found_days[0] + datetime.timedelta(days=6))
        guessed["assumed"] = True
        return guessed
    return None
