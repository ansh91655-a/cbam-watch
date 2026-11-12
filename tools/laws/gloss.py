"""번역문의 전문용어에 영문을 괄호로 병기한다: 내재배출량 → 내재배출량(embedded emissions).

번역 자료(data/laws-ko/)에는 국문만 두고, 사이트에 싣는 자료를 만들 때 이 프로그램이 병기를 붙인다.
그래서 병기가 모든 법령에 같은 규칙으로 붙고, 용어집을 고치면 화면도 따라 바뀐다.
- 병기하는 낱말: 용어집(language/glossary.json)에서 core로 표시한 낱말(CBAM의 전문용어).
- 한 조각(조 하나, 부속서 하나) 안에서 처음 나올 때 한 번만 붙인다. 원문 문단에 그 영문이 실제로 있을 때만 붙인다.
- 더 긴 낱말의 일부인 자리에는 붙이지 않는다("내재배출량" 안의 "배출량").
"""
from tools.laws import terms


def annotate(blocks):
    """한 조각의 문단들 [[원문, 국문], ...]에 병기를 붙여 새 목록으로 돌려준다."""
    shown, result = set(), []
    for english, korean in blocks:
        if not korean or korean == english:
            result.append([english, korean])
            continue
        taken, inserts = [], []
        for entry in terms.found(english):
            place = next(((start, end) for start, end in terms.spans(korean, entry["ko"])
                          if not any(start < other_end and other_start < end for other_start, other_end in taken)), None)
            if place is None:
                continue
            taken.append(place)
            if entry["core"] and entry["show"] not in shown and korean[place[1]:place[1] + 1] != "(" and entry["show"].lower() not in korean.lower():
                shown.add(entry["show"])
                inserts.append((place[1], entry["show"]))
        for at, show in sorted(inserts, reverse=True):
            korean = f"{korean[:at]}({show}){korean[at:]}"
        result.append([english, korean])
    return result
