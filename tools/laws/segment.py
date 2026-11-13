"""받아 둔 법령의 글을 읽기 좋은 조각으로 나눈다. 받기와 쓰기는 하지 않는다.

조각(part)은 머리(제목과 근거), 전문(recitals), 장·절의 제목, 조, 맺음(서명), 부속서, 각주다.
조각 안의 줄(block)은 문단 하나이고, 번역은 이 줄마다 붙는다. 번호만 따로 적힌 줄("1.", "(a)")은 다음 줄과 잇는다.
통합본의 개정 표시(▼B, ►M1 … ◄)는 글에서 뺀다.
받아 둘 때 부속서의 뒷부분을 뺀 자리의 표시([이 부속서의 나머지 N줄은 싣지 않음], tools/archive/acts.py)는 줄로 싣지 않고 그 조각의 "cut"에 뺀 줄 수로 적는다.
화면이 그 자리에 싣지 않은 부분이 있다고 알린다.
"""
import re

ARTICLE = re.compile(r"^Article (\d+[a-z]*)$")
DIVISION = re.compile(r"^(CHAPTER|TITLE|SECTION|Section|PART) ([IVXLC]+|\d+)[A-Za-z]?$")
ANNEX = re.compile(r"^ANNEX(?: ([IVXLC]+[a-z]?))?$")
WHEREAS = re.compile(r"^Whereas:?$")
DONE = re.compile(r"^Done at .+")
CUT = re.compile(r"^\[이 부속서의 나머지 (\d+)줄은 싣지 않음\]$")  # 받아 둘 때 뺀 줄의 수(tools/archive/acts.py의 trim)
META = re.compile(r"^\[[^\]]+\]")                       # 저장할 때 붙인 머리 줄([주소] 등)
FILE_NAME = re.compile(r"^\S+\.fmx\.xml$")               # 받아 온 파일의 이름이 글에 섞인 줄
MARK_LINE = re.compile(r"^[▼►]\S*(?: —+)?$")            # 통합본의 개정 표시만 있는 줄
INLINE_MARK = re.compile(r"\s*(?:►\S+|◄)\s*")
LEAD = re.compile(r"^(\d+[a-z]?\.|\(\s?\*?\d+[a-z]?\s?\)|\([a-z]{1,3}\)|\([ivxlc]+\)|[—–•-])$")  # 번호나 줄표만 있는 줄
NOTE = re.compile(r"^(\(\s?\*?\d+\s?\)\s+\S|ELI: |ISSN )")
TITLE_MAX = 160
ROMAN = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100}


def roman(text):
    """로마 숫자를 수로. 로마 숫자가 아니면 0."""
    total, last = 0, 0
    for letter in reversed(text.upper()):
        value = ROMAN.get(letter)
        if not value:
            return 0
        total += -value if value < last else value
        last = max(last, value)
    return total


def lines_of(text):
    """글의 줄에서 머리 줄과 개정 표시를 빼고, 번호만 있는 줄을 다음 줄과 이어 돌려준다.

    번호만 있는 줄 다음이 조나 부속서, 장의 머리이거나 뺀 줄의 표시이면 잇지 않는다
    (부속서를 번호 줄에서 끊어 받아 두면 그 번호가 다음 부속서의 머리에 붙어 부속서가 갈리지 않았다). 뺀 줄의 표시는 그대로 돌려준다(parts가 읽는다).
    """
    found, lead = [], ""
    for raw in str(text).splitlines():
        line = INLINE_MARK.sub(" ", raw).strip()
        if CUT.match(line):
            found += [lead, line] if lead else [line]
            lead = ""
            continue
        if not line or META.match(line) or MARK_LINE.match(raw.strip()) or FILE_NAME.match(line):
            continue
        if LEAD.match(line):
            lead = f"{lead} {line}".strip()
            continue
        if lead and (ARTICLE.match(line) or DIVISION.match(line) or ANNEX.match(line)):
            found.append(lead)
            lead = ""
        found.append(f"{lead} {line}".strip())
        lead = ""
    if lead:
        found.append(lead)
    return found


