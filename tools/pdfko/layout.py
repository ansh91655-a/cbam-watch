"""번역을 앉힐 자리를 정한다: 원문 문단의 줄들을 칸으로 삼아 국문을 흘려 넣는다.

- 같은 줄 자리에 같은 밑금으로 앉힌다. 길면 아래 빈 곳을 쓰고, 그래도 넘치면 글자를 조금씩 줄인다(SCALES).
- 한 줄짜리(제목, 목록, 표의 칸)는 오른쪽의 다른 글·괘선·그림에 닿기 전까지 넓혀 쓴다.
- 줄들이 문단 꼴이 아니면(도표의 이름표처럼 흩어진 글) 낱말이 엉뚱한 자리로 갈 수 있으므로 앉히지 않고 원문을 그대로 둔다.
좌표는 왼쪽 위가 원점이다.
"""

import collections
import re
import statistics

from tools.pdfko import fonts

SCALES = (1.0, 0.95, 0.9, 0.85, 0.8, 0.75, 0.7, 0.65, 0.6)
KOREAN = 1.0        # 원문 글자 크기에 견준 국문 글자 크기
SMALLEST = 5.0      # 이보다 작게는 줄이지 않는다(pt)
LEADING = 1.2       # 한 줄짜리 자리에서 줄을 더 놓을 때의 줄 사이(글자 크기의 배수)
DROP = 0.25         # 밑금 아래로 내려가는 깊이(글자 크기의 배수)
MARGIN = 36.0       # 쪽 가장자리에서 비워 두는 너비
SPLIT = 1.25        # 줄 사이가 여느 줄 사이의 이 배수를 넘으면 원문에서 문단이 갈린 곳으로 본다
NEAR = 0.12         # 문장 경계로 나눌 때 원문의 비율에서 벗어나도 되는 한도
SENTENCE = re.compile(r"(?<=[.!?。])\s+")
MARKER = re.compile(r"^(?:[•◦▪■●○‣·\-–—*o]|\(?[0-9a-zA-Z]{1,4}[.)]|\[\d+\]|\d+(?:\.\d+)*\.?)$")


def _mode(values):
    return collections.Counter(values).most_common(1)[0][0]


def hang(spots, pages, source, korean):
    """문단 머리의 글머리표나 번호가 원문과 번역에서 같으면 그 표는 원문 것을 그대로 두고, 나머지 글과 자리를 돌려준다."""
    head = source.split(" ", 1)[0]
    parts = korean.split(" ", 1)
    if not spots or len(parts) < 2 or not MARKER.match(head):
        return spots, korean
    if not any(char.isalnum() for char in head):
        # 기호뿐인 글머리표는 자리를 찾을 때 세지 않으므로 원문에 그대로 남는다: 번역에서만 뗀다
        return (spots, parts[1]) if not any(char.isalnum() for char in parts[0]) else (spots, korean)
    if parts[0] != head:
        return spots, korean
    first = spots[0]
    words = pages[first["page"]]["lines"][first["line"]]["words"]
    inside = [word for word in words if first["box"][0] - 0.5 <= word["box"][0] and word["box"][2] <= first["box"][2] + 0.5]
    if not inside or inside[0]["text"] != head:
        return spots, korean
    if len(inside) == 1:
        return spots[1:], parts[1]
    rest = inside[1:]
    box = (min(w["box"][0] for w in rest), first["box"][1], max(w["box"][2] for w in rest), first["box"][3])
    return [dict(first, box=box, whole=False)] + spots[1:], parts[1]


def slot(number, box, marks, sheet):
    """글자들(marks: [(찍기 연산의 차례, 글자 차례, 글자)])이 놓인 줄 하나의 칸. 보이는 글자가 없거나 누운 글자면 (None, 까닭)."""
    marks = [mark for mark in marks if not sheet.shows[mark[0]]["hidden"]]
    inked = [mark for mark in marks if mark[2]["text"].strip()]
    if not inked or not sheet.plain or sum(1 for mark in inked if mark[2]["flat"]) * 2 < len(inked):
        return None, "글자를 찾지 못함"
    base = _mode(round(glyph["base"] * 2) / 2 for _, _, glyph in inked)
    size = _mode(round(glyph["size"] * 4) / 4 for _, _, glyph in inked)
    x0, top, x1, bottom = box
    return {
        "page": number, "x0": x0, "top": top, "x1": x1, "bottom": bottom, "base": base, "size": size, "apart": False,
        "marks": {(order, index) for order, index, _ in marks},
        "fonts": collections.Counter(sheet.shows[order]["font"] for order, _, _ in inked),
        "colors": collections.Counter(sheet.shows[order]["color"] for order, _, _ in inked),
    }, ""


