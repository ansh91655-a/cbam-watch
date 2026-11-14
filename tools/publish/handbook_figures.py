"""CBAM 해설서의 그림(절의 figure)이 꼴을 갖췄는지 본다. tools.publish.handbook이 절을 검사할 때 부른다.

그림은 절의 글을 한눈에 보이게 한 것이다. 글에 없는 사실을 그림에만 적지 않는다(근거는 절의 basis가 맡는다).
수가 들어가는 그림(bars, split)과 날짜가 들어가는 그림(timeline)은 시험(tests/test_handbook.py)이 다른 참고 자료와 견준다.

그림의 종류와 꼴(모든 그림에 "kind", "title"(그림의 이름), 선택으로 "note"(그림 아래의 한 줄)와 "after"가 있다)
  after     그림을 놓는 자리: 그림 앞에 오는 문단의 수. 적지 않으면 문단을 모두 놓은 뒤에 그림을 놓는다.
            마지막 문단이 목록을 가리키는데('아래와 같은 …') 그림이 그 목록의 그림이 아닐 때, 그림을 그 문단 앞으로 올리는 데 쓴다.
  flow      차례나 흐름. {"numbered": true, "steps": [{"title", "text"?, "tag"?}], "links": ["화살표에 적는 말", …]?}
  timeline  때의 흐름. {"bands": [{"label", "text"?, "marks": [{"date": "2027-02-01" 또는 "when": "2027년 각 분기 말", "edge": "부터"|"까지"?, "label", "text"?}]}]}
  tiles     칸의 묶음. {"items": [{"icon"?, "title", "text"?, "href"?}]}
  matrix    넣는지 아닌지의 표. {"cols": ["칸 이름", …], "rows": [{"title", "cells": [true, false, …], "text"?}], "yes": "넣음", "no": "넣지 않음"}
  lanes     두 쪽이 하는 일과 넘겨주는 것. {"lanes": [{"title", "items": […]}, {"title", "items": […]}], "handover": "넘겨주는 것"}
  equation  셈의 틀. {"terms": [{"label", "text"?}], "ops": ["+", "−", "×", "÷", "="]}  ops는 terms보다 하나 적다
  bars      묶음별 막대. {"unit": "%", "groups": ["2026년", …], "series": [{"name", "values": [10, 20, 30]}]}  series는 둘까지
  split     전체를 몫으로 나눈 막대. {"unit": "tCO2e", "whole": {"label", "value"}, "parts": [{"label", "value"}, …]}  parts는 둘
  factor    CBAM 계수의 연도별 값(data/factor.json의 경로 하나). {"path": "current"}
"""
import re

KINDS = ("flow", "timeline", "tiles", "matrix", "lanes", "equation", "bars", "split", "factor")
OPS = ("+", "−", "×", "÷", "=")
EDGES = ("", "부터", "까지")
LIMITS = {"title": 40, "note": 200, "label": 44, "text": 110, "tag": 30, "cell": 30, "link": 6}
DATE = re.compile(r"\d{4}-\d{2}-\d{2}$")
HREF = re.compile(r"#[a-z][a-z0-9.\-]*$")


def _text(value, limit, name, found, needed=True):
    if value in (None, "") and not needed:
        return
    if not isinstance(value, str) or not value.strip():
        found.append(f"{name}이 빔")
    elif value != value.strip() or "\n" in value:
        found.append(f"{name}의 앞뒤에 빈칸이나 줄바꿈이 있음")
    elif len(value) > limit:
        found.append(f"{name}이 너무 김({len(value)}자, {limit}자까지)")


def _rows(value, name, low, high, found):
    if not isinstance(value, list) or not low <= len(value) <= high:
        found.append(f"{name}은 {low}~{high}개여야 함")
        return []
    return value


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _flow(figure, found):
    steps = _rows(figure.get("steps"), "steps", 2, 7, found)
    for at, step in enumerate(steps, 1):
        if not isinstance(step, dict):
            found.append(f"steps {at}의 꼴이 다름")
            continue
        _text(step.get("title"), LIMITS["label"], f"steps {at}의 title", found)
        _text(step.get("text"), LIMITS["text"], f"steps {at}의 text", found, needed=False)
        _text(step.get("tag"), LIMITS["tag"], f"steps {at}의 tag", found, needed=False)
    links = figure.get("links")
    if links is not None:
        if not isinstance(links, list) or len(links) != max(len(steps) - 1, 0):
            found.append("links는 steps보다 하나 적어야 함")
        else:
            for at, link in enumerate(links, 1):
                _text(link, LIMITS["link"], f"links {at}", found)


