"""꼬리표(구조 트리)가 있는 PDF를 뜻 단위로 읽는다: 제목, 문단, 목록 항목, 표의 칸, 그림 제목, 각주.

글에서 줄 단위로 짐작하던 것(문단의 경계, 글머리표, 각주, 머리말·꼬리말·쪽 번호, 표의 칸 차례)을 PDF에 적힌 짜임에서 그대로 얻는다.
낱말과 띄어쓰기는 pdftotext가 읽은 낱말(geometry)을 쓰고, 낱말이 어느 요소의 것인지는 글자(glyphs)의 내용 조각 번호로 안다.

    python3 -m tools.pdfko.units 파일.pdf        # 단위를 JSON으로 찍는다
"""

import collections
import json
import pathlib
import re
import sys

import pikepdf

from tools.pdfko import geometry, glyphs, tags

INLINE = frozenset({"Span", "Link", "Reference", "Quote", "Annot", "Code", "Ruby", "Warichu", "NonStruct", "Private", "Form"})
HEADINGS = {"H": 1, "H1": 1, "H2": 2, "H3": 3, "H4": 4, "H5": 5, "H6": 6, "Title": 0}
SKIPPED = frozenset({"TOC", "TOCI", "Index"})         # 차례와 찾아보기는 싣지 않는다
NOTES = frozenset({"Note", "Footnote"})
CONTAINERS = frozenset({"Document", "DocumentFragment", "Part", "Art", "Sect", "Div", "Aside", "L", "Table", "TR", "THead", "TBody", "TFoot"})
LOOSE = "loose"     # 구조 트리에 없는 글자를 쪽마다 모아 두는 이름
OPEN, CLOSE = "\ue000", "\ue001"                       # 위첨자의 앞뒤에 잠시 붙여 두는 표시
MARKED = re.compile(f"([^\\s{OPEN}{CLOSE}]*){OPEN}([^{CLOSE}]*){CLOSE}")
RAISED = re.compile(r"^[0-9a-zA-Z*†‡]{1,3}$")          # 위첨자로 붙은 각주 번호의 꼴


def _words(pages, sheets, tree):
    """요소마다 그 안의 낱말을 모은다: {요소: [(쪽, 내용 차례, 줄, x0, x1, 글자 크기, 글, 위첨자인가)]}."""
    held = collections.defaultdict(list)
    for number, (page, sheet) in enumerate(zip(pages, sheets)):
        for row, line in enumerate(page["lines"]):
            marks = [mark for mark in sheet.pick(line["box"]) if mark[2]["text"].strip()]
            if not marks:
                continue
            sizes = collections.Counter(round(glyph["size"] * 2) / 2 for _, _, glyph in marks)
            usual = sizes.most_common(1)[0][0]
            floor = collections.Counter(round(glyph["base"]) for _, _, glyph in marks if round(glyph["size"] * 2) / 2 == usual).most_common(1)[0][0]
            for word in line["words"]:
                inside = [mark for mark in sheet.pick(word["box"]) if mark[2]["text"].strip()]
                if not inside:
                    continue
                owners = collections.Counter()
                for order, _, _ in inside:
                    show = sheet.shows[order]
                    if not show["artifact"] and show["mcid"] is not None:
                        owners[tree.where.get((number, show["mcid"]))] += 1
                owner = owners.most_common(1)[0][0] if owners else None
                if owner is None:
                    if not owners:      # 쪽 꾸밈이거나 꼬리표가 아예 없는 글자
                        continue
                    owner = (LOOSE, number)     # 내용 조각 번호는 있으나 구조 트리에 없는 글자: 도표의 이름표
                size = collections.Counter(round(glyph["size"] * 2) / 2 for _, _, glyph in inside).most_common(1)[0][0]
                base = min(glyph["base"] for _, _, glyph in inside)
                raised = size <= 0.8 * usual and base <= floor - 0.15 * usual and bool(RAISED.match(word["text"]))
                first = min((order, index) for order, index, _ in inside)
                held[owner].append((number, first, row, word["box"][0], word["box"][2], size, word["text"], raised, line["block"], word["box"]))
    return held


def _join(words):
    """낱말들을 글로 잇는다. 같은 줄에서 틈 없이 붙은 것(글자 크기가 달라 갈라진 낱말)과 줄 끝의 붙임표 뒤는 띄우지 않는다."""
    out, last = [], None
    for word in sorted(words, key=lambda word: (word[0], word[1])):
        page, _, row, x0, x1, size, text, raised = word[:8]
        glued = False
        if last is not None:
            same = last[0] == page and last[2] == row
            glued = (same and x0 - last[4] < 0.1 * max(size, last[5])) or (not same and last[6].endswith("-") and len(last[6]) > 1)
        if raised:      # 위첨자는 앞 낱말에 붙이고 표시해 둔다. 각주 번호인지는 문서를 다 읽은 뒤에 가린다(_settle)
            text, glued = f"{OPEN}{text}{CLOSE}", True
        if out and glued:
            out[-1] += text
        else:
            out.append(text)
        last = word
    return " ".join(out)


