"""EU 집행위원회 안내 문서(PDF에서 뽑아 둔 글)를 읽기 좋은 조각으로 나눈다. 법령의 segment.parts와 같은 꼴을 돌려준다.

조각(part)은 표지(cover: 첫 제목 앞의 글), 절(section: 번호가 붙은 제목마다 하나), 부속서(appendix: "ANNEX A" 같은 제목마다 하나)다.
제목은 세 가지 꼴로 적혀 있다.
- 번호만 있는 줄 다음에 제목이 오는 것("2.3.3" / "Definition and explanation of …")
- 번호와 제목이 한 줄에 있는 것("3.1.1 Emissions monitoring", "2.4. How can the CBAM declaration be submitted …?", "4. METHODOLOGY FOR …")
- "ANNEX A"나 "ANNEX III – …" 다음에 제목이 오는 것

표의 칸이나 목록의 번호, 줄 머리에 온 본문의 수를 제목으로 잘못 보지 않도록 세 가지를 본다.
- 번호는 앞 제목의 번호 바로 다음이어야 한다(follows).
- 차례가 있는 문서에서는 차례에 적힌 번호여야 한다. 마디가 하나뿐인 번호("3")는 차례의 쪽 번호와 가릴 수 없으므로 제목이 차례의 어느 제목과 같아야 한다.
  차례가 싣지 않는 번호("2.3.3.1")는 제목의 꼴이 뚜렷하거나 제목이 차례의 어느 제목과 같을 때만 받는다.
- 제목 다음에 본문이 바로 이어지는 꼴(약한 꼴)은 제목이 차례의 제목과 같을 때만 받는다.
PDF에서 글이 뒤섞여 제목 줄을 찾지 못한 번호는 차례의 제목을 빌려 쓴다. 제목 줄이 번호 줄의 앞이나 조금 뒤로 밀려 있는 것도 차례의 제목으로 바로잡는다.

차례가 없는 문서는 꼴이 뚜렷한 제목만 받고, 짧은 줄에 적힌 여러 마디 번호의 제목("4.2.1 Co-ordinated responses")을 더 받는다.
마디가 하나인 번호는 처음 받은 제목과 같은 꼴(마침표가 있는가)일 때만 받는다(쪽 아래의 각주 번호를 제목으로 보지 않게).

문서마다 나누는 방식을 정할 수 있다(sources/guides.json의 outline).
- auto(기본): 위와 같이 나눈다.
- loose: 차례가 없는 문서에서 "1. Introduction"처럼 번호와 마침표 뒤에 제목이 오고 본문이 바로 이어지는 짧은 줄도 제목으로 받는다.
- none: 제목을 찾지 않고 글 전체를 조각 하나(본문)로 둔다. 도안으로 된 짧은 문서처럼 글의 차례가 뒤섞여 번호를 믿을 수 없는 것에 쓴다.

쓰는 법(살펴볼 때): python -m tools.laws.guide_segment <글 파일> [--blocks <조각 id>] [--outline auto|loose|none]
"""
import re
import sys

from tools.laws import pdf_blocks, pdf_pages

NUMBER_ONLY = re.compile(r"^(\d+(?:\.\d+){0,4})\.?$")
NUMBERED = re.compile(r"^(\d+(?:\.\d+){0,4})(?:(\.)\s*|\s+)(\S.*)$")
ANNEX = re.compile(r"^(ANNEX|Annex|APPENDIX|Appendix)\s+([IVXLC]+|[A-Z]|\d+)(?![A-Za-z0-9])\s*[:.–—-]?\s*(.*)$")
GLUED = re.compile(r"[A-Za-z]{30,}")                      # 띄어쓰기가 사라진 글(뽑을 때 깨진 줄)
TWO_SENTENCES = re.compile(r"[A-Za-z]{3,}\.\s?[A-Z]{2}")  # 대문자 제목 안에서 문장이 끝나고 다시 시작하는 곳
OUTLINES = ("auto", "loose", "none")
BODY_ID = "sec-body"  # 제목을 찾지 않는 문서(outline: none)의 하나뿐인 조각
BODY_LABEL = "본문"
TITLE_MAX = 220       # 제목의 글자 수
TITLE_LINES = 4       # 제목이 걸칠 수 있는 줄 수
QUESTION_MAX = 700    # 물음으로 된 제목(질의응답)의 글자 수
QUESTION_LINES = 8    # 물음으로 된 제목이 걸칠 수 있는 줄 수
ONE_LINE_MAX = 120    # 번호와 한 줄에 적힌 제목(물음도 대문자도 아닌 것)의 글자 수
SAME = 25             # 본문의 제목과 차례의 제목을 견줄 때 보는 앞머리의 글자 수
DISPLACED = 8         # 번호 줄의 앞뒤로 자리가 밀린 제목 줄을 찾는 줄 수
BLANK_AHEAD = 20      # 빌려 쓴 제목과 똑같은 줄을 찾아 지우는 줄 수(번호 줄의 뒤쪽)


