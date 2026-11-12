"""EU 집행위원회 안내 문서(PDF에서 뽑아 둔 글)를 읽기 좋은 조각으로 나눈다. 법령의 segment.parts와 같은 꼴을 돌려준다.

조각(part)은 표지(cover: 첫 제목 앞의 글), 절(section: 번호가 붙은 제목마다 하나), 부속서(appendix: "ANNEX A" 같은 제목마다 하나)다.
제목은 세 가지 꼴로 적혀 있다.
- 번호만 있는 줄 다음에 제목이 오는 것("2.3.3" / "Definition and explanation of …")
- 번호와 제목이 한 줄에 있는 것("3.1.1 Emissions monitoring", "2.4. How can the CBAM declaration be submitted …?", "4. METHODOLOGY FOR …")
- "ANNEX A" 다음에 제목이 오는 것

표의 칸이나 목록의 번호, 줄 머리에 온 본문의 수를 제목으로 잘못 보지 않도록 세 가지를 본다.
- 번호는 앞 제목의 번호 바로 다음이어야 한다(follows).
- 차례가 있는 문서에서는 차례에 적힌 번호여야 한다. 마디가 하나뿐인 번호("3")는 차례의 쪽 번호와 가릴 수 없으므로 제목이 차례의 제목과 같아야 한다.
  차례가 싣지 않는 깊은 번호("2.3.3.1")는 제목의 꼴이 뚜렷할 때만 받는다.
- 제목 다음에 본문이 바로 이어지는 꼴(약한 꼴)은 제목이 차례의 제목과 같을 때만 받는다.
PDF에서 글이 뒤섞여 제목 줄을 찾지 못한 번호는 차례의 제목을 빌려 쓴다.

쓰는 법(살펴볼 때): python -m tools.laws.guide_segment <글 파일> [--blocks <조각 id>]
"""
import re
import sys

from tools.laws import pdf_blocks, pdf_pages

NUMBER_ONLY = re.compile(r"^(\d+(?:\.\d+){0,4})\.?$")
NUMBERED = re.compile(r"^(\d+(?:\.\d+){0,4})(?:(\.)\s*|\s+)(\S.*)$")
ANNEX = re.compile(r"^(?:ANNEX|Annex|APPENDIX|Appendix)\s+([A-Z]|[IVXLC]+|\d+)\s*[:.–—-]?\s*(.*)$")
TITLE_MAX = 220       # 제목의 글자 수
TITLE_LINES = 4       # 제목이 걸칠 수 있는 줄 수
QUESTION_MAX = 700    # 물음으로 된 제목(질의응답)의 글자 수
QUESTION_LINES = 8    # 물음으로 된 제목이 걸칠 수 있는 줄 수
ONE_LINE_MAX = 120    # 번호와 한 줄에 적힌 제목(물음도 대문자도 아닌 것)의 글자 수
SAME = 25             # 본문의 제목과 차례의 제목을 견줄 때 보는 앞머리의 글자 수
DISPLACED = 8         # 빌려 쓴 제목과 같은 줄(자리가 밀린 제목)을 찾아 지우는 줄 수


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
    """제목으로 볼 글인가: 길지 않고, 대문자나 수로 시작하고, 문장처럼 끝나지 않는다."""
    text = text.strip()
    return 2 <= len(text) <= limit and (text[0].isupper() or text[0].isdigit() or text[0] in pdf_blocks.OPENERS) and not text.endswith((".", ";", ",", ":"))


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


def _accept(number, title, strong, toc):
    """이 번호와 제목을 제목으로 받을 것인가. strong은 제목의 꼴이 뚜렷한 것(번호만 있는 줄 다음의 제목, 물음, 대문자 제목, 빈 줄이 뒤따르는 제목)."""
    if not toc["text"]:
        return strong
    if len(number) == 1:  # 차례에서 마디가 하나인 번호는 쪽 번호와 섞여 있어 번호로는 찾지 못한다. 차례의 제목 가운데 같은 것이 있는지 본다
        return any(_same(title, listed) for titles in toc["titles"].values() for listed in titles)
    if _dotted(number) in toc["numbers"]:
        return strong or _listed(title, number, toc)
    return strong and len(number) >= 3  # 차례가 싣지 않는 깊은 번호(2.3.3.1)는 꼴이 뚜렷할 때만 받는다


def _title_after(lines, start, number, limit=TITLE_LINES):
    """start 줄부터 제목의 줄을 모은다: (제목, 쓴 줄 수). 빈 줄이나 다음 제목 앞에서 멈춘다."""
    index = start
    while index < len(lines) and not _text(lines, index) and index - start < 3:
        index += 1
    taken = []
    while index < len(lines) and len(taken) < limit:
        line = _text(lines, index)
        if not line or _candidate(line, number):
            break
        taken.append(line)
        index += 1
    return pdf_blocks.joined(taken), index - start


