"""받아 둔 법령 부속서의 표(collected/archive/pages/eu-tables/)를 인증서 비용 추정에 쓸 모양으로 읽는다.

- 벤치마크 표(benchmarks.txt): 무상할당 조정 이행규정 (EU) 2025/2620 부속서 5.3. 품목(CN 8자리)마다 A열(공정 벤치마크)과 B열(기본 벤치마크)이 있고,
  값이 여럿인 칸에는 표시가 붙어 있다: (A)~(L)은 생산 경로, (1)과 (2)는 생산 연도(2026~27년, 2028~30년).
- 기본값 표(defaults.txt): 기본값 이행규정 (EU) 2025/2621 부속서 I(정정 규정이 갈아 끼운 글)의 대한민국 표와 '그 밖의 나라와 지역' 표.
  행의 코드는 4, 6, 8자리(CN)이거나 10자리(TARIC)이고, 값 칸에는 수, '-'(값 없음), 'see below'(아래의 행을 보라), 'N/A'(해당 없음)가 온다.
읽은 결과에는 계산이나 풀이를 더하지 않는다. 짝을 짓고 고르는 일은 tools/calc/build.py가 한다.
"""
import pathlib
import re

from tools.common.rowtext import read_tables

ROOT = pathlib.Path("collected/archive/pages/eu-tables")
BENCHMARKS = ROOT / "benchmarks.txt"
DEFAULTS = ROOT / "defaults.txt"
SECTORS = {"cement": "cement", "fertilisers": "fertilisers", "iron & steel": "steel", "iron and steel": "steel", "aluminium": "aluminium", "hydrogen": "hydrogen"}
NUMBER = re.compile(r"^\d+,\d+$")
VALUE = re.compile(r"(\d+,\d+)((?:\s*\([A-Z0-9]\))*)")
TAG = re.compile(r"\(([A-Z0-9])\)")
KOREA = re.compile(r"korea", re.I)
OTHER = re.compile(r"other countries and territories", re.I)


class Unreadable(Exception):
    """받아 둔 표가 기대한 모양이 아닐 때. 무엇이 다른지 글로 알린다."""


def number(text):
    return float(text.replace(",", "."))


def digits(code):
    return re.sub(r"\D", "", code)


def variants(cell):
    """벤치마크 칸의 값들: [{"value": 수, "route": 경로 글자 또는 "", "period": 1, 2 또는 0}].

    '1,460 (F)(1) 0,659 (G)(1)'처럼 값마다 표시가 뒤따른다. 표시가 없는 값 하나만 있으면 경로와 연도에 상관없이 쓰는 값이다.
    """
    found = []
    for match in VALUE.finditer(cell):
        tags = TAG.findall(match.group(2))
        routes = [tag for tag in tags if tag.isalpha()]
        periods = [int(tag) for tag in tags if tag.isdigit()]
        if len(routes) > 1 or len(periods) > 1:
            raise Unreadable(f"값 하나에 표시가 겹침: {cell}")
        found.append({"value": number(match.group(1)), "route": routes[0] if routes else "", "period": periods[0] if periods else 0})
    left = VALUE.sub("", cell).strip()
    if left or not found:
        raise Unreadable(f"읽지 못한 벤치마크 칸: '{cell}'")
    keys = [(one["route"], one["period"]) for one in found]
    if len(set(keys)) != len(keys) or (len(found) > 1 and ("", 0) in keys):
        raise Unreadable(f"표시가 같은 값이 둘이거나 표시 없는 값이 섞임: {cell}")
    return found


def _sectioned(rows):
    """부문 이름만 있는 행을 만나면 그 뒤의 행에 부문을 붙여 돌려준다: (부문, 행)."""
    sector = None
    for row in rows:
        if row[0] and not any(row[1:]):
            name = SECTORS.get(row[0].strip().lower())
            if not name:
                raise Unreadable(f"모르는 부문 이름: {row[0]}")
            sector = name
            continue
        if sector is None:
            raise Unreadable(f"부문 이름보다 먼저 나온 행: {row[0]}")
        yield sector, row


def _lines(path):
    path = pathlib.Path(path)
    if not path.exists():
        raise Unreadable(f"받아 둔 표가 없음: {path}")
    return path.read_text(encoding="utf-8").split("\n")


