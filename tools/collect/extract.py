"""출처 화면에서 '새로 보일 수 있는 것'을 뽑는다: 링크, 표의 행, 날짜로 시작하는 소식, 문장.

출처 설정(sources/registry.json)의 뜻
- watch: 볼 것의 목록(links, rows, dated, lines)
- filter: 참이면 핵심어가 든 것만 본다
- documents: 참이면 내려받기 문서 링크는 원문 대장(tools/originals)이 맡으므로 여기서는 빼고 본다
- skipTables: 머리 행에 이 글자가 든 표는 보지 않는다(예: 면담 기록처럼 소식이 아닌 표)
"""
import hashlib
import re

from tools.common.htmltext import parse_tables, squeeze

LETTERS = re.compile(r"[A-Za-z가-힣À-ÿ]")
MAX_TEXT = 300
# 날짜만 적힌 줄. 소식 목록에서 항목의 머리에 온다(예: 22Oct2026, 22 October 2026, 2026-10-22, 2026.10.22).
DATE_LINE = re.compile(r"^(\d{1,2}\s?[A-Z][a-z]{2,8}\.?\s?\d{4}|\d{4}[-./]\s?\d{1,2}[-./]\s?\d{1,2}\.?)$")
# 내려받기 카드의 줄(예: "Download (430.01 KB - HTML)", "(430.58 KB - HTML)"). 소식이 아니라 문서 목록이다.
DOWNLOAD_CARD = re.compile(r"^(Download\s*\(|\(\s*\d[\d.,]*\s*[KMG]B\b|\((HTML|PDF|ZIP|XLSX|DOCX)\))", re.I)
DOCUMENT_LINK = "/document/download/"


def _key(prefix, text):
    return prefix + hashlib.sha1(text.encode("utf-8")).hexdigest()[:16]


def _letters(text):
    return len(LETTERS.findall(text))


def _matches(text, keywords):
    lowered = text.lower()
    return any(keyword.lower() in lowered for keyword in keywords)


def _links(source, links, keywords):
    for url, text in links:
        if _letters(text) < 6:
            continue
        if source.get("documents") and DOCUMENT_LINK in url:
            continue
        if source.get("filter") and not _matches(text + " " + url, keywords):
            continue
        yield {"key": "u:" + url, "kind": "link", "text": text[:MAX_TEXT], "url": url}


def _rows(source, tables, keywords):
    skip_marks = [mark.lower() for mark in source.get("skipTables", [])]
    for table in tables:
        head = " | ".join(table["head"] or []).lower()
        if any(mark in head for mark in skip_marks):
            continue
        for cells in table["rows"]:
            joined = squeeze(" | ".join(cells))
            if len([cell for cell in cells if cell]) < 2 or _letters(joined) < 4:
                continue
            if source.get("filter") and not _matches(joined, keywords):
                continue
            yield {"key": _key("r:", joined), "kind": "row", "text": joined[:MAX_TEXT * 2], "url": source["url"], "cells": cells[:12]}


def _dated(source, lines, keywords):
    """날짜 줄 다음의 첫 줄을 제목으로, 그다음 줄들을 본문으로 묶어 한 항목으로 만든다."""
    index = 0
    while index < len(lines):
        if not DATE_LINE.match(lines[index]):
            index += 1
            continue
        date = lines[index]
        body = []
        index += 1
        while index < len(lines) and not DATE_LINE.match(lines[index]) and len(body) < 3:
            body.append(lines[index])
            index += 1
        if not body or _letters(body[0]) < 6:
            continue
        if any(DOWNLOAD_CARD.match(line) for line in body[:2]):
            continue  # 문서 내려받기 카드
        if source.get("filter") and not _matches(" ".join(body), keywords):
            continue
        title = body[0]
        detail = " ".join(body[1:])[:MAX_TEXT] if source.get("tier") == "A" else ""
        text = squeeze(f"{date} | {title}" + (f" | {detail}" if detail else ""))[:MAX_TEXT * 2]
        yield {"key": _key("d:", date + "|" + title), "kind": "dated", "text": text, "url": source["url"]}


def _lines(source, lines, link_texts, keywords):
    min_line = int(source.get("minLine", 30))
    for line in lines:
        if len(line) < min_line or _letters(line) < max(8, min_line // 2):
            continue
        if line in link_texts:
            continue  # 링크로 이미 잡힌 글자
        if source.get("filter") and not _matches(line, keywords):
            continue
        yield {"key": _key("l:", line), "kind": "line", "text": line[:MAX_TEXT], "url": source["url"]}


def entries(source, html, keywords):
    """출처 설정에 따라 항목 목록을 만든다. 항목은 {key, kind, text, url}이다."""
    links, lines, tables = parse_tables(html, source["url"])
    watch = source.get("watch", [])
    found = {}
    if "links" in watch:
        found.update((entry["key"], entry) for entry in _links(source, links, keywords))
    if "rows" in watch:
        found.update((entry["key"], entry) for entry in _rows(source, tables, keywords))
    if "dated" in watch:
        found.update((entry["key"], entry) for entry in _dated(source, lines, keywords))
    if "lines" in watch:
        link_texts = {text for _, text in links} if "links" in watch else set()
        found.update((entry["key"], entry) for entry in _lines(source, lines, link_texts, keywords))
    counts = {"links": len(links), "lines": len(lines), "rows": sum(len(table["rows"]) for table in tables)}
    return list(found.values()), counts