def follows(previous, number):
    """제목 번호가 앞의 번호 바로 다음에 올 수 있는가. 2.3.3 다음에는 2.3.4, 2.4, 3, 2.3.3.1이 온다.

    앞의 제목 하나를 놓친 경우(2.2 다음의 2.3.1)까지 받는다. 표의 칸에 적힌 수는 이 차례에 맞지 않아 걸러진다.
    """
    if previous is None:
        return number[0] in (0, 1) and all(part == 1 for part in number[1:])
    for index, part in enumerate(number):
        if index >= len(previous):
            return all(rest == 1 for rest in number[index:])
        if part != previous[index]:
            return part == previous[index] + 1 and all(rest == 1 for rest in number[index + 1:])
    return False


def title_like(text, limit=TITLE_MAX):
    """제목으로 볼 글인가: 길지 않고, 대문자나 수로 시작하고, 문장처럼 끝나지 않는다. 띄어쓰기가 사라진 깨진 글은 제목으로 보지 않는다."""
    text = text.strip()
    return (2 <= len(text) <= limit and (text[0].isupper() or text[0].isdigit() or text[0] in pdf_blocks.OPENERS)
            and not text.endswith((".", ";", ",", ":")) and not GLUED.search(text))


def _number(text):
    return tuple(int(part) for part in text.split("."))


def _dotted(number):
    return ".".join(str(part) for part in number)


def _text(lines, index):
    return lines[index][0].strip() if 0 <= index < len(lines) else ""


def _candidate(line, previous):
    """앞 번호 다음에 올 수 있는 번호로 시작하는 줄인가(제목을 모을 때 다음 제목 앞에서 멈추는 데 쓴다)."""
    hit = NUMBER_ONLY.match(line) or NUMBERED.match(line)
    return bool(hit) and follows(previous, _number(hit.group(1)))


def _same(title, listed):
    """본문의 제목과 차례의 제목이 같은 것인가. 한쪽이 다른 쪽의 앞머리이면 같은 것으로 본다(차례가 덜 고쳐진 문서가 있다)."""
    ours, theirs = pdf_pages.squash(title), pdf_pages.squash(listed)
    return len(ours) >= 4 and len(theirs) >= 4 and (ours.startswith(theirs[:SAME]) or theirs.startswith(ours[:SAME]))


def _listed(title, number, toc):
    """차례가 이 번호에 적어 둔 제목과 같은가."""
    return any(_same(title, listed) for listed in toc["titles"].get(_dotted(number), []))


def _in_toc(title, toc):
    """차례의 어느 제목과 같은가. 번호의 단과 제목의 단을 따로 늘어놓은 차례에서는 번호로 제목을 찾지 못하므로 줄마다의 글과도 견준다."""
    return (any(_same(title, listed) for titles in toc["titles"].values() for listed in titles)
            or any(_same(title, line) for line in toc.get("lines", [])))


def _accept(number, title, strong, toc):
    """이 번호와 제목을 제목으로 받을 것인가. strong은 제목의 꼴이 뚜렷한 것(번호만 있는 줄 다음의 제목, 물음, 대문자 제목, 빈 줄이 뒤따르는 제목)."""
    if not toc["text"]:
        return strong
    if len(number) == 1:  # 차례에서 마디가 하나인 번호는 쪽 번호와 섞여 있어 번호로는 찾지 못한다. 차례의 제목 가운데 같은 것이 있는지 본다
        return _in_toc(title, toc)
    if _dotted(number) in toc["numbers"]:
        return strong or _listed(title, number, toc)
    # 차례가 싣지 않는 번호: 깊은 번호(2.3.3.1)는 꼴이 뚜렷하면 받고, 그 밖에는 제목이 차례에 있을 때만 받는다(본문의 번호가 차례와 어긋난 문서)
    return (strong and len(number) >= 3) or _in_toc(title, toc)


