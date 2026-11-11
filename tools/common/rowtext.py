"""표의 행을 글 한 줄로 적고 다시 읽는다. 빈 칸의 자리를 잃지 않는 꼴이다: '| 칸 | 칸 |  | 칸 |'.

받아 둔 법령 부속서의 표(collected/archive/pages/eu-tables/)를 쓰는 쪽과 읽는 쪽이 같은 규칙을 쓰게 하려고 한곳에 둔다.
"""
import re

TABLE = re.compile(r"^\[표 (\d+)\] ?(.*)$")


def format_row(cells):
    """칸 글의 목록을 한 줄로. 칸 안의 세로줄은 빗금으로 바꾼다(칸을 나누는 글자와 섞이지 않게)."""
    return "| " + " | ".join(str(cell).replace("|", "/").strip() for cell in cells) + " |"


def parse_row(line):
    """format_row가 쓴 줄을 칸 글의 목록으로. 그런 줄이 아니면 None."""
    line = line.rstrip("\n")
    if not (line.startswith("| ") and line.endswith(" |")) or len(line) < 4:
        return None
    return [cell.strip() for cell in line[2:-2].split(" | ")]


def read_tables(lines):
    """글의 줄들에서 표를 읽는다: [{"number": 번호, "caption": 표 바로 앞의 글, "rows": [[칸, ...], ...]}]."""
    tables, current = [], None
    for line in lines:
        head = TABLE.match(line.rstrip("\n"))
        if head:
            current = {"number": int(head.group(1)), "caption": head.group(2).strip(), "rows": []}
            tables.append(current)
            continue
        cells = parse_row(line)
        if cells is not None and current is not None:
            current["rows"].append(cells)
        elif line.strip() and current is not None and cells is None:
            current = None  # 표 밖의 글이 나오면 그 표는 끝난 것이다
    return tables