def slots(spots, sheets):
    """자리마다 그 줄의 밑금과 크기, 글꼴, 빛깔을 읽어 줄 칸으로 만든다. 돌려주는 것은 (줄 칸들, "") 또는 (None, 까닭)."""
    out = []
    for spot in spots:
        sheet = sheets[spot["page"]]
        marks = sheet.pick(spot["box"])
        made, why = slot(spot["page"], spot["box"], marks, sheet)
        if made is None:
            return None, why
        inked = [mark for mark in marks if mark[2]["text"].strip() and not sheet.shows[mark[0]]["hidden"]]
        for name, why in (("figure", "그림 안의 글자"), ("artifact", "머리말·꼬리말")):
            if sum(1 for order, _, _ in inked if sheet.shows[order].get(name)) * 2 > len(inked):
                return None, why
        last = out[-1] if out else None
        if last and last["page"] == made["page"] and abs(last["base"] - made["base"]) < 0.3 * made["size"]:
            gap = made["x0"] - last["x1"]
            fenced = any(last["x1"] < x < made["x0"] and y0 < made["base"] and y1 > made["base"] - made["size"] for x, y0, y1 in sheet.upright)
            if -made["size"] <= gap <= 2 * made["size"] or (0 < gap <= 10 * made["size"] and not fenced):     # 같은 줄이 둘로 읽힌 것(양쪽 맞춤의 넓은 낱말 사이): 하나로 잇는다
                last["x1"], last["top"], last["bottom"] = max(last["x1"], made["x1"]), min(last["top"], made["top"]), max(last["bottom"], made["bottom"])
                last["marks"] |= made["marks"]
                last["fonts"] += made["fonts"]
                last["colors"] += made["colors"]
                continue
            made["apart"] = True                          # 같은 줄의 떨어진 칸: 문단 꼴이 아니다
        out.append(made)
    for made in out:
        _sweep(made, sheets[made["page"]])
    return (out, "") if out else (None, "글자를 찾지 못함")


def _sweep(slot, sheet):
    """줄 칸에 딸린 기호도 함께 지우게 한다: 토막 사이의 것과, 줄 끝에 따로 떨어진 기호(&, +, – 따위).

    줄 끝의 기호는 바로 뒤에 글이 붙어 있으면(옆 칸의 글머리표) 건드리지 않고, 괘선을 넘거나 멀리 떨어진 것도 건드리지 않는다.
    """
    size = slot["size"]
    band = [
        mark for mark in sorted(sheet.pick((slot["x0"], slot["top"], sheet.width, slot["bottom"])), key=lambda mark: mark[2]["x"])
        if not sheet.shows[mark[0]]["hidden"] and abs(mark[2]["base"] - slot["base"]) <= 0.5 * size
    ]
    slot["marks"].update((order, index) for order, index, glyph in band if glyph["x"] <= slot["x1"] + 0.5)
    run, edge = [], slot["x1"]
    for order, index, glyph in band:
        if glyph["x"] <= slot["x1"] + 0.5 or not glyph["text"].strip():
            continue
        if any(char.isalnum() for char in glyph["text"]):
            if run and glyph["x0"] - edge <= 1.5 * size:
                run = []
            break
        fenced = any(edge < x < glyph["x"] and y0 < slot["base"] and y1 > slot["base"] - size for x, y0, y1 in sheet.upright)
        if fenced or glyph["x0"] - edge > 12 * size:
            break
        run.append((order, index))
        edge = glyph["x1"]
    slot["marks"].update(run)