def _timeline(figure, found):
    bands = _rows(figure.get("bands"), "bands", 1, 4, found)
    marks = 0
    for at, band in enumerate(bands, 1):
        if not isinstance(band, dict):
            found.append(f"bands {at}의 꼴이 다름")
            continue
        _text(band.get("label"), LIMITS["label"], f"bands {at}의 label", found)
        _text(band.get("text"), LIMITS["text"], f"bands {at}의 text", found, needed=False)
        for number, mark in enumerate(band.get("marks") or [], 1):
            marks += 1
            name = f"bands {at}의 marks {number}"
            if not isinstance(mark, dict):
                found.append(f"{name}의 꼴이 다름")
                continue
            if bool(mark.get("date")) == bool(mark.get("when")):
                found.append(f"{name}에는 date와 when 가운데 하나만 적음")
            if mark.get("date") and not DATE.match(str(mark["date"])):
                found.append(f"{name}의 date는 2027-02-01 꼴이어야 함")
            _text(mark.get("when"), LIMITS["tag"], f"{name}의 when", found, needed=False)
            if mark.get("edge", "") not in EDGES:
                found.append(f"{name}의 edge는 '부터'나 '까지'여야 함")
            _text(mark.get("label"), LIMITS["label"], f"{name}의 label", found)
            _text(mark.get("text"), LIMITS["text"], f"{name}의 text", found, needed=False)
    if not marks:
        found.append("marks가 하나도 없음")


def _tiles(figure, found):
    for at, item in enumerate(_rows(figure.get("items"), "items", 2, 8, found), 1):
        if not isinstance(item, dict):
            found.append(f"items {at}의 꼴이 다름")
            continue
        _text(item.get("title"), LIMITS["label"], f"items {at}의 title", found)
        _text(item.get("text"), LIMITS["text"], f"items {at}의 text", found, needed=False)
        if item.get("href") and not HREF.match(str(item["href"])):
            found.append(f"items {at}의 href는 사이트 안의 주소(#…)여야 함")
        if item.get("icon") and not re.match(r"[a-z]+$", str(item["icon"])):
            found.append(f"items {at}의 icon 이름이 다름")


def _matrix(figure, found):
    cols = _rows(figure.get("cols"), "cols", 1, 4, found)
    for at, col in enumerate(cols, 1):
        _text(col, LIMITS["cell"], f"cols {at}", found)
    for at, row in enumerate(_rows(figure.get("rows"), "rows", 2, 10, found), 1):
        if not isinstance(row, dict):
            found.append(f"rows {at}의 꼴이 다름")
            continue
        _text(row.get("title"), LIMITS["label"], f"rows {at}의 title", found)
        _text(row.get("text"), LIMITS["text"], f"rows {at}의 text", found, needed=False)
        cells = row.get("cells")
        if not isinstance(cells, list) or len(cells) != len(cols) or not all(isinstance(cell, bool) for cell in cells):
            found.append(f"rows {at}의 cells는 cols와 같은 수의 true·false여야 함")
    _text(figure.get("yes"), LIMITS["cell"], "yes", found)
    _text(figure.get("no"), LIMITS["cell"], "no", found)


def _lanes(figure, found):
    for at, lane in enumerate(_rows(figure.get("lanes"), "lanes", 2, 2, found), 1):
        if not isinstance(lane, dict):
            found.append(f"lanes {at}의 꼴이 다름")
            continue
        _text(lane.get("title"), LIMITS["label"], f"lanes {at}의 title", found)
        for number, item in enumerate(_rows(lane.get("items"), f"lanes {at}의 items", 1, 6, found), 1):
            _text(item, LIMITS["text"], f"lanes {at}의 items {number}", found)
    _text(figure.get("handover"), LIMITS["text"], "handover", found)


