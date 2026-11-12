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
# 게시글의 머리에 붙는 칸 가운데 싣지 않는 것: 담당자·작성자·등록자의 이름과 전화번호(요약에 쓰지 않는 개인 연락처), 조회수.
# 칸의 이름과 값이 한 줄에 있기도 하고("담당자 홍길동") 이어진 두 줄에 있기도 하다("담당자" 다음 줄에 "홍길동").
DROP_STARTS = ("담당자", "연락처", "조회수", "작성자", "등록자", "전화번호")
# 전화번호만 적힌 줄(02-123-4567, 044-123-4567, +82-2-123-4567). 띄어쓰기를 뺀 글자에 맞춘다
PHONE = re.compile(r"^(?:\+82[-.]?\d{1,2}|\(?0\d{1,2}\)?)[-.]?\d{3,4}[-.]?\d{4}$")
# 숫자만 적힌 줄. 머리 바로 아래에서는 이름 없이 붙은 조회수나 내려받은 횟수다
COUNT = re.compile(r"^[\d,]{1,9}$")
# 목록 화면의 링크 글자 안에 통째로 든 줄을 제목으로 볼 때, 그 줄이 적어도 이만큼은 길어야 한다
TITLE_PART = 10
MAX_LINES = 400
MAX_CHARS = 12000
MIN_CHARS = 200


def flat(text):
    """띄어쓰기와 줄바꿈을 뺀 글자. 화면마다 다른 띄어쓰기를 견디려는 것이다."""
    return re.sub(r"\s+", "", str(text))


def _meta_distance(lines, index):
    """이 줄에서 몇 줄 뒤에 등록일 같은 글자가 처음 나오는가. 가까이에 없으면 None."""
    for offset, line in enumerate(lines[index + 1:index + 1 + META_WINDOW], start=1):
        squeezed = flat(line)
        if any(mark in squeezed for mark in META_MARKS):
            return offset
    return None


def _title_hits(lines, title):
    """제목이 적힌 줄의 번호들.

    제목이 통째로 든 줄을 찾는다. 없으면 거꾸로, 제목 안에 통째로 든 줄 가운데 가장 긴 것을 찾는다:
    목록 화면의 링크 글자에는 제목 말고도 날짜, 글쓴이, '더 보기' 같은 글자가 붙어 있을 수 있기 때문이다.
    """
    wanted = flat(title)
    if not wanted:
        return []
    hits = [index for index, line in enumerate(lines) if wanted in flat(line)]
    if hits:
        return hits
    inside = [(len(flat(line)), index) for index, line in enumerate(lines) if len(flat(line)) >= TITLE_PART and flat(line) in wanted]
    longest = max((length for length, _ in inside), default=0)
    return [index for length, index in inside if length == longest]


def _start(lines, title):
    """게시글의 머리 줄 번호. 제목은 메뉴, 지나온 길, 본문에도 적혀 있을 수 있다.

    등록일 같은 글자가 가장 가까이 뒤따르는 줄을 머리로 본다. 그런 줄이 없으면 마지막으로 나온 줄이다.
    """
    hits = _title_hits(lines, title)
    if not hits:
        return None
    near = [(distance, index) for index in hits for distance in [_meta_distance(lines, index)] if distance is not None]
    return min(near)[1] if near else hits[-1]


def _is_stop(line, extra):
    text = line.strip()
    return text in STOP_LINES or text.startswith(STOP_STARTS) or any(mark and flat(mark) in flat(text) for mark in extra)


def body(lines, title, stops=()):
    """(본문 줄들, 제목 줄을 찾았는가, 길어서 잘랐는가)를 돌려준다. 제목을 찾지 못하면 화면의 줄을 처음부터 쓴다.

    stops는 그 출처에서만 쓰는 끝 표시다(이용 조건을 적은 줄 등). 길이는 MAX_LINES줄, MAX_CHARS자까지다.
    머리 바로 아래의 담당자, 작성자, 연락처, 조회수 칸과 전화번호만 적힌 줄은 싣지 않는다.
    제목을 찾지 못했을 때는 머리가 어디인지 모르므로 화면 어디에서든 그런 칸을 싣지 않는다.
    """
    start = _start(lines, title)
    kept, size = [], 0
    cut = value_next = False
    for offset, line in enumerate(lines[start or 0:]):
        if kept and _is_stop(line, stops):
            break
        if len(kept) >= MAX_LINES or size + len(line) > MAX_CHARS:
            cut = True
            break
        head = start is not None and 0 < offset <= META_WINDOW
        if head or start is None or value_next:
            squeezed = flat(line)
            if squeezed.startswith(DROP_STARTS):
                value_next = squeezed in DROP_STARTS  # 칸의 이름만 적힌 줄이면 값은 다음 줄에 있다
                continue
            if value_next:
                value_next = False
                continue
            if PHONE.match(squeezed) or (head and COUNT.match(squeezed)):
                continue
        kept.append(line)
        size += len(line)
    return kept, start is not None, cut


def long_enough(lines):
    """본문으로 볼 만큼 글이 있는가(첨부 파일만 있는 글, 빈 화면을 가린다)."""
    return sum(len(flat(line)) for line in lines) >= MIN_CHARS
