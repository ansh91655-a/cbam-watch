"""출처 화면에서 '새로 보일 수 있는 것'을 뽑는다: 링크, 문장, 표의 행."""
import hashlib
import re

from tools.common.htmltext import parse, squeeze

LETTERS = re.compile(r"[A-Za-z가-힣À-ÿ]")
MAX_TEXT = 300


def _key(prefix, text):
    return prefix + hashlib.sha1(text.encode("utf-8")).hexdigest()[:16]


def _letters(text):
    return len(LETTERS.findall(text))


def _matches(text, keywords):
    lowered = text.lower()
    return any(keyword.lower() in lowered for keyword in keywords)


def entries(source, html, keywords):
    """출처 설정에 따라 항목 목록을 만든다. 항목은 {key, kind, text, url}이다."""
    links, lines, rows = parse(html, source["url"])
    watch = source.get("watch", [])
    use_filter = bool(source.get("filter"))
    min_line = int(source.get("minLine", 30))
    found = {}

    if "links" in watch:
        for url, text in links:
            if _letters(text) < 6:
                continue
            if use_filter and not _matches(text + " " + url, keywords):
                continue
            found["u:" + url] = {"key": "u:" + url, "kind": "link", "text": text[:MAX_TEXT], "url": url}

    if "rows" in watch:
        for cells in rows:
            cells = [cell for cell in cells]
            joined = squeeze(" | ".join(cells))
            if len([cell for cell in cells if cell]) < 2 or _letters(joined) < 4:
                continue
            if use_filter and not _matches(joined, keywords):
                continue
            key = _key("r:", joined)
            found[key] = {"key": key, "kind": "row", "text": joined[:MAX_TEXT * 2], "url": source["url"], "cells": cells[:12]}

    if "lines" in watch:
        link_texts = {text for _, text in links}
        for line in lines:
            if len(line) < min_line or _letters(line) < max(8, min_line // 2):
                continue
            if line in link_texts and "links" in watch:
                continue  # 링크로 이미 잡힌 글자
            if use_filter and not _matches(line, keywords):
                continue
            key = _key("l:", line)
            found[key] = {"key": key, "kind": "line", "text": line[:MAX_TEXT], "url": source["url"]}

    return list(found.values()), {"links": len(links), "lines": len(lines), "rows": len(rows)}