class _Reader:
    def __init__(self, tree, held):
        self.tree, self.held = tree, held
        self.kids = collections.defaultdict(list)
        for index, element in enumerate(tree.elements):
            self.kids[element["parent"]].append(index)
        self.units, self.tables = [], 0

    def kind(self, index):
        return self.tree.elements[index]["type"]

    def gather(self, index, stop=()):
        """요소와 그 안의 글줄 요소(Span, Link …)에 든 낱말들. stop에 든 종류의 자식은 넘어간다."""
        words = list(self.held.get(index, []))
        for kid in self.kids[index]:
            if self.kind(kid) in INLINE and self.kind(kid) not in stop:
                words += self.gather(kid, stop)
        return words

    def marks(self, index):
        out = list(self.tree.elements[index]["marks"])
        for kid in self.kids[index]:
            if self.kind(kid) in INLINE:
                out += self.marks(kid)
        return out

    def emit(self, kind, index, words, **more):
        if kind == "p" and len(words) > 1:
            first = min(words, key=lambda word: (word[0], word[1]))
            if first[7] and first[6].isdigit():     # 위첨자 번호로 시작하는 문단: 꼬리표가 없는 각주
                rest = [word for word in words if word is not first]
                kind, more = "note", dict(more, label=first[6])
                words = rest
        text = _join(words)
        if not text:
            return
        unit = {"kind": kind, "text": text, "page": min(word[0] for word in words) + 1, "marks": sorted(set(map(tuple, self.marks(index))))}
        unit.update({key: value for key, value in more.items() if value not in (None, "")})
        self.units.append(unit)

    def blocks(self, index):
        """요소 안의 덩이 요소들. 글줄 요소(Link 따위) 안에 든 것(각주)도 찾는다."""
        out = []
        for kid in self.kids[index]:
            if self.kind(kid) in INLINE:
                out += self.blocks(kid)
            else:
                out.append(kid)
        return out

    def walk(self, index, context):
        kind = self.kind(index)
        if kind in SKIPPED:
            return
        if kind in HEADINGS:
            self.emit("h", index, self.gather(index), level=HEADINGS[kind], **context)
        elif kind in NOTES:
            self.note(index, context)
            return
        elif kind == "LI":
            self.item(index, context)
            return
        elif kind == "Table":
            self.table(index, context)
            return
        elif kind == "Figure":
            self.labels(self.gather(index), context)
        elif kind == "Formula":
            self.emit("formula", index, self.gather(index), **context)
        elif kind in CONTAINERS:
            # 담는 요소에 바로 놓인 글줄 요소(Span 따위)는 하나하나가 문단이다
            if self.held.get(index):
                self.emit("p", index, list(self.held[index]), **context)
            for kid in self.kids[index]:
                if self.kind(kid) in INLINE:
                    self.emit("p", kid, self.gather(kid), **context)
                else:
                    self.walk(kid, context)
            return
        elif kind == "Caption":
            self.emit("caption", index, self.gather(index), **context)
        elif self.held.get(index) or any(self.kind(kid) in INLINE for kid in self.kids[index]):
            self.emit("p", index, self.gather(index), **context)
        for kid in self.blocks(index):
            self.walk(kid, context)

    def labels(self, words, context):
        """그림 안의 글자를 덩이(글상자)마다 이름표 하나로 낸다. 자리는 네모로 적는다(내용 조각 번호를 여러 이름표가 함께 쓰므로)."""
        groups = collections.defaultdict(list)
        for word in words:
            groups[(word[0], word[8])].append(word)
        for (page, _), group in sorted(groups.items(), key=lambda entry: min((word[0], word[1]) for word in entry[1])):
            text = _join(group)
            if text:
                boxes = [word[9] for word in group]
                box = [round(min(b[0] for b in boxes), 1), round(min(b[1] for b in boxes), 1), round(max(b[2] for b in boxes), 1), round(max(b[3] for b in boxes), 1)]
                self.units.append(dict(context, kind="figure", text=text, page=page + 1, box=box))

    def note(self, index, context):
        label = next((kid for kid in self.kids[index] if self.kind(kid) == "Lbl"), None)
        words = self.gather(index)
        for kid in self.blocks(index):
            if kid != label:
                words += self.gather(kid)
        words.sort(key=lambda word: (word[0], word[1]))
        mark = _join(self.gather(label)) if label is not None else ""
        if not mark and words and (words[0][7] or re.fullmatch(r"\(?\d{1,3}\)?", words[0][6])):
            mark, words = words[0][6], words[1:]
        self.emit("note", index, words, label=mark.strip("[]()"), **context)

    def item(self, index, context):
        label = "".join(_join(self.gather(kid)) for kid in self.kids[index] if self.kind(kid) == "Lbl")
        depth = context.get("depth", 0) + 1
        inner = dict(context, depth=depth)
        first = True
        for kid in self.kids[index]:
            if self.kind(kid) == "Lbl":
                continue
            # 항목의 몸(LBody)에 바로 든 글이 항목의 글이다. 그 안의 문단은 차례로 잇고, 안쪽 목록은 한 단 더 들어간다.
            direct = self.gather(kid) if self.kind(kid) not in ("L", "Table") else []
            if direct:
                self.emit("li", kid, direct, label=label if first else "", **inner)
                first = False
            for part in self.blocks(kid) if self.kind(kid) not in ("L", "Table") else [kid]:
                if self.kind(part) == "P" and first:
                    self.emit("li", part, self.gather(part), label=label, **inner)
                    first = False
                    for deeper in self.blocks(part):
                        self.walk(deeper, inner)
                else:
                    self.walk(part, inner)

    def reach(self, index):
        """요소 안(모든 깊이)의 낱말이 놓인 왼쪽 끝과 오른쪽 끝. 낱말이 없으면 None."""
        words, stack = [], [index]
        while stack:
            at = stack.pop()
            words += self.held.get(at, [])
            stack += self.kids[at]
        return (min(word[3] for word in words), max(word[4] for word in words)) if words else None

    def table(self, index, context):
        self.tables += 1
        lines, stack = [], list(reversed(self.kids[index]))
        while stack:
            kid = stack.pop()
            kind = self.kind(kid)
            if kind == "Caption":
                self.emit("caption", kid, self.gather(kid), **context)
            elif kind == "TR":
                lines.append([(cell, self.reach(cell)) for cell in self.kids[kid] if self.kind(cell) in ("TH", "TD")])
            else:
                stack.extend(reversed(self.kids[kid]))
        for row, placed in enumerate(_grid(lines), start=1):
            for cell, column, cols, rows in placed:
                inner = dict(context, table=self.tables, row=row, column=column, head=self.kind(cell) == "TH")
                if cols > 1 or rows > 1:
                    inner.update(cols=cols, rows=rows)
                direct = self.gather(cell)
                if direct:
                    self.emit("cell", cell, direct, **inner)
                for part in self.blocks(cell):
                    if self.kind(part) == "P":
                        self.emit("cell", part, self.gather(part), **inner)
                        for deeper in self.blocks(part):
                            self.walk(deeper, inner)
                    else:
                        self.walk(part, inner)