def _title_lines(lines, start, number, limit=TITLE_LINES):
    """start 줄부터 제목의 줄을 모은다: (줄들, 쓴 줄 수). 빈 줄이나 다음 제목 앞에서 멈춘다."""
    index = start
    while index < len(lines) and not _text(lines, index) and index - start < 3:
        index += 1
    taken = []
    while index < len(lines) and len(taken) < limit:
        line = _text(lines, index)
        if not line or _candidate(line, number) or (taken and (pdf_blocks.BULLET.match(line) or pdf_blocks.BULLET_START.match(line))):
            break  # 제목 다음 줄에 바로 붙은 글머리표는 본문의 목록이다
        taken.append(line)
        index += 1
    return taken, index - start


def _title_after(lines, start, number, limit=TITLE_LINES):
    """start 줄부터 모은 제목: (제목, 쓴 줄 수)."""
    taken, used = _title_lines(lines, start, number, limit)
    return pdf_blocks.joined(taken), used


def _displaced(lines, index, title):
    """번호 줄의 앞이나 뒤 몇 줄 안에 이 제목과 똑같은 줄이 있는가(제목 줄의 자리가 밀린 문서)."""
    wanted = pdf_pages.squash(title)
    near = list(range(max(0, index - DISPLACED), index)) + list(range(index + 1, min(len(lines), index + 1 + DISPLACED)))
    return bool(wanted) and any(pdf_pages.squash(_text(lines, at)) == wanted for at in near)


def _cut_to_listed(taken, used, listed):
    """모은 제목 줄이 차례의 제목보다 길면(제목 다음 줄에 본문이 바로 붙은 것) 차례의 제목만큼만 남긴다: (줄들, 쓴 줄 수)."""
    wanted = {pdf_pages.squash(title) for title in listed}
    for count in range(1, len(taken)):
        if pdf_pages.squash(" ".join(taken[:count])) in wanted:
            return taken[:count], used - (len(taken) - count)
    return taken, used


def _alone(lines, index, number, toc):
    """번호만 있는 줄에서 시작하는 제목: (제목, 쓴 줄 수, 빌린 제목인가). 없으면 None."""
    listed = toc["titles"].get(_dotted(number), [])
    taken, used = _cut_to_listed(*_title_lines(lines, index + 1, number), listed)
    title = pdf_blocks.joined(taken)
    if listed and len(number) > 1 and not _listed(title, number, toc) and (_dotted(number) in toc.get("paired", ()) or _displaced(lines, index, listed[0])):
        return listed[0], 1, True      # 뒤따르는 글이 차례의 제목과 다르다. 차례의 제목이 믿을 만하거나(짝지은 것) 가까운 다른 줄에 있으면 그 제목을 쓴다
    if not title:  # 번호 줄 둘이 잇달아 오고 제목 둘이 그 뒤에 오는 꼴("5" / "5.1" / "큰 제목" / "작은 제목")
        at = index + 1
        while at < len(lines) and not _text(lines, at) and at - index <= 3:
            at += 1
        child = NUMBER_ONLY.match(_text(lines, at))
        if child and _number(child.group(1)) == number + (1,):
            both, _ = _title_lines(lines, at + 1, number + (1,))
            if len(both) >= 2 and title_like(both[0]) and _accept(number, both[0], True, toc):
                return both[0], 1, True  # 큰 제목의 줄은 지워져 작은 번호가 제 제목을 받는다
    if title_like(title) and _accept(number, title, True, toc):
        return title, 1 + used, False
    if title.endswith(".") and title_like(title[:-1]) and _listed(title, number, toc):
        return title, 1 + used, False  # 마침표로 끝나는 제목은 차례에 같은 제목이 있을 때만 받는다
    if listed and len(number) > 1:
        return listed[0], 1, True      # 제목 줄을 찾지 못했다. 차례의 제목을 빌려 쓴다(마디가 하나인 번호는 차례에서 믿을 수 없어 빌리지 않는다)
    return None


