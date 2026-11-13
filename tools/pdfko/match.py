"""규정 원문 화면의 문단이 원문 PDF의 어느 낱말들인지 찾는다. 받기와 쓰기는 하지 않는다.

문단은 pdftotext가 뽑은 줄을 이어 만든 것이라(tools.laws.pdf_blocks), 글자와 숫자만 남겨 견주면 낱말 여럿을 이은 것과 같다.
찾는 차례
1. 문단의 차례대로 줄을 훑으며 줄의 첫 낱말부터 이어 본다. 쪽이 넘어가는 자리에 낀 머리말·꼬리말·각주의 줄은 건너뛴다.
2. 줄의 가운데에서 시작하는 문단(번호 뒤에 제목이 적힌 줄, 한 줄에 칸이 여럿인 표)은 낱말의 자리에서 시작해 본다.
3. 줄의 차례가 뒤섞여 뽑힌 문단(번호가 따로 뽑힌 각주, 둘째 줄이 먼저 뽑힌 주소)은 가까운 줄들을 차례 없이 맞춰 본다.
제자리에서 찾지 못한 문단(자리를 옮겨 실은 각주)은 문서 전체에서 다시 찾는다.
"""
import re

SKIP = 30      # 문단 하나를 잇는 동안 건너뛸 수 있는 줄 수(쪽 끝의 각주와 꼬리말, 다음 쪽의 머리말)
LOOK = 500     # 제자리에서 찾을 때 앞으로 살피는 줄 수
NEAR = 14      # 차례 없이 맞출 때 살피는 앞뒤 줄 수
ANCHOR = 10    # 차례 없이 맞출 때 기준으로 삼는 줄의 가장 짧은 길이(글자와 숫자)


def squash(text):
    """견주기 좋게 소문자 글자와 숫자만 남긴다."""
    return re.sub(r"[^a-z0-9]+", "", str(text).lower())


def flatten(pages):
    """쪽들의 줄을 한 줄로 늘어놓는다: [{"page", "line", "box", "text", "squash", "words": [{"box", "text", "squash"}]}]"""
    lines = []
    for number, page in enumerate(pages):
        for index, line in enumerate(page["lines"]):
            words = [{"box": word["box"], "text": word["text"], "squash": squash(word["text"])} for word in line["words"]]
            lines.append({"page": number, "line": index, "box": line["box"], "text": line["text"], "words": words,
                          "squash": "".join(word["squash"] for word in words)})
    return lines


def _eat(line, rest, begin=0):
    """줄의 begin번째 낱말부터 rest를 채워 간다: (다 쓴 낱말의 끝 자리, 남은 글). 한 낱말도 맞지 않으면 None."""
    at = begin
    for word in line["words"][begin:]:
        if not word["squash"]:
            at += 1
            continue
        if not rest or not rest.startswith(word["squash"]):
            break
        rest = rest[len(word["squash"]):]
        at += 1
    ate = any(word["squash"] for word in line["words"][begin:at])
    return (at, rest) if ate else None


def _whole(line, rest):
    """줄을 처음부터 끝까지 쓸 수 있으면 남은 글, 아니면 None(문단의 마지막 줄은 가운데에서 끝나도 된다)."""
    eaten = _eat(line, rest)
    if eaten is None:
        return None
    end, left = eaten
    tail = any(word["squash"] for word in line["words"][end:])
    return None if tail and left else (end, left)


def _run(lines, target, start, used, begin=0):
    """start 줄의 begin번째 낱말에서 시작해 target을 다 채우는 자리들 [(줄의 차례, 낱말 시작, 낱말 끝)]. 채우지 못하면 None."""
    if start in used:
        return None
    eaten = _eat(lines[start], target, begin)
    if eaten is None:
        return None
    end, rest = eaten
    if rest and any(word["squash"] for word in lines[start]["words"][end:]):
        return None  # 첫 줄을 다 쓰지 못했는데 글이 남았다
    spans, at, skipped = [(start, begin, end)], start + 1, 0
    while rest:
        if at >= len(lines) or skipped > SKIP:
            return None
        got = None if at in used or not lines[at]["squash"] else _whole(lines[at], rest)
        if got:
            spans.append((at, 0, got[0]))
            rest, skipped = got[1], 0
        else:
            skipped += 1
        at += 1
    return spans


