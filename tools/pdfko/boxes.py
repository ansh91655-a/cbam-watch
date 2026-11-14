"""꼬리표가 없는 PDF를 쪽에 놓인 글 상자대로 읽는다(도안으로 된 한두 쪽짜리 안내 자료).

꼬리표(구조 트리)가 없는 PDF는 뽑아 낸 글에서 줄 단위로 문단을 짐작한다(tools.laws.pdf_blocks). 흐름도나 여러 칸으로 짠 안내 자료에서는
한 상자의 글이 줄마다 다른 문단으로 갈리고("If producer is in the" / "CBAM Registry") 읽는 차례가 뒤섞인다.
여기서는 pdftotext가 알려 주는 덩이(한 상자의 글)를 문단으로 삼고, 상자의 자리로 읽는 차례를 정한다.
어느 문서를 이렇게 읽을지는 sources/guides.json이 정한다(그 문서의 "units": "layout").

- 덩이 하나가 문단 하나다. 줄은 띄어 잇되, 붙임표로 끝난 줄과 너비가 모자라 꺾인 주소는 붙여 잇는다.
- 읽는 차례: 덩이들 사이의 빈 틈으로 쪽을 가르기를 되풀이한다. 위아래로 가를 틈이 있으면 위쪽부터 읽고, 좌우를 가르는 틈이 훨씬 넓으면
  왼쪽 칸을 다 읽은 뒤에 오른쪽 칸을 읽는다(칸 제목 다음에 그 칸의 글).
- 세로로 누운 글(쪽 가장자리에 적힌 발간 번호와 저작권 표시)은 싣지 않는다.
- 각주: 번호만 작게 적힌 덩이("1", "2")가 옆의 줄을 가리키면 그 줄을 그 번호의 각주로 읽는다(꼬리표로 읽은 각주와 같은 꼴: kind "note", label).
  글 안에 작게 올려 적은 번호는 앞 낱말에 붙이고, 그 번호의 각주가 있으면 "[1]"로 적는다. 각주가 없으면 글자 그대로 붙인다(CO2, m3).
"""
import re
import statistics

NUMBER = re.compile(r"^\d{1,2}$")
CLOSING = re.compile(r"^[.,;:?!)\]]+$")
CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")
ADDRESS = re.compile(r"https?://\S+$")                          # 주소로 끝난 글
ADDRESS_MORE = re.compile(r"^[\w.~!*'();:@&=+$,/?#%\[\]-]+$")   # 주소에 쓰는 글자만으로 된 낱말 하나
ADDRESS_SIGN = re.compile(r"[./_\-?=%]")
TALL = 1.5        # 낱말의 높이가 너비의 이 배를 넘으면 세로로 누운 글이다(석 자 이상인 낱말에서 본다)
SMALL = 0.7       # 줄의 보통 낱말보다 이만큼 작은 번호는 올리거나 내려 적은 글자다
NEAR_TOP = 3.0    # 각주 번호와 그 줄의 위쪽 자리가 이만큼 안에서 맞아야 한다(포인트)
NEAR_LEFT = 15.0  # 각주 번호의 오른쪽에서 줄이 시작하는 데까지의 틈
FULL = 0.12       # 줄의 오른쪽 끝이 덩이의 오른쪽 끝에서 너비의 이 비율 안에 있으면 꽉 찬 줄이다
ROW_GAP = 0.5     # 위아래를 가르는 틈으로 치는 가장 좁은 너비(포인트)
COLUMN_GAP = 6.0  # 좌우를 가르는 틈으로 치는 가장 좁은 너비
ROWS_FIRST = 3    # 좌우를 가르는 틈이 위아래를 가르는 틈의 이 배를 넘을 때에만 좌우로 먼저 가른다


def _vertical(line):
    return any(len(word["text"]) >= 3 and word["box"][3] - word["box"][1] > TALL * (word["box"][2] - word["box"][0]) for word in line["words"])


def _blocks(page):
    """쪽의 덩이들: [{"lines": [줄, …], "box": (x0, y0, x1, y1)}]. 세로로 누운 줄은 뺀다."""
    grouped = {}
    for line in page["lines"]:
        if not _vertical(line):
            grouped.setdefault(line["block"], []).append(line)
    found = []
    for lines in grouped.values():
        boxes = [line["box"] for line in lines]
        found.append({"lines": lines, "box": (min(box[0] for box in boxes), min(box[1] for box in boxes), max(box[2] for box in boxes), max(box[3] for box in boxes))})
    return found


def _label(blocks):
    """번호만 적힌 덩이의 번호를 그것이 가리키는 줄에 붙이고(줄에 "label"), 그 덩이는 뺀다. 가리키는 줄을 찾지 못한 번호는 문단으로 남긴다."""
    marks = [block for block in blocks if all(NUMBER.match(line["text"].strip()) for line in block["lines"])]
    rest = [block for block in blocks if not any(block is mark for mark in marks)]
    for mark in marks:
        left = []
        for number in mark["lines"]:
            host = next((line for block in rest for line in block["lines"] if "label" not in line
                         and abs(line["box"][1] - number["box"][1]) <= NEAR_TOP and 0 <= line["box"][0] - number["box"][2] <= NEAR_LEFT), None)
            if host is None:
                left.append(number)
            else:
                host["label"] = number["text"].strip()
        if left:
            rest.append({"lines": left, "box": mark["box"]})
    return rest


