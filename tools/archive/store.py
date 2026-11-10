"""소급 수집 결과를 쓰는 공통 함수. 결과는 모두 collected/archive/ 아래에 둔다."""
import pathlib
import re

from tools.common.jsonio import read_json, stamp, write_json

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


# 같은 기록인지 가리는 데 쓰는 값들(출처마다 있는 것만 쓴다)
IDENTITY = ("celex", "procedure", "reference", "number", "url", "date", "event", "title", "note")


def _identity(entry):
    return tuple(str(entry.get(key, "")) for key in IDENTITY)


def carry_over(entries, previous):
    """앞의 목록에 있던 기록 가운데 이번 목록에 없는 것을 뒤에 붙인다. (합친 목록, 붙인 수)를 돌려준다."""
    have = {_identity(entry) for entry in entries}
    carried = [entry for entry in previous if _identity(entry) not in have]
    return list(entries) + carried, len(carried)


def save_index(code, entries, report, incomplete=None):
    """출처 하나의 목록을 쓴다. report에는 몇 쪽을 읽었는지, 어디에서 멈췄는지 같은 확인용 값을 적는다.

    읽지 못한 것이 있는 실행(incomplete)은 목록을 줄이지 않는다: 앞의 목록에 있던 기록 가운데 이번에 빠진 것을 그대로 남긴다.
    사이트가 점검 중이거나 답이 끊긴 날에 모아 둔 공식 기록이 사라지면, 규제 연혁의 근거가 없어진 것처럼 보이기 때문이다.
    incomplete를 주지 않으면 report의 error와 failures로 판단한다. 스스로 앞의 목록과 합치는 출처는 False를 준다.
    """
    if incomplete is None:
        incomplete = bool(report.get("error")) or bool(report.get("failures"))
    if incomplete:
        entries, carried = carry_over(entries, read_json(ROOT / f"{code}.json", {}).get("entries", []))
        if carried:
            report = {**report, "keptFromBefore": report.get("keptFromBefore", 0) + carried}
    write_json(ROOT / f"{code}.json", {"source": code, "fetchedAt": stamp(), "since": SINCE, "report": report, "entries": entries})


def save_text(relative, lines):
    """원문 글을 쓴다(재이용이 허용된 EU 기관과 영국 정부의 자료만). 저장소 안의 경로를 돌려준다."""
    path = ROOT / "pages" / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(path)