def _question(lines, index, number, text, bare=False):
    """물음표로 끝나는 줄까지를 제목으로 모은다(질의응답의 물음): (제목, 쓴 줄 수). 물음이 아니면 None.

    bare(차례가 없는 문서)이면 제목 다음에 오는 본문의 물음("• Do stakeholders agree …?")까지 삼키지 않도록, 글머리표로 시작하는 줄이나
    문장이 끝난 줄(. :) 다음으로는 잇지 않는다.
    """
    if text.endswith("?"):
        return text, 1
    if pdf_blocks.ends_sentence(text):
        return None
    taken = [text]
    for offset in range(1, QUESTION_LINES + 1):
        line = _text(lines, index + offset)
        if not line or _candidate(line, number):
            return None
        if bare and (pdf_blocks.BULLET.match(line) or pdf_blocks.BULLET_START.match(line) or taken[-1].endswith((".", ":"))):
            return None
        taken.append(line)
        if line.endswith("?"):
            return pdf_blocks.joined(taken), 1 + offset
    return None


def _short_line(lines, index, toc):
    """줄이 쪽의 너비를 채우지 않고 끝났는가(제목 줄은 짧고, 본문의 줄은 다음 줄로 넘어간다)."""
    return len(_text(lines, index)) < pdf_blocks.SHORT * toc.get("width", pdf_blocks.DEFAULT_WIDTH)


def _inline(lines, index, number, hit, toc):
    """번호와 제목이 한 줄에 있는 제목: (제목, 쓴 줄 수, 빌린 제목인가). 없으면 None."""
    text = hit.group(3)
    if not text.lstrip(pdf_blocks.OPENERS)[:1].isupper():
        return None
    bare = not toc["text"]  # 차례가 없는 문서
    loose = bare and toc.get("mode") == "loose"
    question = _question(lines, index, number, text, bare)
    if question:
        title, used, strong = question[0], question[1], True
    elif pdf_blocks.is_upper(text):
        used = 1
        while used <= TITLE_LINES and pdf_blocks.is_upper(_text(lines, index + used)) and not _candidate(_text(lines, index + used), number):
            used += 1
        title, strong = pdf_blocks.joined([text] + [_text(lines, index + offset) for offset in range(1, used)]), True
        if TWO_SENTENCES.search(title):
            return None  # 대문자로 적힌 본문의 문단이다(제목의 꼴로 잘못 꾸며진 것)
    elif (len(number) > 1 or not hit.group(2) or loose) and len(text) <= ONE_LINE_MAX:
        title, used = (text.rstrip(":").rstrip() if loose else text), 1  # loose: 쌍점으로 끝나는 제목("2.2. Purpose of the processing operation:")도 받는다
        while toc["text"] and used < TITLE_LINES:  # 제목이 다음 줄로 넘어간 것은 차례의 글과 견줘 잇는다
            extra = _text(lines, index + used)
            if not extra or _candidate(extra, number) or pdf_pages.squash(f"{title} {extra}") not in toc["text"]:
                break
            title, used = f"{title} {extra}", used + 1
        strong = not _text(lines, index + used) or _candidate(_text(lines, index + used), number)
        if not strong and bare and (len(number) > 1 or loose):
            strong = _short_line(lines, index, toc)  # 차례가 없는 문서: 짧게 끝난 줄이면 제목으로 본다
    else:
        return None
    if title_like(title.rstrip("?"), QUESTION_MAX if title.endswith("?") else TITLE_MAX) and _accept(number, title, strong, toc):
        return title, used, False
    if title.endswith(".") and title_like(title[:-1]) and _listed(title, number, toc):
        return title, used, False
    return None


def _page_top(lines, index):
    """이 줄이 쪽의 첫 줄인가(앞의 글 줄이 다른 쪽에 있다)."""
    at = index - 1
    while at >= 0 and not lines[at][0].strip():
        at -= 1
    return at < 0 or lines[at][1] != lines[index][1]


def _annex_listed(letter, title, toc):
    """차례에 이 부속서가 이 제목으로 적혀 있는가."""
    tail = pdf_pages.squash(title)[:SAME]
    return any(pdf_pages.squash(f"{word} {letter}") + tail in toc["text"] for word in ("annex", "appendix"))


