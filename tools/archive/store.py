"""소급 수집 결과를 쓰는 공통 함수. 결과는 모두 collected/archive/ 아래에 둔다."""
import pathlib
import re

from tools.common.jsonio import stamp, write_json

ROOT = pathlib.Path("collected/archive")
SINCE = "2025-01-01"  # 이 날부터의 소식을 모은다

MONTHS = {name: index for index, name in enumerate(
    ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"], start=1)}
LONG_DATE = re.compile(r"^(\d{1,2}) ([A-Za-z]+) (\d{4})$")


def iso_from_long(text):
    """'30 September 2026'을 '2026-09-30'으로 바꾼다. 날짜가 아니면 빈 글."""
    match = LONG_DATE.match(text.strip())
    if not match or match.group(2).lower() not in MONTHS:
        return ""
    return f"{int(match.group(3)):04d}-{MONTHS[match.group(2).lower()]:02d}-{int(match.group(1)):02d}"


def iso_from_numbers(text):
    """'2026-11-09', '2026.10.01', '17/12/2025'를 '2026-11-09' 꼴로 바꾼다. 날짜가 아니면 빈 글."""
    text = text.strip().rstrip(".")
    match = re.match(r"^(\d{4})[-./](\d{1,2})[-./](\d{1,2})$", text)
    if match:
        return f"{int(match.group(1)):04d}-{int(match.group(2)):02d}-{int(match.group(3)):02d}"
    match = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})$", text)
    if match:
        return f"{int(match.group(3)):04d}-{int(match.group(2)):02d}-{int(match.group(1)):02d}"
    return ""


def slug(text, limit=90):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:limit]


def save_index(code, entries, report):
    """출처 하나의 목록을 쓴다. report에는 몇 쪽을 읽었는지, 어디에서 멈췄는지 같은 확인용 값을 적는다."""
    write_json(ROOT / f"{code}.json", {"source": code, "fetchedAt": stamp(), "since": SINCE, "report": report, "entries": entries})


def save_text(relative, lines):
    """원문 글을 쓴다(재이용이 허용된 EU 기관과 영국 정부의 자료만). 저장소 안의 경로를 돌려준다."""
    path = ROOT / "pages" / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(path)
