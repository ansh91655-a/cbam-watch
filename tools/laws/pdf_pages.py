"""PDF에서 뽑아 둔 글(쪽마다 \\f로 나뉜 것)을 쪽으로 읽고, 본문이 아닌 것을 가려낸다. 받기와 쓰기는 하지 않는다.

- 되풀이되는 머리말과 꼬리말: 여러 쪽의 첫 줄이나 마지막 줄에 똑같이 나오는 줄(수만 다른 것 포함)은 뺀다.
  그 줄이 쪽의 가운데에 끼어 있는 것(꼬리말 아래에 각주가 온 쪽)도 함께 뺀다.
- 쪽 번호: 쪽의 마지막 줄에 수만 적힌 것. (적힌 수 - 쪽의 차례)가 문서에서 가장 흔한 값일 때만 쪽 번호로 본다.
- 차례 쪽: "CONTENTS", "Outline" 같은 줄에서 시작해 본문의 첫 제목이 나오는 쪽 앞까지. 본문에서 빼고, 제목을 가려내는 데만 쓴다.
- 각주: 쪽 아래에 번호만 적힌 줄과 그 아래의 글. 번호는 문서 전체에서 이어진다. 본문에 그 번호가 붙어 있는 자리(hydrogen3)를
  찾았을 때만 각주로 보고, 그 자리는 [3]으로 바꾼다(표의 칸에 적힌 수를 각주로 잘못 보지 않게).
"""
import collections
import re

NUMBER = re.compile(r"^\d{1,4}$")
PAGE_LABEL = re.compile(r"^(?:Page\s+)?(\d{1,4})(?:\s*(?:/|of)\s*\d{1,4})?$")
TOC_HEAD = re.compile(r"^(TABLE OF CONTENTS|Table of [Cc]ontents|CONTENTS|Contents|Outline)$")
LEADERS = re.compile(r"\.{5,}")
DOTTED = re.compile(r"^(\d+(?:\.\d+)*)\.?(?=\s|$)")
FIRST_HEADING = re.compile(r"^1\.?(?:\s+\S.*)?$")
INLINE_NOTE = re.compile(r"^(\d{1,3})\s+(\S.*)$")
ADDRESS = re.compile(r"^Commission européenne/Europese Commissie\b")  # 표지 아래에 적힌 집행위원회의 주소와 대표 전화
ARROWS = (">", "›", "»")  # 도안으로 된 문서에서 제목 앞에 놓인 화살표가 따로 뽑힌 줄
TOC_STOP = re.compile(r"^(?:ANNEX|Annex|APPENDIX|Appendix)\b")
TOC_TAIL = re.compile(r"[\s.]*\d{1,4}\s*$")
COLUMN_NUMBER = re.compile(r"^(\d+(?:\.\d+)*)\.?$")  # 차례의 번호 단에 적힌 줄("1.", "1.4")
COLUMN_MIN = 5    # 번호만 있는 줄이 이만큼은 있어야 단이 나뉜 차례로 본다
LISTS_AFTER = re.compile(r"^(?:List|Table) of (?:tables|figures)$", re.I)  # 차례 다음에 오는 표·그림 목록의 제목
TOC_SEARCH = 12   # 차례는 문서의 앞쪽 몇 쪽 안에서만 찾는다
TOC_TOP = 12      # 차례의 제목은 쪽의 위쪽 몇 줄 안에 있다
TOC_SPAN = 20     # 차례가 이어질 수 있는 쪽 수
NOTE_JUMP = 5     # 각주 번호가 이만큼까지 건너뛰어도 이어진 것으로 본다(앞쪽의 각주를 놓쳤을 때)
INVERTED_LINES = 15  # 번호가 글 뒤에 적힌 각주 구역의 줄 수는 이보다 많지 않다
REPEATED = 0.5    # 이 비율이 넘는 쪽에 똑같이 나오는 첫 줄·마지막 줄은 머리말·꼬리말이다
REPEATED_MIN = 3  # 적어도 이만큼의 쪽에 나와야 한다(두 쪽짜리 문서에서 우연히 같은 줄을 빼지 않게)
REPEATED_TURNS = 6    # 머리말·꼬리말이 여러 줄일 수 있어 이만큼 되풀이해 벗긴다
BOILERPLATE_MIN = 12  # 쪽의 가운데에 낀 머리말·꼬리말은 이보다 긴 줄만 뺀다(짧은 줄은 본문의 줄과 가릴 수 없다)


