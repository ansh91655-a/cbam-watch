"""HTML에서 링크와 보이는 글자를 뽑는다. 표준 라이브러리의 html.parser만 쓴다."""
import re
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit, urlunsplit, parse_qsl, urlencode

SKIP_TAGS = {"script", "style", "noscript", "template", "svg"}
BLOCK_TAGS = {
    "p", "div", "li", "tr", "br", "h1", "h2", "h3", "h4", "h5", "h6", "section", "article",
    "header", "footer", "nav", "table", "ul", "ol", "dd", "dt", "td", "th", "main", "aside",
}
TRACKING = re.compile(r"^(utm_|fbclid$|gclid$|mc_cid$|mc_eid$)")


def squeeze(text):
    return re.sub(r"\s+", " ", text or "").strip()


def decode(body, content_type=""):
    """본문 바이트를 글자로 바꾼다. 머리글과 meta 태그에서 문자 집합을 찾는다."""
    match = re.search(r"charset=([\w-]+)", content_type or "", re.I)
    names = [match.group(1)] if match else []
    head = body[:3000].decode("ascii", "ignore")
    meta = re.search(r"charset=[\"']?([\w-]+)", head, re.I)
    if meta:
        names.append(meta.group(1))
    names += ["utf-8", "cp949"]
    for name in names:
        try:
            return body.decode(name)
        except Exception:
            continue
    return body.decode("utf-8", "replace")


def clean_url(base, href):
    """상대 주소를 절대 주소로 바꾸고, 조각과 추적용 매개변수와 세션 표시를 뗀다."""
    if not href:
        return ""
    href = href.strip()
    if href.startswith(("javascript:", "mailto:", "tel:", "#")):
        return ""
    absolute = urljoin(base, href)
    parts = urlsplit(absolute)
    if parts.scheme not in ("http", "https"):
        return ""
    path = re.sub(r";jsessionid=[^?#/]*", "", parts.path, flags=re.I)
    pairs = parse_qsl(parts.query, keep_blank_values=True)
    if any(TRACKING.match(k) for k, _ in pairs):
        query = urlencode([(k, v) for k, v in pairs if not TRACKING.match(k)])
    else:
        query = parts.query
    return urlunsplit((parts.scheme, parts.netloc.lower(), path, query, ""))


class _Collector(HTMLParser):
    """링크(주소, 글자)와 줄 단위의 보이는 글자를 한 번에 모은다."""

    def __init__(self, base):
        super().__init__(convert_charrefs=True)
        self.base = base
        self.links = []
        self.lines = []
        self._buffer = []
        self._skip = 0
        self._anchor = None
        self._anchor_text = []
        self.table_rows = []  # {"table": 표 번호, "head": 머리 행 여부, "cells": 칸 글자}
        self._table = -1
        self._row = None
        self._row_head = True
        self._cell = None

    def _flush(self):
        text = squeeze("".join(self._buffer))
        if text:
            self.lines.append(text)
        self._buffer = []

    def handle_starttag(self, tag, attrs):
        if tag in SKIP_TAGS:
            self._skip += 1
            return
        if tag in BLOCK_TAGS:
            self._flush()
        if tag == "table":
            self._table += 1
        elif tag == "tr":
            self._row = []
            self._row_head = True
        elif tag in ("td", "th") and self._row is not None:
            self._cell = []
            if tag == "td":
                self._row_head = False
        if tag == "a":
            href = dict(attrs).get("href", "")
            self._anchor = clean_url(self.base, href)
            self._anchor_text = []

    def handle_endtag(self, tag):
        if tag in SKIP_TAGS:
            self._skip = max(0, self._skip - 1)
            return
        if tag == "a" and self._anchor is not None:
            text = squeeze("".join(self._anchor_text))
            if self._anchor and text:
                self.links.append((self._anchor, text))
            self._anchor = None
        if tag in ("td", "th") and self._row is not None and self._cell is not None:
            self._row.append(squeeze("".join(self._cell)))
            self._cell = None
        elif tag == "tr" and self._row is not None:
            if any(self._row):
                self.table_rows.append({"table": self._table, "head": self._row_head, "cells": self._row})
            self._row = None
        if tag in BLOCK_TAGS:
            self._flush()

    def handle_data(self, data):
        if self._skip:
            return
        if self._cell is not None:
            self._cell.append(data)
        self._buffer.append(data)
        if self._anchor is not None:
            self._anchor_text.append(data)

    def close(self):
        super().close()
        self._flush()


def _collect(html, base):
    collector = _Collector(base)
    try:
        collector.feed(html)
        collector.close()
    except Exception:
        pass
    return collector


def _best_links(collector):
    best = {}
    for url, text in collector.links:
        if url not in best or len(text) > len(best[url]):
            best[url] = text
    return list(best.items())


def _group_tables(table_rows):
    """행을 표 단위로 묶는다. 머리 행은 th만으로 된 첫 행이고, 그런 행이 없으면 표의 첫 행이다."""
    tables = {}
    for row in table_rows:
        table = tables.setdefault(row["table"], {"head": None, "rows": []})
        if row["head"] and table["head"] is None and not table["rows"]:
            table["head"] = row["cells"]
        table["rows"].append(row["cells"])
    for table in tables.values():
        if table["head"] is None and table["rows"]:
            table["head"] = table["rows"][0]
    return list(tables.values())


def parse(html, base):
    """(링크 목록, 보이는 글의 줄 목록, 표의 행 목록)을 돌려준다.

    링크는 (주소, 글자) 쌍이고 주소가 같은 것은 긴 글자를 남긴다. 표의 행은 칸 글자의 목록이다.
    """
    collector = _collect(html, base)
    return _best_links(collector), collector.lines, [row["cells"] for row in collector.table_rows]


def parse_tables(html, base):
    """parse와 같되 표의 행을 표 단위로 묶어 돌려준다: (링크, 줄, [{"head": 머리 행, "rows": 행들}])."""
    collector = _collect(html, base)
    return _best_links(collector), collector.lines, _group_tables(collector.table_rows)