def _is_title(line, following):
    """조나 부속서의 이름으로 볼 줄인가: 짧고, 문장처럼 끝나지 않고, 번호로 시작하지 않는다."""
    if not following or len(line) > TITLE_MAX or ARTICLE.match(line) or DIVISION.match(line) or ANNEX.match(line):
        return False
    return not re.match(r"^(\d+[a-z]?\.|\()", line) and not line.endswith((".", ":", ";", ","))


def _new(kind, key, label):
    return {"id": key, "kind": kind, "label": label, "title": "", "blocks": []}


def parts(text):
    """글을 조각의 목록으로 나눈다. 조각은 {"id", "kind", "label", "title", "blocks"}다. 받아 둘 때 뒷부분을 뺀 부속서에는 "cut"(뺀 줄 수)이 붙는다.

    kind: front(제목과 근거), recitals(전문), division(장·절 제목), article(조), closing(맺음), annex(부속서), notes(각주)
    """
    lines = lines_of(text)
    found = [_new("front", "front", "")]
    notes = _new("notes", "notes", "")
    in_annex, divisions, seen = False, 0, set()

    def start(part):
        base, number = part["id"], 2
        while part["id"] in seen:  # 같은 번호가 또 나오면(드문 일이다) 뒤에 차례를 붙여 가린다
            part["id"] = f"{base}-{number}"
            number += 1
        seen.add(part["id"])
        found.append(part)

    index = 0
    while index < len(lines):
        line = lines[index]
        if CUT.match(line):
            found[-1]["cut"] = found[-1].get("cut", 0) + int(CUT.match(line).group(1))
            index += 1
            continue
        following = lines[index + 1] if index + 1 < len(lines) else ""
        part = None
        if ANNEX.match(line):
            in_annex = True
            part = _new("annex", f"annex-{(ANNEX.match(line).group(1) or '0').lower()}", line)
        elif in_annex:
            pass
        elif ARTICLE.match(line):
            part = _new("article", f"art-{ARTICLE.match(line).group(1)}", line)
        elif DIVISION.match(line):
            divisions += 1
            part = _new("division", f"div-{divisions}", line)
        elif WHEREAS.match(line):
            part = _new("recitals", "recitals", "Whereas")
        elif DONE.match(line):
            part = _new("closing", "closing", "")
            part["blocks"].append(line)
        if part is None:
            found[-1]["blocks"].append(line)
            index += 1
            continue
        if part["kind"] in ("article", "annex", "division") and _is_title(following, lines[index + 2:index + 3] or part["kind"] == "division"):
            part["title"] = following
            index += 1
        start(part)
        index += 1
    # 각주: 맺음에 섞인 것과 글의 맨 끝에 이어진 것을 한 조각으로 모은다
    for part in found:
        if part["kind"] == "closing":
            notes["blocks"] += [block for block in part["blocks"] if NOTE.match(block)]
            part["blocks"] = [block for block in part["blocks"] if not NOTE.match(block)]
    tail = []
    last = found[-1]
    while last["kind"] in ("annex", "article") and last["blocks"] and NOTE.match(last["blocks"][-1]):
        tail.insert(0, last["blocks"].pop())
    notes["blocks"] += tail
    if notes["blocks"]:
        found.append(notes)
    return [part for part in found if part["blocks"] or part["title"] or part["kind"] == "division"]


def label_ko(part):
    """조각의 이름을 국문으로: Article 7 → 제7조, ANNEX I → 부속서 I, CHAPTER II → 제2장."""
    kind, label = part["kind"], part["label"]
    if kind == "article":
        return f"제{ARTICLE.match(label).group(1)}조"
    if kind == "annex":
        number = ANNEX.match(label).group(1)
        return f"부속서 {number}" if number else "부속서"
    if kind == "division":
        word, number = DIVISION.match(label).group(1), DIVISION.match(label).group(2)
        unit = {"CHAPTER": "장", "TITLE": "편", "SECTION": "절", "Section": "절", "PART": "부"}[word]
        return f"제{roman(number) or number}{unit}"
    return {"front": "제목과 근거", "recitals": "전문", "closing": "맺음", "notes": "각주"}.get(kind, label)
