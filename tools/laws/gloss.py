"""번역문의 전문용어에 영문을 괄호로 병기한다: 내재배출량 → 내재배출량(embedded emissions).

번역 자료(data/laws-ko/)에는 국문만 두고, 사이트에 싣는 자료를 만들 때 이 프로그램이 병기를 붙인다.
그래서 병기가 모든 법령에 같은 규칙으로 붙고, 용어집을 고치면 화면도 따라 바뀐다.
- 병기하는 낱말: 용어집(language/glossary.json)에서 core로 표시한 낱말(CBAM의 전문용어).
- 한 조각(조 하나, 부속서 하나) 안에서 처음 나올 때 한 번만 붙인다. 원문 문단에 그 영문이 실제로 있을 때만 붙인다.
- 더 긴 낱말의 일부인 자리에는 붙이지 않는다. 용어집의 더 긴 낱말이 먼저 자리를 잡고("내재배출량" 안의 "배출량"),
  용어집에 없는 합성어 안도 가른다: 앞이 다른 글자에 붙어 있거나("내재무상할당량"의 "무상할당") 뒤가 조사가 아닌 글자로 이어지면
  ("검증기관"의 "검증", "배출권거래제"의 "배출권", "제출일"의 "제출", "인정받은"의 "인정") 그 자리는 건너뛰고 다음에 깨끗이 나온 자리에 붙인다.
- 용어집이 띄어 적은 표기는 붙여 쓴 것도 같은 낱말로 본다("부적합 사항" = "부적합사항").
"""
import re

from tools.laws import terms

HANGUL = re.compile(r"[가-힣]+")
JOINED = re.compile(r"[가-힣A-Za-z0-9]")
# 낱말 뒤에 붙는 조사와 서술격 조사. 이것으로만 된 꼬리는 낱말의 끝으로 본다(사업장별로, 등록부상의, 신고인인가)
PARTICLE = re.compile(
    r"(?:들)?(?:은|는|이|가|을|를|의|도|만|뿐|나|이나|든|이든|당|별|상|에|에서|에게|께|와|과|로|으로|로서|으로서|로써|으로써|로부터|으로부터|부터|까지"
    r"|마다|보다|처럼|만큼|조차|이다|이며|이고|이거나|이어야|이라|라|이란|란|인가|인지|이라는|라는|이라면|라면|였다|이었다)"
    r"(?:은|는|이|가|을|를|의|도|만|나|로|으로|서|뿐)?$")
COPULA = re.compile(r" (?:경우|수|때|것|귀하|여러분|이른바)")  # "…인 경우", "…일 수 있다". 신고인·제출일 같은 낱말과 가른다


def _places(korean, forms):
    """국문 글에서 표기들이 나온 자리 [(시작, 끝)]. 표기 안의 띄어쓰기는 있어도 없어도 된다. 긴 자리부터."""
    found = set()
    for form in forms:
        letters = [re.escape(piece) for piece in form.split()]
        if letters:
            found |= {(match.start(), match.end()) for match in re.finditer(r"\s*".join(letters), korean)}
    return sorted(found, key=lambda place: (place[0] - place[1], place[0]))


def _clean(korean, start, end):
    """낱말이 제 모습으로 나온 자리인가(합성어의 일부가 아닌가)."""
    if korean[end:end + 1] == "(" or (start and JOINED.match(korean[start - 1])):
        return False
    tail = HANGUL.match(korean, end)
    if not tail:
        return True
    if tail.group(0) in ("인", "일"):
        return bool(COPULA.match(korean, tail.end()))
    return bool(PARTICLE.match(tail.group(0)))


def annotate(blocks):
    """한 조각의 문단들 [[원문, 국문], ...]에 병기를 붙여 새 목록으로 돌려준다."""
    shown, result = set(), []
    for english, korean in blocks:
        if not korean or korean == english:
            result.append([english, korean])
            continue
        entries = terms.found(english)
        spots = sorted(((place, index) for index, entry in enumerate(entries) for place in _places(korean, entry["ko"])),
                       key=lambda spot: (spot[0][0] - spot[0][1], spot[0][0]))
        taken, held = [], {}
        for (start, end), index in spots:   # 긴 낱말부터 자리를 잡는다. 잡힌 자리 안의 짧은 낱말은 세지 않는다
            if not any(start < other_end and other_start < end for other_start, other_end in taken):
                taken.append((start, end))
                held.setdefault(index, []).append((start, end))
        inserts = []
        for index, entry in enumerate(entries):
            if not entry["core"] or entry["show"] in shown or entry["show"].lower() in korean.lower():
                continue
            place = next((place for place in sorted(held.get(index, [])) if _clean(korean, *place)), None)
            if place:
                shown.add(entry["show"])
                inserts.append((place[1], entry["show"]))
        for at, show in sorted(inserts, reverse=True):
            korean = f"{korean[:at]}({show}){korean[at:]}"
        result.append([english, korean])
    return result
