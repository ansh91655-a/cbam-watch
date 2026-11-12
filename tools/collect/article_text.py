"""게시글 화면에서 뽑은 줄들 가운데 본문만 남긴다. 받기와 쓰기는 하지 않는다(tools.collect.articles가 한다).

게시글 화면에는 사이트의 메뉴와 바닥글이 함께 실려 있다. 목록 화면에서 본 제목이 적힌 줄부터
본문이 끝났음을 알리는 줄(만족도 조사, 이전글·다음글, 목록) 앞까지를 본문으로 본다.
"""
import re

# 이 글귀로 시작하는 줄이 나오면 본문이 끝난 것이다
STOP_STARTS = ("만족도 조사", "이 페이지에서 제공하는 정보에 만족하셨습니까")
# 줄 전체가 이 글자일 때만 끝으로 본다(본문 문장 안의 같은 낱말에는 걸리지 않게)
STOP_LINES = ("목록", "목록으로", "이전글", "다음글", "이전 글", "다음 글")
# 제목 줄 바로 뒤에 이런 글자가 나오면 그 줄이 게시글의 머리다(메뉴나 지나온 길에 적힌 같은 제목과 가린다)
META_MARKS = ("등록일", "작성일", "게시일", "담당부서", "조회수", "첨부파일")
META_WINDOW = 12
MAX_LINES = 300
MAX_CHARS = 9000
MIN_CHARS = 200


def flat(text):
    """띄어쓰기와 줄바꿈을 뺀 글자. 화면마다 다른 띄어쓰기를 견디려는 것이다."""
    return re.sub(r"\s+", "", str(text))


def license_line(lines, marks):
    """이용 조건을 밝힌 줄을 찾는다(예: 공공누리 1유형). 없으면 빈 글."""
    wanted = [flat(mark) for mark in marks if flat(mark)]
    for line in lines:
        squeezed = flat(line)
        if any(mark in squeezed for mark in wanted):
            return line.strip()
    return ""


def terms_hints(lines, limit=3, width=100):
    """이용 조건의 글귀를 찾지 못했을 때, 화면이 저작권을 어떻게 적었는지 알 수 있게 그 낱말이 든 줄을 몇 개 돌려준다."""
    found = [line.strip()[:width] for line in lines if any(word in flat(line) for word in ("공공누리", "KOGL", "저작권", "저작물"))]
    return found[:limit]


def _meta_distance(lines, index):
    """이 줄에서 몇 줄 뒤에 등록일 같은 글자가 처음 나오는가. 가까이에 없으면 None."""
    for offset, line in enumerate(lines[index + 1:index + 1 + META_WINDOW], start=1):
        squeezed = flat(line)
        if any(mark in squeezed for mark in META_MARKS):
            return offset
    return None


def _start(lines, title):
    """게시글의 머리 줄 번호. 제목은 메뉴, 지나온 길, 본문에도 적혀 있을 수 있다.

    등록일 같은 글자가 가장 가까이 뒤따르는 줄을 머리로 본다. 그런 줄이 없으면 마지막으로 나온 줄이다.
    """
    wanted = flat(title)
    if not wanted:
        return None
    hits = [index for index, line in enumerate(lines) if wanted in flat(line)]
    if not hits:
        return None
    near = [(distance, index) for index in hits for distance in [_meta_distance(lines, index)] if distance is not None]
    return min(near)[1] if near else hits[-1]


def _is_stop(line, extra):
    text = line.strip()
    return text in STOP_LINES or text.startswith(STOP_STARTS) or any(mark and flat(mark) in flat(text) for mark in extra)


def body(lines, title, stops=()):
    """(본문 줄들, 제목 줄을 찾았는가)를 돌려준다. 제목을 찾지 못하면 화면의 줄을 처음부터 쓴다.

    stops는 그 출처에서만 쓰는 끝 표시다(이용 조건을 적은 줄 등). 길이는 MAX_LINES줄, MAX_CHARS자까지다.
    """
    start = _start(lines, title)
    kept = []
    size = 0
    for line in lines[start or 0:]:
        if kept and _is_stop(line, stops):
            break
        if len(kept) >= MAX_LINES or size + len(line) > MAX_CHARS:
            break
        kept.append(line)
        size += len(line)
    return kept, start is not None


def long_enough(lines):
    """본문으로 볼 만큼 글이 있는가(첨부 파일만 있는 글, 빈 화면을 가린다)."""
    return sum(len(flat(line)) for line in lines) >= MIN_CHARS