def _inside(lines, target, start, used):
    """start 줄의 가운데 낱말에서 시작하는 자리. 줄의 글에 target의 앞머리가 들어 있을 때만 본다."""
    line = lines[start]
    if start in used or target[:8] not in line["squash"]:
        return None
    for begin in range(1, len(line["words"])):
        if line["words"][begin]["squash"] and target.startswith(line["words"][begin]["squash"]):
            run = _run(lines, target, start, used, begin)
            if run:
                return run
    return None


def _scatter(lines, target, anchor, used):
    """anchor 줄의 앞뒤에서, 줄의 차례에 매이지 않고 target을 채우는 줄들. 긴 줄부터 맞춘다."""
    near = [index for index in range(max(0, anchor - NEAR), min(len(lines), anchor + NEAR + 1)) if index not in used and lines[index]["squash"]]
    rest, spans = target, []
    while rest:
        fits = [index for index in near if all(index != span[0] for span in spans) and rest.startswith(lines[index]["squash"])]
        if not fits:
            return None
        pick = max(fits, key=lambda index: len(lines[index]["squash"]))
        spans.append((pick, 0, len(lines[pick]["words"])))
        rest = rest[len(lines[pick]["squash"]):]
    return spans if any(index == anchor for index, _, _ in spans) else None


def _search(lines, target, span, used, index):
    for start in span:
        run = _run(lines, target, start, used)
        if run:
            return run
    for start in span:
        run = _inside(lines, target, start, used)
        if run:
            return run
    for anchor in span:
        piece = lines[anchor]["squash"]
        if len(piece) >= ANCHOR and anchor not in used and piece in target:
            run = _scatter(lines, target, anchor, used)
            if run:
                return run
    return None


def locate(pages, paragraphs):
    """문단마다 그 글이 놓인 자리를 찾는다.

    paragraphs는 [(열쇠, 원문, 앞에 붙는 번호)] (문서의 차례대로. 번호는 제목일 때만, 없으면 빈 글).
    돌려주는 것은 ({열쇠: [자리, …]}, 찾지 못한 열쇠들). 자리는 {"page", "line", "box": 그 줄에서 문단에 든 낱말들을 싼 네모, "whole": 줄 전체인가}.
    같은 글의 문단이 여러 번 나오면 나온 차례대로 다른 줄을 주고, 같은 열쇠의 자리는 따로따로 모은다: {열쇠: [[자리, …], [자리, …]]}.
    """
    lines = flatten(pages)
    found, lost, used, cursor = {}, [], set(), 0
    for block_key, text, label in paragraphs:
        target = squash(text)
        if not target:
            continue
        ahead = range(cursor, min(len(lines), cursor + LOOK))
        run = _search(lines, target, ahead, used, cursor)
        if run:
            cursor = min(index for index, _, _ in run) + 1
        else:
            run = _search(lines, target, range(len(lines)), used, 0)
        if not run:
            lost.append(block_key)
            continue
        spots = []
        for index, begin, end in run:
            line = lines[index]
            words = line["words"][begin:end]
            whole = begin == 0 and not any(word["squash"] for word in line["words"][end:])
            if whole:
                used.add(index)
            box = line["box"] if whole else (min(w["box"][0] for w in words), min(w["box"][1] for w in words), max(w["box"][2] for w in words), max(w["box"][3] for w in words))
            spots.append({"page": line["page"], "line": line["line"], "box": box, "whole": whole})
        found.setdefault(block_key, []).append(spots)
    return found, lost