def _grid(lines):
    """표의 줄마다 칸의 자리를 정한다: [[(칸 요소, 칸 번호, 차지하는 칸 수, 차지하는 줄 수), …], …].

    PDF에는 합쳐진 칸이 한 번만 적히고 얼마나 합쳤는지는 적히지 않는다. 그래서 칸이 모자란 줄은 글의 가로 자리로 어느 칸인지 가린다:
    칸이 다 있는 줄들에서 칸마다의 왼쪽 끝을 얻고, 모자란 줄의 칸은 그 사이에 든 자리로 보낸다.
    비는 자리는 위 칸이 아래로 이어진 것(같은 줄의 오른쪽에 칸이 더 있을 때)이거나 왼쪽 칸이 옆으로 이어진 것으로 본다.
    """
    width = max((len(line) for line in lines), default=0)
    full = [line for line in lines if len(line) == width and all(box for _, box in line)]
    lefts = [min(line[column][1][0] for line in full) for column in range(width)] if full and width > 1 else []
    ordered = all(a < b for a, b in zip(lefts, lefts[1:]))
    placed = []
    for line in lines:
        columns = list(range(1, len(line) + 1))
        if lefts and ordered and len(line) < width and all(box for _, box in line):
            guess = [max((at for at, left in enumerate(lefts) if box[0] >= left - 6), default=0) + 1 for _, box in line]
            if all(a < b for a, b in zip(guess, guess[1:])):
                columns = guess
        placed.append([[cell, column, 1, 1] for (cell, _), column in zip(line, columns)])
    above = {}      # 칸 번호 → 그 칸을 차지한 위쪽 칸(아래로 늘릴 수 있는 것)
    for row in placed:
        taken = {entry[1]: entry for entry in row}
        last = max(taken, default=0)
        for column in range(1, width + 1):
            if column in taken:
                continue
            if column < last and column in above:
                above[column][3] += 1           # 위 칸이 이 줄까지 내려온다
                taken[column] = None
            elif column > last and last:
                taken[last][2] += 1             # 줄의 마지막 칸이 옆으로 이어진다
        for entry in row:
            for across in range(entry[2]):
                above[entry[1] + across] = entry
        for column, entry in list(above.items()):
            if column not in taken and not any(e[1] <= column < e[1] + e[2] for e in row):
                del above[column]               # 이 줄에서 이어지지 않은 칸은 더 내려오지 않는다
    return [[tuple(entry) for entry in row] for row in placed]