def _annex(lines, index, previous, toc):
    """"ANNEX A"로 시작하는 제목: (글자, 제목, 쓴 줄 수). 없으면 None.

    차례가 있는 문서에서는 차례에 같은 제목으로 적힌 것을 받는다. 차례의 꼴이 달라 제목을 견주지 못할 때는 대문자로 적힌 줄(ANNEX)이나
    쪽의 첫 줄만 받는다(표의 칸이나 본문에 나온 "Annex II"를 제목으로 보지 않게).
    """
    line = _text(lines, index)
    hit = ANNEX.match(line)
    if not hit or len(line) > ONE_LINE_MAX or _text(lines, index - 1):
        return None
    word, letter, title, used = hit.group(1), hit.group(2), hit.group(3).strip(), 1
    if toc["text"] and not any(pdf_pages.squash(f"{name} {letter}") in toc["text"] for name in ("annex", "appendix")):
        return None
    if not title:
        taken, more = _title_lines(lines, index + 1, previous)
        if toc["text"] and taken:  # 제목이 여러 줄이면 차례의 글에 있는 데까지만 제목으로 본다(뒤따르는 본문을 삼키지 않게)
            kept = taken[:1]
            for extra in taken[1:]:
                if pdf_pages.squash(" ".join(kept + [extra])) not in toc["text"]:
                    break
                kept.append(extra)
            if _annex_listed(letter, " ".join(kept), toc):
                more -= len(taken) - len(kept)
                taken = kept
        title = pdf_blocks.joined(taken)
        used += more
    if not title_like(title):
        return None
    if toc["text"] and not (_annex_listed(letter, title, toc) or word.isupper() or _page_top(lines, index)):
        return None
    return letter, title, used


def heading_at(lines, index, previous, toc):
    """index 줄에서 시작하는 제목. 없으면 None. {"kind", "number", "label", "title", "used": 쓴 줄 수, "borrowed": 차례에서 빌린 제목인가}"""
    line = _text(lines, index)
    alone = NUMBER_ONLY.match(line)
    numbered = None if alone else NUMBERED.match(line)
    if alone or numbered:
        number = _number((alone or numbered).group(1))
        if not follows(previous, number):
            return None
        style = "." if (line.endswith(".") if alone else bool(numbered.group(2))) else ""
        if not toc["text"] and len(number) == 1 and toc.get("style") not in (None, style):
            return None  # 차례가 없는 문서: 큰 번호의 꼴이 앞의 제목들과 다르다(쪽 아래의 각주 번호)
        found = _alone(lines, index, number, toc) if alone else _inline(lines, index, number, numbered, toc)
        if not found:
            return None
        if len(number) == 1 and toc.get("style") is None:
            toc["style"] = style
        return {"kind": "section", "number": number, "label": _dotted(number), "title": found[0], "used": found[1], "borrowed": found[2]}
    annex = _annex(lines, index, previous, toc)
    return {"kind": "appendix", "number": None, "label": f"Annex {annex[0]}", "title": annex[1], "used": annex[2], "borrowed": False} if annex else None


def stream(pages, width):
    """쪽들의 본문을 한 줄기로 잇는다: [(줄, 쪽의 차례)]. 쪽이 바뀌는 곳에서 문장이 이어지면 빈 줄을 넣지 않는다."""
    lines = []
    for index, page in enumerate(pages):
        body = page["lines"]
        if not body:
            continue
        if lines:
            last, first = lines[-1][0], body[0].strip()
            open_end = bool(last.strip()) and not pdf_blocks.ends_sentence(last) and pdf_blocks.ending(last) not in ":;"
            if not (open_end and (first[:1].islower() or len(last.strip()) >= pdf_blocks.SHORT * width)):
                lines.append(("", index))
        lines += [(line, index) for line in body]
    return lines


def _part(kind, key, label, title, level):
    return {"id": key, "kind": kind, "label": label, "title": title, "level": level, "lines": [], "pages": set()}


def _blank_displaced(lines, index, previous_part, title):
    """빌려 쓴 제목과 똑같은 줄(자리가 밀린 제목)을 지운다: 뒤따르는 몇 줄과, 앞 조각의 마지막 몇 줄에서."""
    wanted = pdf_pages.squash(title)
    for later in range(index, min(len(lines), index + BLANK_AHEAD)):
        if pdf_pages.squash(lines[later][0]) == wanted:
            lines[later] = ("", lines[later][1])
            return
    kept = previous_part["lines"]
    for earlier in range(len(kept) - 1, max(-1, len(kept) - 1 - DISPLACED), -1):
        if pdf_pages.squash(kept[earlier]) == wanted:
            kept[earlier] = ""
            return