def squash(text):
    """견주기 좋게 소문자 글자와 숫자만 남긴다."""
    return re.sub(r"[^a-z0-9]+", "", str(text).lower())


def _trim(lines):
    start, end = 0, len(lines)
    while start < end and not lines[start].strip():
        start += 1
    while end > start and not lines[end - 1].strip():
        end -= 1
    return lines[start:end]


def split(text):
    """쪽마다의 줄 목록(앞뒤의 빈 줄은 뺀다). 표지 아래의 기관 주소 줄과, 화살표만 있는 줄은 뺀다."""
    pages = [_trim([line.rstrip() for line in page.split("\n") if not ADDRESS.match(line.strip()) and line.strip() not in ARROWS]) for page in str(text).split("\f")]
    while pages and not pages[-1]:
        pages.pop()
    return pages


def _shape(line):
    """줄의 꼴: 수는 #으로 바꿔 쪽마다 수만 다른 줄을 같은 것으로 본다."""
    return re.sub(r"\d+", "#", line.strip())


def strip_repeated(pages):
    """여러 쪽의 첫 줄이나 마지막 줄에 되풀이되는 줄(머리말, 꼬리말)을 뺀다. 같은 줄이 쪽의 가운데에 낀 것도 뺀다."""
    needed = max(REPEATED_MIN, REPEATED * len(pages))
    boilerplate = set()
    for _ in range(REPEATED_TURNS):
        changed = False
        for position in (0, -1):
            seen = collections.Counter(_shape(lines[position]) for lines in pages if lines)
            common = {line for line, count in seen.items() if count >= needed and re.search(r"[A-Za-z]{3}", line)}
            if common:
                pages = [_trim(lines[1:] if position == 0 else lines[:-1]) if lines and _shape(lines[position]) in common else lines for lines in pages]
                boilerplate |= {line for line in common if len(line) >= BOILERPLATE_MIN}
                changed = True
        if not changed:
            break
    if boilerplate:
        pages = [_trim([line for line in lines if _shape(line) not in boilerplate]) for lines in pages]
    return pages