def areas(lines):
    """이어진 줄들을 한 자리로 묶는다(쪽이 바뀌거나, 위로 올라가거나, 멀리 떨어지면 새 자리).

    한 자리 안에서 줄 사이가 유난히 넓은 곳은 원문에서 문단이 갈린 곳이다(글에서는 한 문단으로 읽혔다). 거기서 자리를 나누고 "stack"으로 표시한다.
    """
    out = []
    for slot in lines:
        last = out[-1][-1] if out else None
        step = slot["base"] - last["base"] if last else 0
        if last and last["page"] == slot["page"] and not slot["apart"] and 0.3 * last["size"] < step < 2.6 * last["size"]:
            out[-1].append(slot)
        elif last and last["page"] == slot["page"] and not slot["apart"] and step > 0 and abs(slot["x0"] - out[-1][-1]["x0"]) <= 4 and len(out[-1]) > 1:
            out.append([dict(slot, stack=True)])       # 같은 왼쪽 끝에서 한참 아래에 이어진 글(문단에 붙어 읽힌 그림 제목 따위)
        else:
            out.append([slot])
    split = []
    for group in out:
        steps = [b["base"] - a["base"] for a, b in zip(group, group[1:])]
        usual = min(steps) if steps else 0
        part = [group[0]]
        for slot, step in zip(group[1:], steps):
            if len(steps) > 1 and step > SPLIT * usual:
                split.append(part)
                part = [dict(slot, stack=True)]
            else:
                part.append(slot)
        split.append(part)
    return split


def _aligned(group):
    """자리 하나의 꼴: "block", "centre", 또는 None(줄들이 들쭉날쭉함)."""
    if len(group) == 1:
        return "block"
    steps = [b["base"] - a["base"] for a, b in zip(group, group[1:])]
    middle = statistics.median(steps)
    if any(abs(step - middle) > 0.3 * middle for step in steps):
        return None
    lefts = [slot["x0"] for slot in group[1:]]
    centres = [(slot["x0"] + slot["x1"]) / 2 for slot in group]
    ragged = max(slot["x0"] for slot in group) - min(slot["x0"] for slot in group) > 6
    if ragged and max(centres) - min(centres) <= 4:
        return "centre"
    return "block" if max(lefts) - min(lefts) <= 4 else None


def shape(groups):
    """자리들의 꼴: "block"(왼쪽을 맞춘 문단), "centre"(가운데를 맞춘 글), "loose"(흩어진 글)."""
    kinds = []
    for number, group in enumerate(groups):
        kind = _aligned(group)
        if kind is None or any(slot["apart"] for slot in group):
            return "loose"
        kinds.append(kind)
        if not number or groups[number - 1][0]["page"] != group[0]["page"]:
            continue
        before = groups[number - 1]
        if group[0].get("stack"):
            # 바로 아래에 이어진 문단: 왼쪽 끝(첫 줄은 들여쓸 수 있다)이나 가운데가 맞아야 한다
            edge = lambda part: statistics.median(slot["x0"] for slot in part[1:]) if len(part) > 1 else part[0]["x0"]
            centre = lambda part: statistics.mean((slot["x0"] + slot["x1"]) / 2 for slot in part)
            if not (-4 <= edge(group) - edge(before) <= (40 if len(group) == 1 else 4) or -40 <= edge(group) - edge(before) <= 4 and len(before) == 1 or abs(centre(group) - centre(before)) <= 4):
                return "loose"
        elif not (group[0]["base"] < before[0]["base"] and group[0]["x0"] > before[0]["x0"] + 20):
            return "loose"          # 같은 쪽에서 아래로 건너뛴 자리: 단이 바뀐 것이 아니다
    return "centre" if kinds and all(kind == "centre" for kind in kinds) else "block"


def frame(page):
    """쪽에서 글이 놓이는 왼쪽 끝과 오른쪽 끝."""
    boxes = [line["box"] for line in page["lines"]]
    if not boxes:
        return MARGIN, page["width"] - MARGIN
    return max(min(box[0] for box in boxes), MARGIN / 2), min(max(box[2] for box in boxes), page["width"] - MARGIN / 2)


