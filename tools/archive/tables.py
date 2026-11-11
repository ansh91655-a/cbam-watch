"""법령 부속서의 값 표를 칸의 자리를 살려 받아 둔다. 인증서 비용 추정기(tools/calc)의 자료가 여기에서 나온다.

'eu-acts' 단계는 부속서를 앞부분만 남기고, 남긴 것도 글을 줄로 편 것이라 빈 칸이 있는 표에서는 값의 열을 알 수 없다.
이 단계는 필요한 표만 골라 행과 칸을 그대로 적는다(읽는 법은 tools/common/rowtext.py).
- benchmarks: 무상할당 조정 이행규정 (EU) 2025/2620의 부속서 5(CBAM 벤치마크).
- defaults: 기본값 이행규정 (EU) 2025/2621의 부속서 I. 정정 규정 (EU) 2026/1740이 부속서 I을 통째로 갈아 끼웠으므로 그 글에서 받는다.
  나라마다 표가 하나씩 있어 모두 실으면 1만 행이 넘는다. 대한민국의 표와, 값이 없는 품목에 쓰라고 정해 둔
  '그 밖의 나라와 지역' 표만 남기고, 어떤 나라의 표가 있었는지는 이름만 적어 둔다.
받는 곳은 EU 출판국 자료 창구이고, EU 법령은 출처를 밝히고 다시 쓸 수 있다.
손으로 돌린다: 워크플로 '소급 수집'에서 mode = crawl, steps = eu-tables.
"""
import re

from tools.archive import fulltext
from tools.archive.store import save_index, save_text
from tools.common.htmlgrid import grids
from tools.common.rowtext import format_row

KOREA = re.compile(r"korea", re.I)
NOT_KOREA = re.compile(r"democratic", re.I)  # 조선민주주의인민공화국의 표가 따로 있을 때 섞이지 않게
OTHER = re.compile(r"other countries and territories", re.I)
HOW = ("[읽는 법] 표마다 '[표 번호] 표 바로 앞의 글' 줄 다음에 행을 한 줄씩 적었다. 칸은 ' | '로 나눴고 빈 칸은 비워 두었다. "
       "여러 행이나 열에 걸친 칸은 걸친 자리마다 같은 글을 적었다.")
MIN_COLUMNS, MIN_ROWS = 3, 2


def titled(table):
    """표의 제목이 표 안의 첫 행(모든 칸에 걸친 한 칸)으로 들어 있으면 그것을 caption으로 올리고 그 행을 뺀다."""
    rows = table["rows"]
    if len(rows) > 1 and rows[0][0] and len(set(rows[0])) == 1 and len(rows[0]) > 1:
        return {**table, "caption": rows[0][0], "rows": rows[1:]}
    return table


def data_tables(html):
    """값 표로 볼 만한 것만: 열이 셋 이상이고 행이 둘 이상인 표. 문서 전체를 감싼 표(한 칸에 글이 몰린 것)는 빠진다."""
    found = []
    for number, table in enumerate(grids(html), start=1):
        rows = table["rows"]
        if len(rows) >= MIN_ROWS and len(rows[0]) >= MIN_COLUMNS and max(len(cell) for row in rows for cell in row) < 4000:
            found.append({"number": number, **table})
    return found


def is_defaults(table):
    return any("default value" in cell.lower() for row in table["rows"][:2] for cell in row)


def pick_defaults(tables):
    """(남길 표, 나라 이름 목록, 사유). 대한민국의 표와 '그 밖의 나라와 지역' 표가 모두 있어야 한다."""
    country = [titled(table) for table in tables if is_defaults(titled(table))]
    names = list(dict.fromkeys(table["caption"] for table in country))
    korea = [table for table in country if KOREA.search(table["caption"]) and not NOT_KOREA.search(table["caption"])]
    other = [table for table in country if OTHER.search(table["caption"])]
    if not korea or not other:
        missing = "대한민국" if not korea else "그 밖의 나라와 지역"
        return [], names, f"{missing}의 표를 찾지 못함(표 {len(tables)}개, 표 앞의 글: {'; '.join(names)[:900]})"
    return korea + other, names, ""


def pick_benchmarks(tables):
    """이 법령에서 열이 셋 이상인 표는 부속서 5의 벤치마크 표뿐이다(본문의 목록은 두 칸짜리 표로 되어 있다). 모두 남긴다."""
    rows = sum(len(table["rows"]) for table in tables)
    if rows < 50:
        captions = "; ".join(f"{table['caption'][:40]}({len(table['rows'])}행, 머리: {' / '.join(table['rows'][0])[:80]})" for table in tables[:12])
        return [], f"벤치마크 표로 볼 만한 행이 {rows}개뿐임(받은 표: {captions})"
    return tables, ""


# (이름, CELEX 번호, 무엇인지)
TARGETS = [
    ("benchmarks", "32025R2620", "무상할당 조정 이행규정 (EU) 2025/2620 부속서 5의 CBAM 벤치마크 표"),
    ("defaults", "32026R1740", "기본값 이행규정 (EU) 2025/2621의 부속서 I(정정 규정 (EU) 2026/1740이 갈아 끼운 글) 가운데 대한민국과 '그 밖의 나라와 지역'의 표"),
]


def text_lines(tables):
    lines = []
    for table in tables:
        lines += ["", f"[표 {table['number']}] {table['caption']}"] + [format_row(row) for row in table["rows"]]
    return lines


def read(name, celex):
    """(줄 목록, 받은 곳, 표의 수, 행의 수, 사유)."""
    pages, why = fulltext.celex_pages(celex)
    if why:
        return [], "", 0, 0, why
    tables, offset = [], 0
    for _, _, html in pages:  # 파일이 여럿이면 표 번호를 이어서 매긴다
        found = data_tables(html)
        tables += [{**table, "number": table["number"] + offset} for table in found]
        offset += max((table["number"] for table in found), default=0)
    extra = []
    if name == "defaults":
        tables, names, why = pick_defaults(tables)
        extra = [f"[나라 목록] {'; '.join(names)}"]
    else:
        tables, why = pick_benchmarks(tables)
    if why:
        return [], "", 0, 0, why
    return extra + text_lines(tables), pages[0][1], len(tables), sum(len(table["rows"]) for table in tables), ""


def crawl():
    entries, failures = [], []
    for name, celex, what in TARGETS:
        try:
            lines, origin, tables, rows, why = read(name, celex)
        except Exception as problem:
            lines, origin, tables, rows, why = [], "", 0, 0, f"{type(problem).__name__}: {problem}"[:300]
        if why:
            failures.append(f"{name} {celex}: {why}")
            continue
        address = f"https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:{celex}"
        path = save_text(f"eu-tables/{name}.txt", [f"[주소] {address}", f"[받은 곳] {origin}", f"[무엇] {what}", HOW] + lines)
        entries.append({"name": name, "celex": celex, "title": what, "url": address, "tables": tables, "rows": rows, "textPath": path})
    save_index("eu-tables", entries, {"targets": len(TARGETS), "failures": failures})
    return {"stored": len(entries), "failures": failures}