def parts(text, outline="auto"):
    """글을 조각의 목록으로 나눈다. 조각은 {"id", "kind", "label", "title", "level", "blocks"}다. 각주는 그 번호가 나온 조각의 끝에 "[3] …"으로 싣는다.

    outline은 제목을 찾는 방식이다: auto(기본), loose(차례가 없는 문서에서 "1. 제목" 꼴도 받는다), none(찾지 않고 글 전체를 조각 하나로 둔다).
    """
    if outline not in OUTLINES:
        raise ValueError(f"모르는 outline: {outline}")
    document = pdf_pages.read(text)
    toc = {**document["toc"], "mode": outline, "style": None}
    width = toc["width"] = pdf_blocks.typical_width([line for page in document["pages"] for line in page["lines"]])
    lines = stream(document["pages"], width)
    whole = outline == "none"
    found = [_part("section", BODY_ID, BODY_LABEL, "", 1) if whole else _part("cover", "cover", "", "", 0)]
    seen, previous, index = {found[0]["id"]}, None, 0
    while index < len(lines):
        line, page = lines[index]
        heading = heading_at(lines, index, previous, toc) if line.strip() and not whole else None
        if heading is None:
            found[-1]["lines"].append(line)
            found[-1]["pages"].add(page)
            index += 1
            continue
        if heading["kind"] == "section":
            previous = heading["number"]
            key, level = "sec-" + "-".join(str(part) for part in heading["number"]), len(heading["number"])
        else:
            key, level = "annex-" + heading["label"].split()[-1].lower(), 1
        base, count = key, 2
        while key in seen:  # 같은 번호가 또 나오면 뒤에 차례를 붙여 가린다
            key, count = f"{base}-{count}", count + 1
        seen.add(key)
        found.append(_part(heading["kind"], key, heading["label"], heading["title"], level))
        found[-1]["pages"].add(page)
        for at in range(index, min(len(lines), index + heading["used"])):
            lines[at] = ("", lines[at][1])  # 제목으로 쓴 줄은 비운다(뒤의 번호가 이 줄을 자리가 밀린 제 제목으로 보지 않게)
        index += heading["used"]
        if heading["borrowed"]:  # 자리가 밀려 따로 적힌 제목 줄은 지운다(제목이 두 번 나오지 않게)
            _blank_displaced(lines, index, found[-2], heading["title"])
    for part in found:
        part["blocks"] = pdf_blocks.blocks(part.pop("lines"), width)
    for page, entry in enumerate(document["pages"]):
        for number, note in entry["notes"]:
            on_page = [part for part in found if page in part["pages"]] or found[-1:]
            home = next((part for part in on_page if any(f"[{number}]" in block for block in part["blocks"] + [part["title"]])), on_page[-1])
            home.setdefault("notes", []).append(f"[{number}] {note}")
    for part in found:
        part["blocks"] += part.pop("notes", [])
        del part["pages"]
    return [part for part in found if part["blocks"] or part["title"]]


def label_ko(part):
    """조각의 이름을 국문으로: 절은 번호 그대로, Annex A → 부속서 A."""
    if part["kind"] == "appendix":
        return f"부속서 {part['label'].split()[-1]}"
    return "표지와 일러두기" if part["kind"] == "cover" else part["label"]


def main(argv):
    text = open(argv[0], encoding="utf-8").read()
    outline = argv[argv.index("--outline") + 1] if "--outline" in argv else "auto"
    found = parts(text, outline)
    wanted = argv[argv.index("--blocks") + 1] if "--blocks" in argv else ""
    for part in found:
        if wanted:
            if part["id"] == wanted:
                for block in part["blocks"]:
                    print(f"- {block}")
            continue
        print(f"{'  ' * max(0, part['level'] - 1)}{part['label'] or part['kind']}  {part['title'][:80]}  [{len(part['blocks'])}문단 {sum(len(block) for block in part['blocks']):,}자]")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