def _alone(lines, index, number, toc):
    """번호만 있는 줄에서 시작하는 제목: (제목, 쓴 줄 수, 빌린 제목인가). 없으면 None."""
    title, used = _title_after(lines, index + 1, number)
    if title_like(title) and _accept(number, title, True, toc):
        return title, 1 + used, False
    if title.endswith(".") and title_like(title[:-1]) and _listed(title, number, toc):
        return title, 1 + used, False  # 마침표로 끝나는 제목은 차례에 같은 제목이 있을 때만 받는다
    listed = toc["titles"].get(_dotted(number), [])
    if listed and len(number) > 1:
        return listed[0], 1, True      # 제목 줄을 찾지 못했다. 차례의 제목을 빌려 쓴다(마디가 하나인 번호는 차례에서 믿을 수 없어 빌리지 않는다)
    return None


def _question(lines, index, number, text):
    """물음표로 끝나는 줄까지를 제목으로 모은다(질의응답의 물음): (제목, 쓴 줄 수). 물음이 아니면 None."""
    if text.endswith("?"):
        return text, 1
    if pdf_blocks.ends_sentence(text):
        return None
    taken = [text]
    for offset in range(1, QUESTION_LINES + 1):
        line = _text(lines, index + offset)
        if not line or _candidate(line, number):
            return None
        taken.append(line)
        if line.endswith("?"):
            return pdf_blocks.joined(taken), 1 + offset
    return None


def _inline(lines, index, number, hit, toc):
    """번호와 제목이 한 줄에 있는 제목: (제목, 쓴 줄 수, 빌린 제목인가). 없으면 None."""
    text = hit.group(3)
    if not text[:1].isupper():
        return None
    question = _question(lines, index, number, text)
    if question:
        title, used, strong = question[0], question[1], True
    elif pdf_blocks.is_upper(text):
        used = 1
        while used <= TITLE_LINES and pdf_blocks.is_upper(_text(lines, index + used)) and not _candidate(_text(lines, index + used), number):
            used += 1
        title, strong = pdf_blocks.joined([text] + [_text(lines, index + offset) for offset in range(1, used)]), True
    elif (len(number) > 1 or not hit.group(2)) and len(text) <= ONE_LINE_MAX:
        title, used = text, 1
        while toc["text"] and used < TITLE_LINES:  # 제목이 다음 줄로 넘어간 것은 차례의 글과 견줘 잇는다
            extra = _text(lines, index + used)
            if not extra or _candidate(extra, number) or pdf_pages.squash(f"{title} {extra}") not in toc["text"]:
                break
            title, used = f"{title} {extra}", used + 1
        strong = not _text(lines, index + used) or _candidate(_text(lines, index + used), number)
    else:
        return None
    if title_like(title.rstrip("?"), QUESTION_MAX if title.endswith("?") else TITLE_MAX) and _accept(number, title, strong, toc):
        return title, used, False
    if title.endswith(".") and title_like(title[:-1]) and _listed(title, number, toc):
        return title, used, False
    return None


def _annex(lines, index, previous, toc):
    """"ANNEX A"로 시작하는 제목: (글자, 제목, 쓴 줄 수). 없으면 None."""
    line = _text(lines, index)
    hit = ANNEX.match(line)
    if not hit or len(line) > ONE_LINE_MAX or _text(lines, index - 1):
        return None
    letter, title, used = hit.group(1), hit.group(2).strip(), 1
    if toc["text"] and pdf_pages.squash(f"annex {letter}") not in toc["text"] and pdf_pages.squash(f"appendix {letter}") not in toc["text"]:
        return None
    if not title:
        title, more = _title_after(lines, index + 1, previous)
        used += more
    return (letter, title, used) if title_like(title) else None


def heading_at(lines, index, previous, toc):
    """index 줄에서 시작하는 제목. 없으면 None. {"kind", "number", "label", "title", "used": 쓴 줄 수, "borrowed": 차례에서 빌린 제목인가}"""
    line = _text(lines, index)
    alone = NUMBER_ONLY.match(line)
    numbered = None if alone else NUMBERED.match(line)
    if alone or numbered:
        number = _number((alone or numbered).group(1))
        if not follows(previous, number):
            return None
        found = _alone(lines, index, number, toc) if alone else _inline(lines, index, number, numbered, toc)
        return {"kind": "section", "number": number, "label": _dotted(number), "title": found[0], "used": found[1], "borrowed": found[2]} if found else None
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


def parts(text):
    """글을 조각의 목록으로 나눈다. 조각은 {"id", "kind", "label", "title", "level", "blocks"}다. 각주는 그 번호가 나온 조각의 끝에 "[3] …"으로 싣는다."""
    document = pdf_pages.read(text)
    width = pdf_blocks.typical_width([line for page in document["pages"] for line in page["lines"]])
    lines = stream(document["pages"], width)
    found, seen, previous, index = [_part("cover", "cover", "", "", 0)], {"cover"}, None, 0
    while index < len(lines):
        line, page = lines[index]
        heading = heading_at(lines, index, previous, document["toc"]) if line.strip() else None
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
        index += heading["used"]
        if heading["borrowed"]:  # 자리가 밀려 조금 아래에 따로 적힌 제목 줄은 지운다(제목이 두 번 나오지 않게)
            for later in range(index, min(len(lines), index + DISPLACED)):
                if pdf_pages.squash(lines[later][0]) == pdf_pages.squash(heading["title"]):
                    lines[later] = ("", lines[later][1])
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
    found = parts(text)
    wanted = argv[2] if len(argv) > 2 and argv[1] == "--blocks" else ""
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