def _equation(figure, found):
    terms = _rows(figure.get("terms"), "terms", 2, 6, found)
    for at, term in enumerate(terms, 1):
        if not isinstance(term, dict):
            found.append(f"terms {at}의 꼴이 다름")
            continue
        _text(term.get("label"), LIMITS["label"], f"terms {at}의 label", found)
        _text(term.get("text"), LIMITS["text"], f"terms {at}의 text", found, needed=False)
    ops = figure.get("ops")
    if not isinstance(ops, list) or len(ops) != max(len(terms) - 1, 0) or any(op not in OPS for op in ops):
        found.append(f"ops는 terms보다 하나 적어야 하고 {' '.join(OPS)} 가운데 하나여야 함")
    elif ops.count("=") != 1:
        found.append("ops에는 = 가 하나 있어야 함")


def _bars(figure, found):
    _text(figure.get("unit"), 10, "unit", found)
    groups = _rows(figure.get("groups"), "groups", 2, 8, found)
    for at, group in enumerate(groups, 1):
        _text(group, LIMITS["cell"], f"groups {at}", found)
    for at, series in enumerate(_rows(figure.get("series"), "series", 1, 2, found), 1):
        if not isinstance(series, dict):
            found.append(f"series {at}의 꼴이 다름")
            continue
        _text(series.get("name"), LIMITS["label"], f"series {at}의 name", found)
        values = series.get("values")
        if not isinstance(values, list) or len(values) != len(groups) or not all(_number(value) and value >= 0 for value in values):
            found.append(f"series {at}의 values는 groups와 같은 수의 0 이상인 수여야 함")


def _split(figure, found):
    _text(figure.get("unit"), 10, "unit", found)
    whole = figure.get("whole")
    if not isinstance(whole, dict) or not _number(whole.get("value")) or whole["value"] <= 0:
        found.append("whole의 value는 0보다 큰 수여야 함")
        return
    _text(whole.get("label"), LIMITS["label"], "whole의 label", found)
    parts = _rows(figure.get("parts"), "parts", 2, 2, found)
    for at, part in enumerate(parts, 1):
        if not isinstance(part, dict) or not _number(part.get("value")) or part["value"] < 0:
            found.append(f"parts {at}의 value는 0 이상인 수여야 함")
            return
        _text(part.get("label"), LIMITS["label"], f"parts {at}의 label", found)
    if parts and abs(sum(part["value"] for part in parts) - whole["value"]) > 0.0015:
        found.append("parts의 합이 whole과 다름")


def _factor(figure, found):
    if not re.match(r"[a-z]+$", str(figure.get("path") or "")):
        found.append("path에 data/factor.json의 경로 이름을 적음")


CHECKS = {"flow": _flow, "timeline": _timeline, "tiles": _tiles, "matrix": _matrix, "lanes": _lanes,
          "equation": _equation, "bars": _bars, "split": _split, "factor": _factor}


def problems(figure, paragraphs=None):
    """그림 하나의 꼴 문제들(글). 문제가 없으면 빈 목록. paragraphs: 그 절의 문단 수(주면 after가 그 안의 자리인지 본다)."""
    if not isinstance(figure, dict):
        return ["그림의 꼴이 다름"]
    found = []
    if figure.get("kind") not in KINDS:
        return [f"그림의 종류를 모름: {figure.get('kind')!r}"]
    _text(figure.get("title"), LIMITS["title"], "title", found)
    _text(figure.get("note"), LIMITS["note"], "note", found, needed=False)
    after = figure.get("after")
    if after is not None and (isinstance(after, bool) or not isinstance(after, int) or after < 1 or (paragraphs is not None and after >= paragraphs)):
        found.append("after는 그림 앞에 오는 문단의 수로, 1부터 문단 수보다 하나 적은 수까지 적음")
    CHECKS[figure["kind"]](figure, found)
    return found


def texts(figure):
    """그림에 적힌 모든 글(용어집이 쓰지 말라는 표기를 보는 데 쓴다)."""
    found = []

    def walk(value):
        if isinstance(value, str):
            found.append(value)
        elif isinstance(value, list):
            for one in value:
                walk(one)
        elif isinstance(value, dict):
            for name, one in value.items():
                if name not in ("kind", "icon", "href", "date", "path", "edge", "ops"):
                    walk(one)

    walk(figure if isinstance(figure, dict) else {})
    return found


def hrefs(figure):
    """그림 안의 사이트 주소들(가리키는 화면이 있는지는 handbook이 본다)."""
    return [str(item["href"]) for item in (figure.get("items") or []) if isinstance(item, dict) and item.get("href")] if isinstance(figure, dict) else []
