"""기관 간 협상용 대조 문서(네 칸 표)의 PDF를 칸별 글로 편다.

EU 이사회 문서 등록부에 올라오는 대조 문서는 한 행에 집행위 제안, 유럽의회 수정안, 이사회 안, 합의안을 나란히 싣는다.
PDF에서 글만 뽑으면 칸이 뒤섞이므로, 낱말이 놓인 가로 자리로 칸을 가려 행마다 칸마다 한 줄로 적는다.
의회 칸과 이사회 칸은 집행위 제안과 견준 모습이다: 뺀 말에는 줄이 그어져 있고 더한 말은 굵은 기울임이다.
줄이 그어진 말은 지금의 글에서 빼고 따로 적는다(그대로 두면 "뺀 조항"을 "있는 조항"으로 읽게 된다).

    [행 34] Recital 21 (쪽 31)
    [집행위 34] (21) To facilitate the application ... Article 6 of the Paris Agreement.
    [의회 34] deleted
    [이사회 34] (21)
    [이사회 34 지움] To facilitate the application ... Article 6 of the Paris Agreement.
    [의회 204d 더함] ‘8a. Where unforeseeable, exceptional ...

이렇게 적어 두면 "유럽의회 칸에 이 말이 있다(또는 뺐다)"를 프로그램이 한 줄에서 확인할 수 있다.
pdfplumber가 필요하다(워크플로에서 따로 설치한다).
"""
import io
import re

# 낱말의 왼쪽 끝이 이 값 이상이면 그 칸이다(쪽의 너비 842pt 기준). 표의 칸 자리는 문서 전체에서 같다.
COLUMNS = [("집행위", 95.0), ("의회", 270.0), ("이사회", 445.0), ("합의안", 620.0)]
NUMBER_LEFT = 58.0      # 행 번호가 놓이는 자리의 왼쪽 끝
HEAD_BOTTOM = 70.0      # 이 위는 쪽마다 되풀이되는 칸 이름
FOOT_TOP = 532.0        # 이 아래는 쪽 번호와 문서 이름
LOCATOR_FONT = "Calibri"  # 행의 위치를 적은 줄(예: Article 1, first paragraph, point (21))의 글꼴
ROW_NUMBER = re.compile(r"^\d{1,4}[a-z]{0,2}$")
NAMES = [name for name, _ in COLUMNS]
ADDED_FONT = "BoldItalic"   # 더한 말의 글꼴
STRIKE_HEIGHT = 1.5         # 줄 긋기는 이보다 얇은 가로 막대로 그려진다
PARTS = ("", "더함", "지움")  # 지금의 글, 더한 말, 뺀 말


def struck(word, bars):
    """낱말의 가운데 높이를 가로 막대가 지나가면 줄이 그어진 말이다(밑줄은 아래쪽에 있으므로 걸리지 않는다)."""
    height = word["bottom"] - word["top"]
    low, high = word["top"] + height * 0.3, word["bottom"] - height * 0.25
    width = max(word["x1"] - word["x0"], 0.1)
    for bar in bars:
        if low <= bar["top"] <= high:
            overlap = min(word["x1"], bar["x1"]) - max(word["x0"], bar["x0"])
            if overlap / width >= 0.6:
                return True
    return False


def mark(words, rects):
    """낱말마다 줄이 그어졌는지(struck)와 더한 말인지(added)를 붙인다."""
    bars = [rect for rect in rects if rect["height"] <= STRIKE_HEIGHT and rect["x1"] - rect["x0"] > 2]
    for word in words:
        word["struck"] = struck(word, bars)
        word["added"] = ADDED_FONT in str(word.get("fontname", ""))
    return words


def column_of(x0):
    """낱말의 왼쪽 끝으로 칸을 가린다. 행 번호 자리는 '번호', 그 왼쪽은 ''."""
    for name, left in reversed(COLUMNS):
        if x0 >= left:
            return name
    return "번호" if x0 >= NUMBER_LEFT else ""


def lines_of(words, tolerance=2.5):
    """낱말을 위에서 아래로, 같은 높이끼리 묶는다."""
    rows = []
    for word in sorted(words, key=lambda item: (item["top"], item["x0"])):
        if rows and abs(rows[-1][0] - word["top"]) <= tolerance:
            rows[-1][1].append(word)
        else:
            rows.append([word["top"], [word]])
    return [sorted(group, key=lambda item: item["x0"]) for _, group in rows]


def rows_of(pages):
    """쪽마다의 낱말 목록에서 행을 만든다. 행은 {number, locator, cells{칸: 지금의 글}, added{칸: 더한 말}, removed{칸: 뺀 말}, page}."""
    rows = []
    current = None

    def blank(locator, page_number):
        return {"number": "", "locator": locator, "page": page_number,
                "cells": {name: "" for name in NAMES}, "added": {name: "" for name in NAMES}, "removed": {name: "" for name in NAMES}}

    def flush():
        if not current:
            return
        for key in ("cells", "added", "removed"):
            current[key] = {name: " ".join(text.split()) for name, text in current[key].items() if text.strip()}
        if current["number"] or current["cells"] or current["removed"]:
            rows.append(current)

    for page_number, words in pages:
        body = [word for word in words if HEAD_BOTTOM <= word["top"] <= FOOT_TOP]
        for line in lines_of(body):
            first = line[0]
            if first["x0"] < NUMBER_LEFT and LOCATOR_FONT in str(first.get("fontname", "")):
                flush()
                current = blank(" ".join(word["text"] for word in line), page_number)
                continue
            if current is None:
                current = blank("", page_number)
            for word in line:
                where = column_of(word["x0"])
                if where == "번호":
                    if ROW_NUMBER.match(word["text"]) and not current["number"]:
                        current["number"] = word["text"]
                    continue
                if not where:
                    continue
                if word.get("struck"):
                    current["removed"][where] += " " + word["text"]
                    continue
                current["cells"][where] += " " + word["text"]
                if word.get("added"):
                    current["added"][where] += " " + word["text"]
    flush()
    return rows


def text_lines(rows):
    """행들을 저장할 글의 줄로 바꾼다. 칸마다 지금의 글, 더한 말, 뺀 말을 따로 적는다."""
    lines = []
    for row in rows:
        number = row["number"] or "-"
        lines.append(f"[행 {number}] {row['locator']} (쪽 {row['page']})".rstrip())
        for name in NAMES:
            for key, tag in (("cells", ""), ("added", " 더함"), ("removed", " 지움")):
                text = row[key].get(name)
                if text:
                    lines.append(f"[{name} {number}{tag}] {text}")
    return lines


def read_pdf(body):
    """PDF 바이트에서 행을 읽는다."""
    import pdfplumber  # 워크플로에서 따로 설치한다
    pages = []
    with pdfplumber.open(io.BytesIO(body)) as document:
        for number, page in enumerate(document.pages, start=1):
            pages.append((number, mark(page.extract_words(extra_attrs=["fontname"]), page.rects)))
    return rows_of(pages)


def only_in(rows, name):
    """한 칸에만 글이 있는 행(그 기관이 새로 넣은 대목)."""
    return [row for row in rows if list(row["cells"]) == [name] and not row["removed"]]