def read(path):
    """PDF의 단위들: {"pages": 쪽 수, "tagged": 꼬리표가 있는가, "units": [단위, …]}.

    단위는 {"kind": "h"|"p"|"li"|"cell"|"caption"|"note"|"figure"|"formula", "text", "page", "marks": [(쪽, 내용 조각 번호), …]}에
    제목의 "level", 목록과 각주의 "label", 목록의 "depth", 표의 "table"·"row"·"column"·"head"(합쳐진 칸이면 "cols"·"rows"도)가 붙는다.
    그림 안의 이름표("figure")는 "marks" 대신 "box"(x0, 위, x1, 아래)로 자리를 적는다.
    """
    pages = geometry.read(path)
    sheets = glyphs.read(path)
    with pikepdf.open(path) as pdf:
        tree = tags.read(pdf)
    if not tree.elements:
        return {"pages": len(pages), "tagged": False, "units": []}
    held = _words(pages, sheets, tree)
    reader = _Reader(tree, held)
    for root in reader.kids[None]:
        reader.walk(root, {})
    units = reader.units
    for number in range(len(pages)):
        words = held.get((LOOSE, number))
        if not words:
            continue
        reader.units = []
        reader.labels(words, {})
        after = max((index for index, unit in enumerate(units) if unit["page"] <= number + 1), default=-1)
        units[after + 1:after + 1] = reader.units
    return {"pages": len(pages), "tagged": True, "units": _settle(units)}


def _settle(units):
    """위첨자 표시를 푼다: 문서에 그 번호의 각주가 있고 앞 낱말이 단위나 수가 아니면 각주 번호("[4]")로, 아니면 그냥 글자로(m3, 10-6) 둔다."""
    labels = {unit.get("label") for unit in units if unit["kind"] == "note"}

    def mark(hit):
        before, raised = hit.group(1), hit.group(2)
        tail = re.search(r"[0-9A-Za-z]*$", before.rstrip("’'\")”.,;:)]")).group(0)
        power = not before or tail[-1:].isdigit() or (tail.isalpha() and len(tail) <= 2)
        return f"{before}[{raised}]" if raised in labels and not power else before + raised

    for unit in units:
        if OPEN in unit["text"]:
            unit["text"] = MARKED.sub(mark, unit["text"]).replace(OPEN, "").replace(CLOSE, "")
        if OPEN in unit.get("label", ""):
            unit["label"] = unit["label"].replace(OPEN, "").replace(CLOSE, "")
    return units


FOLDER = "originals/units"


def stored(text_path):
    """받아 둔 글(originals/text/<문서>/<판>.txt)에 짝이 되는 단위 파일의 자리."""
    text = pathlib.Path(text_path)
    return pathlib.Path(FOLDER) / text.parent.name / f"{text.stem}.json"


def write(pdf_path, text_path):
    """PDF 하나의 단위 파일을 만든다. 꼬리표가 없는 PDF도 그 사실을 적은 파일을 남긴다(다시 읽지 않게)."""
    found = read(pdf_path)
    target = stored(text_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(found, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    return found


def main(arguments):
    """--all: 싣는 문서 모두의 단위 파일을 다시 만든다. --missing: 없는 것만 만든다. 그 밖에는 파일 하나를 읽어 찍는다."""
    if arguments and arguments[0] in ("--all", "--missing"):
        state = json.loads(pathlib.Path("originals/state.json").read_text(encoding="utf-8"))
        made = 0
        for doc in (state.get("docs") or {}).values():
            for version in doc.get("versions", [])[-1:]:
                if not str(version.get("file", "")).lower().endswith(".pdf") or not version.get("text"):
                    continue
                if arguments[0] == "--missing" and stored(version["text"]).is_file():
                    continue
                try:
                    found = write(version["file"], version["text"])
                except Exception as error:      # 하나가 읽히지 않아도 나머지는 만든다(그 문서는 글에서 나눈 조각을 쓴다)
                    print(f"단위를 읽지 못함: {version['file']}: {error!r}"[:300])
                    continue
                made += 1
                print(f"{stored(version['text'])}: {len(found['units'])}개" + ("" if found["tagged"] else " (꼬리표 없음)"))
        print(f"단위 파일 {made}개를 만들었습니다.")
        return 0
    json.dump(read(arguments[0]), sys.stdout, ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
