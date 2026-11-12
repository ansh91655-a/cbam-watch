"""PDF에서 읽은 줄들을 문단으로 묶는다. 번역은 이 문단마다 붙는다.

PDF의 글은 화면 너비에서 줄이 바뀌고 문단 사이에 빈 줄이 없는 곳이 많다. 그래서 이렇게 가른다.
- 빈 줄은 덩어리의 경계다.
- 덩어리 안에서는 문장이 끝난 짧은 줄(문단의 마지막 줄) 다음에 새 문장이 시작하면 문단을 가른다. 쌍반점으로 끝난 줄(목록의 항목) 다음에서도 가른다.
  줄이 꽉 찬 채로 문장이 끝난 곳은 가르지 않는다(가르더라도 문장의 경계라서 번역에는 지장이 없지만, 문단을 되도록 원문대로 두려는 것이다).
- 문장부호 없이 끝난 짧은 줄 다음에 대문자로 시작하는 줄이 오면 가른다(번호 없는 작은 제목, 표의 칸). 식의 기호로 시작하는 줄에서도 가른다.
- 글머리표나 번호만 따로 적힌 줄("•", "(a)", "1.")은 다음 문단의 머리에 붙인다.
- 붙임표로 끝난 줄(non- / legislative)은 띄우지 않고 잇는다.
"""
import re

GLYPHS = "•◦▪■●○➢►✓–—-"
BULLET = re.compile(r"^(?:[•◦▪■●○➢►✓–—-]|o)$")  # 글머리표만 있는 줄. 둘째 단계의 글머리표는 글자 o로 뽑힌다
BULLET_START = re.compile(r"^[•◦▪■●○➢►✓]\s*\S")
MARKER = re.compile(r"^(?:\([a-z]{1,3}\)|\([ivxlc]{1,5}\)|\(\d{1,2}\)|\d{1,2}[.)]|[a-z][.)])$")
ABBREVIATION = re.compile(r"(?:^|[\s(])(?:e\.g|i\.e|etc|cf|No|Nos|Art|Arts|para|paras|resp|approx|vs|incl|Fig|Eq|Ref|ref|p|pp)\.$")
TERMINAL = ".?!"
CLOSERS = "”’\"')]»"
OPENERS = "“‘\"'([«"
MATH = re.compile(r"^[\U0001D400-\U0001D7FF]")  # 식의 기호로 시작하는 줄(식, 기호의 풀이)은 새 문단이다
WORDS = re.compile(r"[A-Za-z]{3,}")
SHORT = 0.85         # 줄의 길이가 보통 너비의 이 비율보다 짧으면 문단의 마지막 줄로 본다
LABEL = 0.6          # 이보다 짧고 문장부호 없이 끝난 줄 다음에 대문자로 시작하는 줄이 오면 제목이나 표의 칸으로 보고 가른다
DEFAULT_WIDTH = 90


def typical_width(lines):
    """꽉 찬 줄의 보통 길이(글자 수). 긴 줄들의 90번째 백분위수다."""
    lengths = sorted(len(line.strip()) for line in lines if len(line.strip()) >= 30)
    return lengths[int(0.9 * (len(lengths) - 1))] if len(lengths) >= 20 else DEFAULT_WIDTH


def is_upper(text):
    """글자가 모두 대문자인 줄인가."""
    letters = [letter for letter in text if letter.isalpha()]
    return len(letters) >= 3 and all(letter.isupper() for letter in letters)


def ending(line):
    """줄의 끝 글자. 닫는 따옴표와 괄호는 건너뛴다."""
    text = line.rstrip()
    while text and text[-1] in CLOSERS:
        text = text[:-1]
    return text[-1:]


def ends_sentence(line):
    return ending(line) in TERMINAL and ending(line) != "" and not ABBREVIATION.search(line.rstrip())


def starts_fresh(line):
    """새 문장이나 새 항목으로 시작하는 줄인가: 대문자, 수, 여는 따옴표나 괄호, 글머리표."""
    first = line.lstrip()[:1]
    return bool(first) and (first.isupper() or first.isdigit() or first in OPENERS or first in GLYPHS)


def is_lead(text):
    """글머리표나 번호만 있는 줄인가."""
    return bool(BULLET.match(text) or MARKER.match(text))


def joined(lines):
    """한 문단의 줄들을 한 줄로 잇는다."""
    text = ""
    for line in lines:
        line = line.strip()
        if not text:
            text = line
        elif text.endswith("-") and len(text) > 1 and text[-2].isalpha() and line[:1].islower():
            text += line
        else:
            text += " " + line
    return re.sub(r"\s+", " ", text).strip()


def chunks(lines):
    """빈 줄로 나뉜 덩어리들."""
    found, current = [], []
    for line in lines:
        if line.strip():
            current.append(line.strip())
        elif current:
            found.append(current)
            current = []
    if current:
        found.append(current)
    return found


def paragraphs(chunk, width):
    """빈 줄 없이 이어진 줄들을 문단(줄의 목록)으로 가른다."""
    found, current = [], []
    for index, line in enumerate(chunk):
        symbol = MATH.match(line) and (WORDS.search(line) or any(WORDS.search(earlier) for earlier in current))  # 기호의 풀이. 식만 이어진 줄은 한 문단으로 둔다
        if is_lead(line) or ((BULLET_START.match(line) or symbol) and current and not is_lead(current[-1])):
            if current:
                found.append(current)
            current = []
        current.append(line)
        following = chunk[index + 1] if index + 1 < len(chunk) else ""
        if not following or is_lead(line):
            continue
        last = ending(line)
        closed = ends_sentence(line) or last == ":"
        label = (len(line) < LABEL * width and line[:1].isupper() and following[:1].isupper() and last.isalnum()
                 and not (is_upper(line) and is_upper(following)))  # 제목처럼 생긴 짧은 줄. 대문자로만 된 제목이 두 줄에 걸친 것은 가르지 않는다
        if last == ";" or label or (closed and len(line) < SHORT * width and starts_fresh(following)):
            found.append(current)
            current = []
    if current:
        found.append(current)
    return found


def blocks(lines, width=DEFAULT_WIDTH):
    """줄들(빈 줄이 섞인 것)을 문단의 목록으로. 글머리표만 있는 문단은 다음 문단의 머리에 붙인다."""
    found, lead = [], ""
    for chunk in chunks(lines):
        for paragraph in paragraphs(chunk, width):
            if is_lead(paragraph[0]) and len(paragraph) > 1:
                paragraph = [f"{paragraph[0]} {paragraph[1]}"] + paragraph[2:]
            text = joined(paragraph)
            if is_lead(text):
                lead = text  # 글이 뒤따르는 글머리표. 여럿이 잇따르면(글이 빠진 것) 하나만 남긴다
                continue
            found.append(f"{lead} {text}" if lead else text)
            lead = ""
    return found
