"""글에서 날짜를 찾아 (연, 월, 일)로 바꾼다. 국문, 영문, 독일어, 네덜란드어, ISO 표기를 읽는다."""
import re

MONTHS = {}
for index, names in enumerate([
    ("january", "jan", "januar", "januari"), ("february", "feb", "februar", "februari"), ("march", "mar", "märz", "maart"),
    ("april", "apr"), ("may", "mai", "mei"), ("june", "jun", "juni"), ("july", "jul", "juli"), ("august", "aug", "augustus"),
    ("september", "sep", "sept"), ("october", "oct", "oktober", "okt"), ("november", "nov"), ("december", "dec", "dezember", "dez"),
], start=1):
    for name in names:
        MONTHS[name] = index

_NAME = "|".join(sorted(MONTHS, key=len, reverse=True))
PATTERNS = [
    (re.compile(r"(\d{4})\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일"), lambda m: (int(m[1]), int(m[2]), int(m[3]))),
    # 연-월-일. 구분 글자는 -, /, . 가운데 하나(예: 2026-07-09, 2026/07/09, 2026.07.09)
    (re.compile(r"(?<![\d/])(\d{4})([-/.])(\d{1,2})\2(\d{1,2})(?![\d/])"), lambda m: (int(m[1]), int(m[3]), int(m[4]))),
    # 일 월 연. 사이를 띄우지 않은 표기(예: 28Sep2026)도 읽는다.
    (re.compile(rf"(?<!\d)(\d{{1,2}})\.?\s*({_NAME})\.?,?\s*(\d{{4}})(?!\d)", re.I), lambda m: (int(m[3]), MONTHS[m[2].lower()], int(m[1]))),
    (re.compile(rf"({_NAME})\.?\s+(\d{{1,2}}),?\s+(\d{{4}})", re.I), lambda m: (int(m[3]), MONTHS[m[1].lower()], int(m[2]))),
    (re.compile(r"(\d{1,2})[./](\d{1,2})[./](\d{4})"), lambda m: (int(m[3]), int(m[2]), int(m[1]))),
]


def find(text):
    """(찾은 날짜의 집합, 날짜 표기를 지운 나머지 글)을 돌려준다."""
    found = set()
    rest = text
    for pattern, convert in PATTERNS:
        for match in pattern.finditer(rest):
            try:
                year, month, dayno = convert(match)
            except Exception:
                continue
            if 1 <= month <= 12 and 1 <= dayno <= 31 and 1900 < year < 2100:
                found.add((year, month, dayno))
        rest = pattern.sub(" ", rest)
    return found, rest