def strip_page_numbers(pages):
    """쪽의 마지막 줄이 쪽 번호이면 뺀다."""
    labels = []
    for index, lines in enumerate(pages):
        hit = PAGE_LABEL.match(lines[-1].strip()) if lines else None
        labels.append(int(hit.group(1)) - index if hit else None)
    common = collections.Counter(label for label in labels if label is not None).most_common(1)
    if not common or common[0][1] < max(2, len(pages) // 3):
        return pages
    return [_trim(lines[:-1]) if label == common[0][0] else lines for lines, label in zip(pages, labels)]


def _looks_like_toc(lines):
    filled = [line.strip() for line in lines if line.strip()]
    marked = sum(bool(LEADERS.search(line) or NUMBER.match(line) or DOTTED.match(line)) for line in filled)
    return bool(filled) and marked >= 0.4 * len(filled)


def find_toc(pages):
    """차례의 자리: (시작하는 쪽, 그 쪽에서 시작하는 줄, 본문이 시작하는 쪽). 차례가 없으면 None."""
    for page_index, lines in enumerate(pages[:TOC_SEARCH]):
        for line_index, line in enumerate(lines[:TOC_TOP]):
            if not TOC_HEAD.match(line.strip()):
                continue
            for body in range(page_index + 1, min(len(pages), page_index + 1 + TOC_SPAN)):
                if pages[body] and FIRST_HEADING.match(pages[body][0].strip()):
                    return page_index, line_index, body
            body = page_index + 1  # 본문의 첫 제목을 찾지 못하면 차례처럼 생긴 쪽까지만 차례로 본다
            while body < len(pages) and body - page_index < TOC_SPAN and _looks_like_toc(pages[body]):
                body += 1
            return page_index, line_index, body
    return None


def toc_titles(lines):
    """차례의 줄에서 번호마다의 제목을 읽는다: {"2.3.1": ["Unit of production and embedded emissions"]}.

    번호 다음에 오는 첫 글 덩어리가 제목이다(번호와 제목 사이에 쪽 번호가 끼어 있으면 건너뛴다).
    쪽 번호도 번호처럼 보여 한 번호에 제목이 여럿 붙을 수 있으므로(마디가 하나인 번호), 본문의 제목과 견주는 데 쓴다.
    """
    found, lines = {}, [line.strip() for line in lines]
    for index, line in enumerate(lines):
        hit = DOTTED.match(line)
        if not hit:
            continue
        rest = line[hit.end():].strip()
        words = [rest] if rest else []
        cursor = index + 1
        while cursor < len(lines) and len(words) < 5 and not (words and LEADERS.search(words[-1])):
            following = lines[cursor]
            cursor += 1
            if not following or NUMBER.match(following):
                if words:
                    break
                continue
            if DOTTED.match(following) or TOC_STOP.match(following):
                break
            words.append(following)
        title = TOC_TAIL.sub("", LEADERS.sub(" ", " ".join(words))).strip()
        if len(title) >= 3 and title not in found.get(hit.group(1), []):
            found.setdefault(hit.group(1), []).append(title)
    return found


def toc_columns(lines):
    """번호의 단과 제목의 단을 따로 늘어놓은 차례에서 번호와 제목을 짝짓는다: {"1.4": "Structure"}.

    번호만 있는 줄들과, 번호 없이 제목만 있는 줄들의 수가 같을 때만 차례대로 짝짓는다(수가 다르면 빈 것을 돌려준다).
    제목은 점줄이나 쪽 번호로 끝나는 줄까지가 하나다(두 줄에 걸친 제목은 앞줄에 점줄이 없다).
    번호와 제목이 한 줄에 있는 줄("3.3.1 Authenticate …")은 이미 짝지어져 있으므로 세지 않는다.
    """
    numbers, titles, words = [], [], []
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        if LISTS_AFTER.match(line):
            break  # 차례 다음에 오는 표와 그림의 목록은 세지 않는다
        alone = COLUMN_NUMBER.match(line)
        if alone:
            numbers.append(alone.group(1))
            continue
        if DOTTED.match(line):
            words = []
            continue
        words.append(line)
        if LEADERS.search(line) or re.search(r"(?:\s|\.{2,})\d{1,4}$", line):
            titles.append(TOC_TAIL.sub("", LEADERS.sub(" ", " ".join(words))).strip())
            words = []
    if len(numbers) < COLUMN_MIN or len(numbers) != len(titles) or len(set(numbers)) != len(numbers) or words:
        return {}
    return dict(zip(numbers, titles))


def toc_lines(lines):
    """차례의 줄마다 번호와 점줄, 쪽 번호를 떼어 낸 글. 번호와 제목을 따로 늘어놓은 차례(번호의 단과 제목의 단)에서 제목을 찾는 데 쓴다."""
    found = []
    for line in lines:
        text = TOC_TAIL.sub("", LEADERS.sub(" ", DOTTED.sub("", line.strip(), count=1))).strip()
        if len(text) >= 4 and re.search(r"[A-Za-z]{3}", text) and text not in found:
            found.append(text)
    return found


def toc_of(pages, found):
    """차례에서 읽은 것: {"numbers": 줄 머리의 번호들("2.3.1"), "titles": 번호마다의 제목, "paired": 단이 나뉜 차례에서 제목을 차례대로 짝지은 번호들,
    "lines": 줄마다의 제목 글, "text": 차례의 글을 squash한 것}"""
    if not found:
        return {"numbers": set(), "titles": {}, "paired": set(), "lines": [], "text": ""}
    start_page, start_line, body = found
    lines = pages[start_page][start_line + 1:] + [""] + [line for page in pages[start_page + 1:body] for line in page + [""]]
    numbers = {hit.group(1) for hit in (DOTTED.match(line.strip()) for line in lines) if hit}
    titles, paired = toc_titles(lines), toc_columns(lines)
    for number, title in paired.items():  # 단이 나뉜 차례에서는 번호 다음의 글이 제목이 아니다. 차례대로 짝지은 것을 쓴다
        titles[number] = [title]
    return {"numbers": numbers, "titles": titles, "paired": set(paired), "lines": toc_lines(lines),
            "text": squash(" ".join(LEADERS.sub(" ", line) for line in lines))}


STRONG_MARK = r"(?:(?<=[a-z]{3})|(?<=[A-Z]{4})|(?<=[)\]”’\"]))"               # 낱말(hydrogen3, BREF1)이나 닫는 괄호·따옴표에 바로 붙은 자리
WEAK_MARK = r"(?<=[^\d\s][.,;:%])(?<![^A-Za-z][A-Z]\.)(?<!^[A-Z]\.)"            # 문장부호 바로 뒤(period.5). 절 번호(D.1, B.3)는 뺀다
MARK_END = r"(?!\w)(?!\.\d)"


def _strong_reference(number):
    """낱말이나 닫는 괄호·따옴표에 바로 붙은 각주 번호를 찾는 식."""
    return re.compile(rf"{STRONG_MARK}{number}{MARK_END}")


def _weak_reference(number):
    """문장부호 바로 뒤에 붙은 각주 번호를 찾는 식. 낱말에 붙은 것보다 잘못 걸리기 쉬워, 낱말에 붙은 자리가 없을 때만 쓴다."""
    return re.compile(rf"{WEAK_MARK}{number}{MARK_END}")


def _reference(number):
    """본문에 붙어 있는 각주 번호를 찾는 식: 낱말 바로 뒤(hydrogen3, BREF1), 닫는 괄호나 따옴표 바로 뒤, 문장부호 바로 뒤(period.5)의 수.

    단위와 화학식(m3, tCO2), 소수(0.5)는 걸리지 않게 한다: 소문자 세 글자나 대문자 네 글자 뒤, 수가 아닌 글자에 붙은 문장부호 뒤만 본다.
    """
    return re.compile(rf"(?:{STRONG_MARK}|{WEAK_MARK}){number}{MARK_END}")


def _mentioned(lines, number):
    """본문에 이 각주 번호가 달린 자리가 있는가. 괄호에 넣어 적은 것("… system (16).")도 친다."""
    return any(_reference(number).search(line) or re.search(rf"\s\({number}\)", line) for line in lines)


def _note_zone(lines, number, tight=False):
    """번호가 number인 각주가 시작하는 줄의 자리. 쪽의 아래쪽에서부터 찾는다. 없으면 None.

    각주 번호의 앞줄은 비어 있다. tight이면 앞줄이 비어 있지 않아도 받는다: 본문의 마지막 문장이 다음 쪽으로 넘어가는 쪽에서는
    본문과 각주 사이에 빈 줄이 없다. 그때는 번호만 있는 줄이고 그 뒤가 빈 줄일 때만 받는다(본문의 줄 머리에 온 수와 가리려는 것).
    """
    for index in range(len(lines) - 1, -1, -1):
        line = lines[index].strip()
        open_above = bool(index and lines[index - 1].strip())
        if open_above and not (tight and line == str(number) and index + 1 < len(lines) and not lines[index + 1].strip()):
            continue
        inline = INLINE_NOTE.match(line)
        if line == str(number) or (not open_above and inline and int(inline.group(1)) == number and inline.group(2)[:1].isupper()):
            return index
    return None


def _read_notes(zone, first):
    """각주 구역의 줄들을 [(번호, 글)]로 읽는다. 번호가 차례대로 이어지지 않으면 각주가 아닌 것으로 보고 빈 목록을 돌려준다."""
    notes, number, words, blank = [], None, [], True
    for line in zone:
        line = line.strip()
        if not line:
            blank = True
            continue
        expected = first if number is None else number + 1
        inline = INLINE_NOTE.match(line) if blank else None
        if NUMBER.match(line) or (inline and int(inline.group(1)) == expected and number is None):
            value = int(line) if NUMBER.match(line) else int(inline.group(1))
            if value != expected or (number is not None and not words):
                return []
            if number is not None:
                notes.append((number, " ".join(words)))
            number, words = value, ([] if NUMBER.match(line) else [inline.group(2)])
        elif number is None:
            return []
        else:
            words.append(line)
        blank = False
    if number is None or not words:
        return []
    return notes + [(number, " ".join(words))]


def _loose_reference(number):
    """글자나 닫는 괄호에 바로 붙고 띄어쓰기나 문장부호가 뒤따르는 수(UCC3)). 각주 구역을 따로 확인했을 때만 쓴다(CO2 같은 것과 가릴 수 없다)."""
    return re.compile(rf"(?<=[A-Za-z)\]]){number}(?=[\s).,;:]|$)")


def _act_reference(number):
    """법령 번호 바로 뒤에 붙은 각주 번호(2015/24474 → 2015/2447 뒤의 4). 법령 번호의 뒷마디는 네 자리까지다."""
    return re.compile(rf"\b((?:19|20)\d{{2}}/\d{{3,4}}){number}(?!\d)")


def _mark(body, notes):
    """본문에 붙은 각주 번호를 [3] 꼴로 바꾼다. 흔한 꼴로 찾지 못한 번호는 법령 번호 뒤에 붙은 것과, 쪽에 하나뿐인 느슨한 꼴을 찾는다."""
    for number, _ in notes:
        for pattern in (_strong_reference(number), _weak_reference(number)):  # 낱말에 붙은 자리가 있으면 그것만 바꾼다(절 번호 "D.1" 같은 것을 건드리지 않게)
            if any(pattern.search(line) for line in body):
                body = [pattern.sub(f"[{number}]", line) for line in body]
                break
        if any(f"[{number}]" in line for line in body):
            continue
        glued = [index for index, line in enumerate(body) if _act_reference(number).search(line)]
        loose = [(index, hit) for index, line in enumerate(body) for hit in _loose_reference(number).finditer(line)]
        if glued:
            body[glued[0]] = _act_reference(number).sub(rf"\g<1>[{number}]", body[glued[0]], count=1)
        elif len(loose) == 1:
            index, hit = loose[0]
            body[index] = body[index][:hit.start()] + f"[{number}]" + body[index][hit.end():]
    return body


def _inverted_notes(lines, first):
    """각주 번호가 글 뒤에 적힌 꼴을 읽는다: (본문 줄, [(번호, 글)]). 그런 꼴이 아니면 None.

    쪽 아래가 "글1 / 2 / 글2 / 1"처럼 뽑힌 문서가 있다: 쪽의 마지막 줄이 그 쪽 첫 각주의 번호이고, 그 앞에 '글, 다음 번호'가 되풀이된다.
    각주 구역은 본문과 빈 줄로 나뉜다.
    """
    body = _trim(lines)
    if len(body) < 3 or body[-1].strip() != str(first):
        return None
    start = max((index for index, line in enumerate(body[:-1]) if not line.strip()), default=None)
    if start is None or len(body) - start - 2 > INVERTED_LINES:
        return None
    notes, number, words = [], first, []
    for line in (line.strip() for line in body[start + 1:-1]):
        if DOTTED.match(line) and "." in DOTTED.match(line).group(1):
            return None  # 절의 제목이 든 구역은 각주가 아니다(본문과 각주 사이에 빈 줄이 없는 쪽)
        if line == str(number + 1) and words:
            notes.append((number, " ".join(words)))
            number, words = number + 1, []
        elif NUMBER.match(line):
            return None
        else:
            words.append(line)
    if not words:
        return None
    return _trim(body[:start]), notes + [(number, " ".join(words))]


def take_notes(lines, expected):
    """쪽 아래의 각주를 떼어 낸다: (본문 줄, [(번호, 글)], 다음에 올 각주 번호). 각주가 없으면 줄을 그대로 돌려준다."""
    for first, tight in [(expected, False), (expected, True)] + [(number, False) for number in range(expected + 1, expected + NOTE_JUMP + 1)]:
        start = _note_zone(lines, first, tight)
        if start is None:
            continue
        notes = _read_notes(lines[start:], first)
        body = _trim(lines[:start])
        if notes and _mentioned(body, first):
            return _mark(body, notes), notes, notes[-1][0] + 1
    inverted = _inverted_notes(lines, expected)
    if inverted and (_mentioned(inverted[0], expected) or any(_loose_reference(expected).search(line) for line in inverted[0])):
        body, notes = inverted
        return _mark(body, notes), notes, notes[-1][0] + 1
    return lines, [], expected


def read(text):
    """글을 쪽으로 읽는다: {"pages": [{"lines": 본문 줄, "notes": [(번호, 글)]}], "toc": 차례에서 읽은 것}. 차례 쪽은 pages에서 뺀다."""
    pages = strip_page_numbers(strip_repeated(split(text)))
    found = find_toc(pages)
    toc = toc_of(pages, found)
    if found:
        start_page, start_line, body = found
        pages = pages[:start_page] + [_trim(pages[start_page][:start_line])] + pages[body:]
    read_pages, expected = [], 1
    for lines in pages:
        body, notes, expected = take_notes(lines, expected)
        read_pages.append({"lines": body, "notes": notes})
    return {"pages": read_pages, "toc": toc}