def _line(line, notes):
    """줄의 낱말을 글로 잇는다. 작게 적은 번호는 앞 낱말에 붙인다(올려 적었고 그 번호의 각주가 있으면 "[1]"로). 번호 뒤의 문장부호도 붙인다."""
    words = [(CONTROL.sub("", word["text"]), word["box"]) for word in line["words"]]
    words = [(text, box) for text, box in words if text]
    heights = [box[3] - box[1] for text, box in words if len(text) >= 2] or [box[3] - box[1] for _, box in words]
    usual = statistics.median(heights) if heights else 0
    out, after = [], False
    for text, box in words:
        if out and usual and NUMBER.match(text) and box[3] - box[1] <= SMALL * usual:
            raised = box[3] <= line["box"][3] - 0.2 * usual
            out[-1] += f"[{text}]" if raised and text in notes else text
            after = True
            continue
        if after and CLOSING.match(text):
            out[-1] += text
        else:
            out.append(text)
        after = False
    return " ".join(out)


def _join(lines, right, notes):
    """줄들을 문단 하나로 잇는다."""
    out, wrapped = "", False
    for line in lines:
        text = _line(line, notes)
        if not text:
            continue
        if not out:
            out = text
        elif out.endswith("-") and len(out.split()[-1]) > 1 and not ADDRESS.search(out):
            out += text                                   # non- / legislative
        elif wrapped and ADDRESS.search(out) and ADDRESS_MORE.match(text) and ADDRESS_SIGN.search(text):
            out += text                                   # 너비가 모자라 꺾인 주소
        else:
            out += " " + text
        width = right - line["box"][0]
        wrapped = width > 0 and right - line["box"][2] <= FULL * width
    return " ".join(out.split())


def _ordered(blocks):
    """읽는 차례로 늘어놓는다: 덩이들 사이의 빈 틈으로 쪽을 가르기를 되풀이한다.

    위아래를 가르는 틈(가로로 끝까지 비어 있는 띠)이 있으면 그 가운데 가장 넓은 곳에서 위와 아래로 가르고, 좌우를 가르는 틈(세로로 끝까지 비어 있는 띠)이
    그보다 훨씬 넓을 때에만 왼쪽과 오른쪽으로 먼저 가른다. 그래서 제목 아래에 놓인 여러 칸은 칸마다 위에서 아래로 읽고(칸 제목 다음에 그 칸의 글),
    흐름도처럼 상자가 줄지어 놓인 곳은 윗줄부터 왼쪽에서 오른쪽으로 읽는다. 가를 틈이 없으면 위에서 아래로, 왼쪽에서 오른쪽으로 놓는다.
    """
    if len(blocks) < 2:
        return list(blocks)
    widest = {}
    for axis, least in ((1, ROW_GAP), (0, COLUMN_GAP)):
        spans = sorted((block["box"][axis], block["box"][axis + 2]) for block in blocks)
        reach = spans[0][1]
        for begin, finish in spans[1:]:
            if begin - reach >= least and begin - reach > widest.get(axis, (0, 0))[0]:
                widest[axis] = (begin - reach, (begin + reach) / 2)
            reach = max(reach, finish)
    if not widest:
        return sorted(blocks, key=lambda block: (block["box"][1], block["box"][0]))
    axis = 0 if 0 in widest and (1 not in widest or widest[0][0] > ROWS_FIRST * widest[1][0]) else 1
    at = widest[axis][1]
    return _ordered([block for block in blocks if block["box"][axis + 2] <= at]) + _ordered([block for block in blocks if block["box"][axis + 2] > at])


def units(pages):
    """쪽들(tools.pdfko.geometry.read)에서 단위들: [{"kind": "p"|"note", "text", "page", "box"}]. 각주에는 "label"이 붙는다."""
    found = []
    for number, page in enumerate(pages):
        blocks = _label(_blocks(page))
        notes = {line["label"] for block in blocks for line in block["lines"] if "label" in line}
        for block in _ordered(blocks):
            right = block["box"][2]
            plain, note = [], None            # 각주가 시작되기 전의 줄들, 지금 모으는 각주
            pieces = []
            for line in block["lines"]:
                if "label" in line:
                    note = {"label": line["label"], "lines": [line]}
                    pieces.append(note)
                elif note is not None:
                    note["lines"].append(line)      # 각주가 다음 줄로 이어진 것
                else:
                    plain.append(line)
            if plain:
                text = _join(plain, right, notes)
                if text:
                    found.append({"kind": "p", "text": text, "page": number + 1, "box": list(block["box"])})
            for piece in pieces:
                text = _join(piece["lines"], right, notes)
                if text:
                    box = [min(line["box"][0] for line in piece["lines"]), min(line["box"][1] for line in piece["lines"]),
                           max(line["box"][2] for line in piece["lines"]), max(line["box"][3] for line in piece["lines"])]
                    found.append({"kind": "note", "label": piece["label"], "text": text, "page": number + 1, "box": box})
    return found