def reach(group, page, sheet, others):
    """자리가 쓸 수 있는 왼쪽 끝, 오른쪽 끝, 아래 끝. others는 이 문단의 것이 아닌 글의 네모들이다."""
    size = group[0]["size"]
    left, natural = min(slot["x0"] for slot in group), max(slot["x1"] for slot in group)
    top, bottom = min(slot["top"] for slot in group), max(slot["bottom"] for slot in group)
    low, high = frame(page)
    gap = max(4.0, 0.5 * size)
    start, limit = min(low, left), max(high, natural)
    for x0, y0, x1, y1 in others:
        if y0 < bottom + 1 and y1 > top - 1:
            if x0 >= natural - 2:
                limit = min(limit, x0 - gap)
            elif x1 <= left + 2:
                start = max(start, x1 + gap)
    for x, y0, y1 in sheet.upright:
        if y0 < bottom - 1 and y1 > top + 1:
            if x >= natural - 1:
                limit = min(limit, x - 2)
            elif x <= left + 1:
                start = max(start, x + 2)
    for x0, y0, x1, y1 in sheet.images:
        if y0 < bottom and y1 > top:
            if x0 >= natural - 2:
                limit = min(limit, x0 - 3)
            elif x1 <= left + 2:
                start = max(start, x1 + 3)
    right = max(natural, limit) if len(group) == 1 else natural
    floor = page["height"] - MARGIN
    for x0, y0, x1, y1 in list(others) + list(sheet.images):
        if y0 >= bottom - 1 and x0 < right and x1 > left:
            floor = min(floor, y0 - 2)
    for y, x0, x1 in sheet.level:
        if y >= group[-1]["base"] + 1 and x0 < right and x1 > left:
            floor = min(floor, y - 1.5)
    return min(start, left), right, max(floor, bottom)


def _cells(zone, scale):
    """이 자리에서 줄을 놓을 칸들: [(x, 밑금, 너비)]. 가운데 맞춤이면 x는 None이고 너비는 쓸 수 있는 가장 긴 너비다."""
    group, size = zone["group"], zone["size"] * scale
    pitch = zone["pitch"] * scale
    rest = zone["rest"]
    if scale == 1.0:
        spots = [(slot["x0"], slot["base"]) for slot in group]
        base = group[-1]["base"] + pitch
    else:
        first = group[0]
        base = first["top"] + (first["base"] - first["top"]) * scale
        spots = [(first["x0"], base)]
        base += pitch
    while base + DROP * size <= zone["floor"] + 0.01 and len(spots) < 200:
        spots.append((rest, base))
        base += pitch
    if zone["mode"] == "centre":
        return [(None, base, zone["span"]) for _, base in spots]
    return [(x, base, zone["right"] - x) for x, base in spots]


def _wrap(words, cells, measure, space):
    """낱말을 칸에 차례로 채운다. 다 들어가면 [(칸, 글, 너비)], 남으면 None."""
    queue, lines = collections.deque(words), []
    for cell in cells:
        if not queue:
            break
        room, line, used = cell[2], [], 0.0
        while queue:
            word = queue[0]
            wide = measure(word)
            if used + (space if line else 0.0) + wide <= room + 0.01:
                used += (space if line else 0.0) + wide
                line.append(queue.popleft())
                continue
            if not line:                        # 낱말 하나가 칸보다 길다: 글자에서 끊는다
                cut = 1
                while cut < len(word) and measure(word[:cut + 1]) <= room:
                    cut += 1
                line.append(word[:cut])
                used = measure(word[:cut])
                queue[0] = word[cut:]
                if not queue[0]:
                    queue.popleft()
            break
        lines.append((cell, " ".join(line), used))
    return None if queue else lines


def _share(text, weights):
    """국문을 문장 경계에서 나누어 원문의 문단들에 견준 길이대로 나눈다. 알맞은 경계가 없으면 None."""
    sentences = SENTENCE.split(text)
    if len(sentences) < len(weights):
        return None
    total, whole = sum(weights), sum(len(sentence) for sentence in sentences)
    cuts, begin, passed, target = [], 0, 0, 0.0
    for weight in weights[:-1]:
        target += weight / total
        best, running = None, passed
        for index in range(begin, len(sentences) - 1):
            running += len(sentences[index])
            off = abs(running / whole - target)
            if best is None or off < best[0]:
                best = (off, index + 1, running)
        if best is None or best[0] > NEAR:
            return None
        cuts.append(best[1])
        begin, passed = best[1], best[2]
    edges = [0] + cuts + [len(sentences)]
    return [" ".join(sentences[a:b]) for a, b in zip(edges, edges[1:])]


def place(spots, pages, sheets, others, korean):
    """문단 하나를 앉힌다.

    돌려주는 것은 ((그릴 줄들, 지울 글자들, 줄인 비율), "") 또는 (None, 까닭).
    그릴 줄은 {"page", "x", "base", "size", "text", "kind", "heavy", "color"}, 지울 글자는 {쪽: {(찍기 연산의 차례, 글자 차례), …}}.
    """
    lines, why = slots(spots, sheets)
    if not lines:
        return None, why
    return settle(lines, pages, sheets, others, korean)


