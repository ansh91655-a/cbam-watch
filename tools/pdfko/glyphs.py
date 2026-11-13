"""원문 PDF의 글자 하나하나: 자리, 글꼴, 크기, 빛깔, 그리고 그 글자를 찍은 연산자의 차례.

pdfminer로 쪽의 내용 흐름을 풀어 읽는다. 글자 찍기 연산자(Tj, TJ, ', ")마다 흐름 안에서의 차례를 적어 두어,
지울 때(erase) 같은 차례로 다시 찾아 고칠 수 있게 한다. 괘선과 그림의 자리도 함께 읽어 번역을 앉힐 때 넘지 않을 금으로 쓴다.
좌표는 geometry와 같게 왼쪽 위가 원점이다(단위 pt). 돌아간 쪽이나 원점이 어긋난 쪽은 "plain"을 False로 알린다.
"""

import bisect

from pdfminer import utils
from pdfminer.cmapdb import IdentityCMap, IdentityCMapByte
from pdfminer.pdfdevice import PDFTextDevice
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdffont import PDFCIDFont
from pdfminer.pdfinterp import PDFPageInterpreter, PDFResourceManager
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfparser import PDFParser
from pdfminer.pdftypes import dict_value
from pdfminer.psparser import PSLiteral

PAGE = "page"       # 쪽에 바로 놓인 내용 흐름의 이름. 양식(Form XObject) 안의 흐름은 그 객체 번호가 이름이다.
RULE = 6.0          # 금으로 삼는 괘선의 가장 짧은 길이
MID = 0.3           # 글자의 가운데 높이(밑금에서 글자 크기의 몇 배 위인가)
UNSURE = frozenset({"Separation", "DeviceN", "Indexed", "Pattern", "Lab"})


def _unit(font):
    """글자 하나가 차지하는 바이트 수. 글자마다 다를 수 있는 글꼴이면 None."""
    if not isinstance(font, PDFCIDFont):
        return 1
    if isinstance(font.cmap, IdentityCMapByte):
        return 1
    if isinstance(font.cmap, IdentityCMap):
        return 2
    return None


def _rgb(color, space):
    """채우는 빛깔을 (r, g, b)로. 알 수 없는 빛깔 공간이면 None."""
    if getattr(space, "name", "") in UNSURE:
        return None
    values = color if isinstance(color, (tuple, list)) else (color,)
    if not all(isinstance(value, (int, float)) for value in values):
        return None
    values = [min(1.0, max(0.0, float(value))) for value in values]
    if len(values) == 1:
        return (values[0],) * 3
    if len(values) == 3:
        return tuple(values)
    if len(values) == 4:
        cyan, magenta, yellow, black = values
        return ((1 - cyan) * (1 - black), (1 - magenta) * (1 - black), (1 - yellow) * (1 - black))
    return None


