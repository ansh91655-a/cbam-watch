"""번역 하나를 뜻이 틀리게 바꾼다. 검수가 제대로 읽는지 재는 데만 쓴다(tools.laws.verify). 바꾼 글은 번역 자료에 넣지 않는다.

바꾸는 방법은 셋이다. 어느 것이든 원문과 견줘 읽으면 틀린 것이 드러나야 한다.
- 뜻이 뒤집히는 말로 바꾸기(flip): 의무와 허용(하여야 한다 ↔ 할 수 있다), 할 수 있음과 없음, 포함과 제외, 앞과 뒤, 이상과 이하, 늘고 줆, 직접과 간접, 수입과 수출 …
- 부정 빼기(negation): "…하지 아니한다" → "…한다"
- 문장 빼기(omission): 문장이 둘 넘는 번역에서 마지막 문장을 뺀다
"""
import re

# (찾는 식, 바꿀 글). 한 번역에서 한 곳만 바꾼다
FLIPS = [
    (r"하여야 한다", "할 수 있다"), (r"해야 한다", "할 수 있다"), (r"하여야 하며", "할 수 있으며"), (r"해야 하며", "할 수 있으며"),
    (r"할 수 있다", "하여야 한다"), (r"할 수 있으며", "하여야 하며"),
    (r"수 없다", "수 있다"), (r"하여서는 아니 된다", "하여야 한다"), (r"해서는 안 된다", "해야 한다"),
    (r"포함한다", "제외한다"), (r"포함된다", "제외된다"), (r"포함하여", "제외하고"), (r"제외한다", "포함한다"), (r"제외된다", "포함된다"), (r"제외하고", "포함하여"),
    (r"이전에", "이후에"), (r"이후에", "이전에"), (r"(?<=일)까지", "부터"), (r"(?<=일)부터", "까지"),
    (r"(?<=[0-9%])(\s?[가-힣A-Za-z]{0,3}\s?)이상", r"\1이하"), (r"(?<=[0-9%])(\s?[가-힣A-Za-z]{0,3}\s?)이하", r"\1이상"),
    (r"초과", "미만"), (r"미만", "초과"), (r"최대", "최소"), (r"최소", "최대"), (r"증가", "감소"), (r"감소", "증가"),
    (r"직접배출량", "간접배출량"), (r"간접배출량", "직접배출량"), (r"직접", "간접"), (r"간접", "직접"),
    (r"수입자", "수출자"), (r"수입", "수출"), (r"제3국", "회원국"), (r"회원국", "제3국"),
    (r"높은", "낮은"), (r"낮은", "높은"), (r"가능하다", "불가능하다"), (r"필요하다", "필요하지 않다"), (r"매년", "매분기"), (r"분기마다", "해마다"),
]
NEGATIONS = [(r"하지 아니한다", "한다"), (r"하지 않는다", "한다"), (r"되지 아니한다", "된다"), (r"되지 않는다", "된다"),
             (r"하지 아니하며", "하며"), (r"하지 않으며", "하며"), (r"해당하지 않는다", "해당한다"), (r"아니다", "이다")]
SENTENCE_END = re.compile(r"(?<=[다요음임함됨])\.\s+")
MIN_CHARS = 30      # 이보다 짧은 번역은 바꾸지 않는다(제목, 표의 칸)
MIN_SENTENCE = 15   # 빼는 문장은 이보다 길어야 한다


def choices(korean):
    """이 번역을 틀리게 바꾸는 길들: [(바꾼 글, 방법)]"""
    korean = str(korean)
    if len(korean) < MIN_CHARS:
        return []
    found = []
    for kind, rules in (("flip", FLIPS), ("negation", NEGATIONS)):
        for pattern, replacement in rules:
            hit = re.search(pattern, korean)
            if hit:
                changed = korean[:hit.start()] + hit.expand(replacement) + korean[hit.end():]
                if changed != korean:
                    found.append((changed, kind))
    sentences = SENTENCE_END.split(korean)
    if len(sentences) >= 2 and len(sentences[-1]) >= MIN_SENTENCE:
        cut = korean[:korean.rindex(sentences[-1])].rstrip()
        if cut and cut != korean:
            found.append((cut, "omission"))
    return found


def spoil(korean, picker):
    """(바꾼 글, 방법)을 하나 고른다. 바꿀 길이 없으면 None. picker는 random.Random."""
    found = choices(korean)
    return picker.choice(found) if found else None