def settle(lines, pages, sheets, others, korean, tight=False):
    """줄 칸이 정해진 문단 하나를 앉힌다(place의 뒷부분). tight면 원래 글의 너비를 넘지 않는다(그림 안의 이름표)."""
    groups = areas(lines)
    mode = shape(groups)
    if mode == "loose":
        return None, "문단 꼴이 아님"
    names = sum((slot["fonts"] for slot in lines), collections.Counter())
    colors = sum((slot["colors"] for slot in lines), collections.Counter())
    name = names.most_common(1)[0][0]
    kind, heavy = fonts.family(name), fonts.bold(name)
    color = colors.most_common(1)[0][0] or (0.0, 0.0, 0.0)
    size = _mode(slot["size"] for slot in lines for _ in slot["marks"])
    text = fonts.tidy(korean, kind, heavy)
    if not text:
        return None, "찍을 글자가 없음"
    zones = []
    for group in groups:
        page = group[0]["page"]
        start, right, floor = reach(group, pages[page], sheets[page], others[page])
        if tight:
            start, right = min(slot["x0"] for slot in group), max(slot["x1"] for slot in group)
            floor = max(slot["bottom"] for slot in group)
        steps = [b["base"] - a["base"] for a, b in zip(group, group[1:])]
        axis = statistics.mean((slot["x0"] + slot["x1"]) / 2 for slot in group)
        zones.append({
            "group": group, "page": page, "size": size, "mode": mode, "right": right, "floor": floor,
            "pitch": statistics.median(steps) if steps else LEADING * size,
            "rest": statistics.median(slot["x0"] for slot in group[1:]) if len(group) > 1 else group[0]["x0"],
            "axis": axis, "span": max(max(slot["x1"] - slot["x0"] for slot in group), 2 * min(axis - start, right - axis)),
            "weight": sum(len(slot["marks"]) for slot in group),
        })
    for zone, after in zip(zones, zones[1:]):
        bottom = max(slot["bottom"] for slot in zone["group"])
        if after["page"] == zone["page"] and after["group"][0]["top"] > zone["group"][0]["top"]:
            zone["floor"] = min(zone["floor"], max(after["group"][0]["top"] - 1, bottom))
        else:
            zone["floor"] = bottom      # 다음 쪽이나 다음 단으로 이어지는 자리: 아래 여백으로 내려가지 않는다
    # 원문에서 문단이 갈린 곳(stack)마다 묶음을 나누고, 국문도 문장 경계에서 그만큼 나눈다
    runs = [[zones[0]]]
    for zone in zones[1:]:
        if zone["group"][0].get("stack"):
            runs.append([zone])
        else:
            runs[-1].append(zone)
    tries = [([zones], [text], SCALES)]
    if len(runs) > 1:
        texts = _share(text, [sum(zone["weight"] for zone in run) for run in runs])
        if texts:       # 문단마다 나누어 앉히되, 많이 줄여야 하면 나누지 않고 이어서 흘린다
            tries.insert(0, (runs, texts, [scale for scale in SCALES if scale >= 0.85]))
    for runs, texts, scales in tries:
        for scale in scales:
            actual = size * scale * KOREAN
            if actual < SMALLEST and scale < 1.0:
                break
            measure, space = (lambda word: fonts.width(word, kind, heavy, actual)), fonts.width(" ", kind, heavy, actual)
            drawn = []
            for run, part in zip(runs, texts):
                cells = [(zone, cell) for zone in run for cell in _cells(zone, scale)]
                fitted = _wrap(part.split(" "), [cell for _, cell in cells], measure, space)
                if fitted is None:
                    drawn = None
                    break
                for (zone, _), (cell, line, used) in zip(cells, fitted):
                    x = zone["axis"] - used / 2 if cell[0] is None else cell[0]
                    drawn.append({"page": zone["page"], "x": x, "base": cell[1], "size": actual, "text": line, "kind": kind, "heavy": heavy, "color": color})
            if drawn is None:
                continue
            gone = {}
            for slot in lines:
                gone.setdefault(slot["page"], set()).update(slot["marks"])
            return (drawn, gone, scale), ""
    return None, "자리가 모자람"