def benchmarks(path=BENCHMARKS):
    """({"table": 표 번호, "rows": [품목...]}, 표 밖의 글 줄들). 품목은 {"code", "shown", "text", "sector", "a", "b"}이다."""
    lines = _lines(path)
    tables = [table for table in read_tables(lines) if table["rows"] and len(table["rows"][0]) == 4 and "Column A" in table["rows"][0][2]]
    if len(tables) != 1:
        raise Unreadable(f"벤치마크 표가 {len(tables)}개(하나여야 함)")
    table = tables[0]
    if "Column B" not in table["rows"][0][3] or "tCO2e/t" not in table["rows"][0][2]:
        raise Unreadable(f"벤치마크 표의 머리가 다름: {table['rows'][0]}")
    goods = []
    for sector, row in _sectioned(table["rows"][1:]):
        code = digits(row[0])
        if len(code) != 8 or not row[1]:
            raise Unreadable(f"벤치마크 표의 코드나 이름이 다름: {row[:2]}")
        goods.append({"code": code, "shown": row[0], "text": row[1], "sector": sector, "a": variants(row[2]), "b": variants(row[3])})
    codes = [good["code"] for good in goods]
    if len(set(codes)) != len(codes):
        raise Unreadable("벤치마크 표에 같은 코드가 두 번 나옴")
    start = next((index for index, line in enumerate(lines) if line.startswith("[표 밖의 글]")), None)
    end = next((index for index, line in enumerate(lines) if line.startswith(f"[표 {table['number']}]")), len(lines))
    notes = [line for line in lines[start + 1:end] if line.strip()] if start is not None else []
    return {"table": table["number"], "rows": goods}, notes


def _default_row(sector, row):
    code = digits(row[0])
    if len(code) not in (4, 6, 8, 10) or len(row) != 6:
        raise Unreadable(f"기본값 표의 행이 다름: {row}")
    direct, indirect, total = row[2], row[3], row[4]
    if total.lower() == "see below":
        state = "below"
    elif total == "-":
        state = "none"
    elif NUMBER.match(total) and NUMBER.match(direct) and (NUMBER.match(indirect) or indirect == "N/A"):
        state = "value"
    else:
        raise Unreadable(f"기본값 표의 값이 다름: {row}")
    routes = re.findall(r"\(([A-Z])\)", row[5])
    if re.sub(r"\([A-Z]\)|/|\s", "", row[5]):
        raise Unreadable(f"기본값 표의 경로 표시가 다름: {row[5]}")
    found = {"code": code, "shown": row[0], "text": row[1], "sector": sector, "state": state, "routes": routes}
    if state == "value":
        found.update({"direct": number(direct), "indirect": None if indirect == "N/A" else number(indirect), "total": number(total)})
    return found


def defaults(path=DEFAULTS):
    """{"korea": {"caption", "table", "rows"}, "other": {...}}. 두 표는 행의 차례와 코드가 같아야 한다(같은 품목 목록)."""
    tables = [table for table in read_tables(_lines(path)) if table["rows"] and "default value" in " ".join(table["rows"][0]).lower()]
    korea = [table for table in tables if KOREA.search(table["caption"]) and "democratic" not in table["caption"].lower()]
    other = [table for table in tables if OTHER.search(table["caption"])]
    if len(korea) != 1 or len(other) != 1:
        raise Unreadable(f"대한민국 표 {len(korea)}개, 그 밖의 나라 표 {len(other)}개(하나씩이어야 함)")
    found = {}
    for key, table in (("korea", korea[0]), ("other", other[0])):
        head = " | ".join(table["rows"][0]).lower()
        if not all(word in head for word in ("direct emissions", "indirect emissions", "total emissions", "production route", "tco2eq/tonne")):
            raise Unreadable(f"기본값 표의 머리가 다름: {table['rows'][0]}")
        found[key] = {"caption": table["caption"], "table": table["number"], "rows": [_default_row(sector, row) for sector, row in _sectioned(table["rows"][1:])]}
    if [row["code"] for row in found["korea"]["rows"]] != [row["code"] for row in found["other"]["rows"]]:
        raise Unreadable("대한민국 표와 그 밖의 나라 표의 품목 차례가 다름")
    return found
