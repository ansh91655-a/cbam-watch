"""HTML의 표를 칸의 자리를 살려 읽는다. 표준 라이브러리의 html.parser만 쓴다.

tools.common.htmltext는 보이는 글을 줄로 펴서 돌려주므로, 빈 칸이 있는 표에서는 값이 어느 열의 것인지 알 수 없다.
이 모듈은 표마다 행과 칸을 그대로 돌려준다.
- 빈 칸은 빈 글로 남긴다.
- 여러 행이나 열에 걸친 칸(rowspan, colspan)은 걸친 자리마다 같은 글을 채운다.
- 표 안에 든 표도 따로 표 하나로 돌려주고, 그 글은 바깥 표의 칸에도 넣는다. 화면을 짜려고 문서 전체를 감싼 표가 있더라도
  안쪽의 값 표를 잃지 않게 하려는 것이다. 쓰는 쪽이 머리 행을 보고 필요한 표를 고른다.
- 표마다 '표 바로 앞의 글'(caption)을 함께 돌려준다. 법령의 부속서에서는 나라 이름이나 표의 제목이 그 자리에 온다.
"""
import re
from html.parser import HTMLParser

SKIP_TAGS = {"script", "style", "noscript", "template", "svg"}
BLOCK_TAGS = {"p", "div", "li", "tr", "br", "h1", "h2", "h3", "h4", "h5", "h6", "section", "article", "table", "ul", "ol", "dd", "dt", "td", "th"}
SPAN_LIMIT = 400  # 걸친 수가 터무니없이 큰 값(잘못 적힌 것)이 표를 부풀리지 않게 하는 한도


def squeeze(text):
    return re.sub(r"\s+", " ", text or "").strip()


def _span(attrs, name):
    try:
        return max(1, min(SPAN_LIMIT, int(dict(attrs).get(name) or 1)))
    except ValueError:
        return 1


def expand(rows):
    """[(글, rowspan, colspan)]의 행들을 네모난 격자로 편다. 걸친 칸은 걸친 자리마다 같은 글을 채운다."""
    grid, pending = [], {}  # pending[열] = [더 채울 행 수, 글]
    for row in rows:
        out = []

        def carry():
            while len(out) in pending:
                column = len(out)
                left, text = pending[column]
                out.append(text)
                if left <= 1:
                    del pending[column]
                else:
                    pending[column] = [left - 1, text]

        for text, rowspan, colspan in row:
            carry()
            for _ in range(colspan):
                if rowspan > 1:
                    pending[len(out)] = [rowspan - 1, text]
                out.append(text)
        carry()
        grid.append(out)
    width = max((len(row) for row in grid), default=0)
    return [row + [""] * (width - len(row)) for row in grid]


class _Grids(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables = []   # 닫힌 차례가 아니라 열린 차례대로 둔다
        self._open = []    # 열려 있는 표들(바깥 것부터). 표마다 {"caption", "rows", "row", "cell"}
        self._skip = 0
        self._buffer = []  # 지금 쌓고 있는 글 한 덩이
        self._last = ""    # 마지막으로 끝난 글 한 덩이

    def _flush(self):
        text = squeeze("".join(self._buffer))
        if text:
            self._last = text
        self._buffer = []

    def handle_starttag(self, tag, attrs):
        if tag in SKIP_TAGS:
            self._skip += 1
            return
        if tag in BLOCK_TAGS:
            self._flush()
            for table in self._open:  # 칸 안에서 문단이 바뀌면 낱말이 붙지 않게 띄운다
                if table["cell"] is not None:
                    table["cell"][0].append(" ")
        if tag == "table":
            table = {"caption": self._last, "rows": [], "row": None, "cell": None}
            self.tables.append(table)
            self._open.append(table)
        elif tag == "tr" and self._open:
            self._open[-1]["row"] = []
        elif tag in ("td", "th") and self._open and self._open[-1]["row"] is not None:
            self._open[-1]["cell"] = [[], _span(attrs, "rowspan"), _span(attrs, "colspan")]

    def handle_endtag(self, tag):
        if tag in SKIP_TAGS:
            self._skip = max(0, self._skip - 1)
            return
        if tag in BLOCK_TAGS:
            self._flush()
        if not self._open:
            return
        table = self._open[-1]
        if tag in ("td", "th") and table["cell"] is not None and table["row"] is not None:
            pieces, rowspan, colspan = table["cell"]
            table["row"].append((squeeze("".join(pieces)), rowspan, colspan))
            table["cell"] = None
        elif tag == "tr" and table["row"] is not None:
            if table["row"]:
                table["rows"].append(table["row"])
            table["row"] = None
        elif tag == "table":
            self._open.pop()

    def handle_data(self, data):
        if self._skip:
            return
        self._buffer.append(data)
        for table in self._open:
            if table["cell"] is not None:
                table["cell"][0].append(data)


def grids(html):
    """[{"caption": 표 바로 앞의 글, "rows": [[칸 글, ...], ...]}]. 행이 없는 표는 뺀다."""
    reader = _Grids()
    try:
        reader.feed(html)
        reader.close()
    except Exception:
        pass
    found = []
    for table in reader.tables:
        rows = [row for row in expand(table["rows"]) if any(row)]
        if rows:
            found.append({"caption": table["caption"], "rows": rows})
    return found