class _Recorder(PDFTextDevice):
    """쪽을 그리는 대신 글자와 괘선과 그림의 자리를 적는다."""

    def __init__(self, manager):
        super().__init__(manager)
        self.streams = []
        self.height = 0.0
        self.shows, self.images, self.upright, self.level, self.totals = [], [], [], [], {}
        self.tags = []
        self.uses = {}      # 문서 전체에서 흐름(쪽의 내용, 양식)마다 그려진 횟수
        self._show = None

    def start(self, height):
        self.height = height
        self.shows, self.images, self.upright, self.level, self.totals = [], [], [], [], {}
        self.tags = []
        self.ink = {}       # 내용 조각 번호마다 그 안에서 그린 그림과 선이 차지한 네모(그림 요소의 자리를 아는 데 쓴다)

    def _inked(self, x0, top, x1, bottom):
        mark = next((mark for _, mark in reversed(self.tags) if mark is not None), None)
        if mark is None:
            return
        old = self.ink.get(mark)
        self.ink[mark] = (x0, top, x1, bottom) if old is None else (min(old[0], x0), min(old[1], top), max(old[2], x1), max(old[3], bottom))

    def begin_tag(self, tag, props=None):
        mark = props.get("MCID") if isinstance(props, dict) else None
        self.tags.append((getattr(tag, "name", str(tag)), mark if isinstance(mark, int) else None))

    def end_tag(self):
        if self.tags:
            self.tags.pop()

    def render_string(self, textstate, seq, ncs, graphicstate):
        font = textstate.font
        name, count = self.streams[-1]
        size = textstate.fontsize
        self._show = show = {
            "stream": name, "index": count - 1,
            "font": getattr(font, "fontname", "") or "", "color": _rgb(graphicstate.ncolor, ncs),
            "hidden": textstate.render == 3, "unit": _unit(font), "counts": [], "glyphs": [],
            # 이 글자들이 든 내용 조각의 번호(구조 트리에서 무엇인지 찾는 열쇠)와, 쪽 꾸밈(머리말·꼬리말·쪽 번호)인지
            "mcid": next((mark for _, mark in reversed(self.tags) if mark is not None), None),
            "artifact": any(name == "Artifact" for name, _ in self.tags),
        }
        tight = textstate.charspace * 1000 / size if size else 0.0
        wide = 0.0 if font.is_multibyte() or not size else textstate.wordspace * 1000 / size
        self._steps = (tight, wide)
        super().render_string(textstate, seq, ncs, graphicstate)
        self.shows.append(show)
        self._show = None

    def render_string_horizontal(self, seq, matrix, pos, font, fontsize, scaling, charspace, wordspace, rise, dxscale, ncs, graphicstate):
        x, y = pos
        show = self._show
        tight, wide = self._steps
        for item in seq:
            if isinstance(item, (int, float)):
                x -= item * dxscale
                show["counts"].append(None)
                continue
            if not isinstance(item, bytes):
                show["counts"].append(None)
                continue
            count = 0
            for cid in font.decode(item):
                width = font.char_width(cid)
                advance = width * fontsize * scaling
                spot = utils.translate_matrix(matrix, (x, y))
                left = utils.apply_matrix_pt(spot, (0, rise))
                right = utils.apply_matrix_pt(spot, (advance, rise))
                middle = utils.apply_matrix_pt(spot, (advance / 2, rise + MID * fontsize))
                tall = fontsize * (spot[2] ** 2 + spot[3] ** 2) ** 0.5
                try:
                    text = font.to_unichr(cid)
                except Exception:
                    text = ""
                # 지울 때 이 글자 대신 넣을 걸음(TJ의 숫자): 글자 폭에 글자 사이와 낱말 사이를 더한 것
                step = -(width * 1000 + tight + (wide if cid == 32 else 0.0))
                show["glyphs"].append({
                    "x": middle[0], "y": self.height - middle[1], "x0": min(left[0], right[0]), "x1": max(left[0], right[0]),
                    "base": self.height - left[1], "size": tall, "text": text, "step": step,
                    "flat": abs(spot[1]) < 1e-3 and abs(spot[2]) < 1e-3 and spot[0] > 0 and spot[3] > 0,
                })
                x += advance + charspace
                if cid == 32 and wordspace:
                    x += wordspace
                count += 1
            show["counts"].append(count)
        return (x, y)

    def render_string_vertical(self, seq, matrix, pos, font, fontsize, scaling, charspace, wordspace, rise, dxscale, ncs, graphicstate):
        self._show["unit"] = None       # 세로쓰기는 건드리지 않는다
        self._show["counts"] = None
        return pos

    def paint_path(self, graphicstate, stroke, fill, evenodd, path):
        if not (stroke or fill) or self.ctm is None:
            return
        start = last = None
        for step in path:
            kind = step[0]
            if kind == "h":
                point = start
            elif len(step) >= 3:
                point = utils.apply_matrix_pt(self.ctm, (step[-2], step[-1]))
                self._inked(point[0], self.height - point[1], point[0], self.height - point[1])
            else:
                continue
            if kind == "m":
                start = last = point
                continue
            if kind in ("l", "h") and last is not None and point is not None:
                self._rule(last, point)
            last = point

    def _rule(self, one, two):
        (x0, y0), (x1, y1) = one, two
        if abs(x0 - x1) < 0.5 and abs(y0 - y1) >= RULE:
            self.upright.append((x0, self.height - max(y0, y1), self.height - min(y0, y1)))
        elif abs(y0 - y1) < 0.5 and abs(x0 - x1) >= RULE:
            self.level.append((self.height - y0, min(x0, x1), max(x0, x1)))

    def render_image(self, name, stream):
        if self.ctm is None:
            return
        corners = [utils.apply_matrix_pt(self.ctm, corner) for corner in ((0, 0), (1, 0), (0, 1), (1, 1))]
        xs, ys = [x for x, _ in corners], [y for _, y in corners]
        self.images.append((min(xs), self.height - max(ys), max(xs), self.height - min(ys)))
        self._inked(*self.images[-1])


class _Reader(PDFPageInterpreter):
    """내용 흐름마다 글자 찍기 연산자의 차례를 센다."""

    def render_contents(self, resources, streams, ctm=utils.MATRIX_IDENTITY):
        device = self.device
        name = PAGE if not device.streams else getattr(streams[0], "objid", None)
        device.streams.append([name, 0])
        device.uses[name] = device.uses.get(name, 0) + 1
        try:
            super().render_contents(resources, streams, ctm)
        finally:
            device.totals[name] = device.streams.pop()[1]

    def do_TJ(self, seq):
        self.device.streams[-1][1] += 1
        super().do_TJ(seq)

    def do_BDC(self, tag, props):
        if isinstance(props, PSLiteral):        # 이름으로 가리킨 속성은 자원에서 찾아 푼다
            try:
                props = dict_value(dict_value(self.resources.get("Properties"))[props.name])
            except Exception:
                props = {}
        self.device.begin_tag(tag, props)


class Sheet:
    """쪽 하나의 글자들. pick으로 네모 안의 글자를 고른다."""

    def __init__(self, width, height, plain, shows, images, upright, level, totals):
        self.width, self.height, self.plain = width, height, plain
        self.shows, self.images, self.upright, self.level = shows, images, upright, level
        self.totals = totals        # 흐름마다의 글자 찍기 연산자 수(지울 때 차례가 맞는지 견준다)
        self.once = frozenset()
        self.ink = {}
        marks = [(glyph["y"], glyph["x"], order, index) for order, show in enumerate(shows) for index, glyph in enumerate(show["glyphs"])]
        marks.sort()
        self._marks = marks
        self._ys = [mark[0] for mark in marks]

    def pick(self, box, slack=0.5):
        """네모(x0, 위, x1, 아래) 안에 가운데가 든 글자들: [(찍기 연산의 차례, 그 안에서의 차례, 글자)]."""
        x0, top, x1, bottom = box
        begin = bisect.bisect_left(self._ys, top - slack)
        end = bisect.bisect_right(self._ys, bottom + slack)
        return [
            (order, index, self.shows[order]["glyphs"][index])
            for _, x, order, index in self._marks[begin:end] if x0 - slack <= x <= x1 + slack
        ]


def read(path):
    """PDF 파일의 쪽마다 Sheet를 만든다."""
    sheets = []
    with open(path, "rb") as handle:
        document = PDFDocument(PDFParser(handle))
        manager = PDFResourceManager(caching=True)
        device = _Recorder(manager)
        reader = _Reader(manager, device)
        for page in PDFPage.create_pages(document):
            x0, y0, x1, y1 = (float(value) for value in page.mediabox)
            plain = not page.rotate and abs(x0) < 0.01 and abs(y0) < 0.01
            device.start(y1 - y0)
            reader.process_page(page)
            sheets.append(Sheet(x1 - x0, y1 - y0, plain, device.shows, device.images, device.upright, device.level, device.totals))
            sheets[-1].ink = device.ink
    once = {name for name, count in device.uses.items() if count == 1 and name != PAGE and name is not None}
    for sheet in sheets:
        sheet.once = once       # 문서에서 한 번만 그려지는 양식(Form XObject): 그 안의 글자는 고쳐도 다른 쪽이 달라지지 않는다
    return sheets
