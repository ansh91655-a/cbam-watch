"""화면이 이용 조건을 밝혔는지 가린다. 받기와 쓰기는 하지 않는다(tools.collect.articles가 한다).

출처 대장의 articles에 적힌 규칙으로 본다.
- license: 화면의 글이나 그림의 대체 글에 있어야 하는 글귀의 목록. 예: "공공누리 1유형", "Open Government Licence v3.0".
  공공누리의 다른 유형(2~4유형)의 글귀가 같은 화면에 함께 있으면 받아들이지 않는다. 유형마다의 안내문을 모두 실어 두고
  그 가운데 하나만 보여 주는 사이트가 있어, 글자만으로는 어느 것이 그 글의 조건인지 가릴 수 없기 때문이다.
- field: 글마다 유형을 적는 칸. {"label": "공공누리", "accept": ["1유형", "제1유형"]} 꼴이다.
  그 칸의 값이 하나뿐이고 accept에 있을 때만 받아들인다.
- termsUrl: 이용 조건을 한 번만 적어 두는 화면의 주소(저작권 안내 화면 등). 글의 화면에 글귀가 없을 때 그 화면에서 찾는다.
  적지 않으면 그 출처의 목록 화면(url)에서 찾는다.
"""
import re

from tools.collect.article_text import flat

# 출처만 밝히면 누구나 쓸 수 있는 공공누리 유형은 1유형이다. 아래 글귀가 함께 있는 화면은 가릴 수 없는 화면으로 본다.
KOGL_OTHERS = ("공공누리2유형", "공공누리제2유형", "공공누리3유형", "공공누리제3유형", "공공누리4유형", "공공누리제4유형")
HINT_WORDS = ("공공누리", "kogl", "저작권", "저작물", "copyright", "licence", "license", "creativecommons", "cc0",
              "hergebruik", "urheberrecht", "re-use", "reuse", "©")
ATTRIBUTE = re.compile(r"""\b(?:alt|title)\s*=\s*(?:"([^"]{2,200})"|'([^']{2,200})')""", re.IGNORECASE)
FIELD_VALUE_LIMIT = 12  # 칸의 값으로 볼 글자 수의 한도("1유형", "제1유형" 같은 짧은 값만 본다)


def attribute_texts(html):
    """그림의 대체 글과 풀이 글(alt, title)의 목록. 공공누리 표시는 글이 아니라 그림으로 붙어 있는 일이 많다."""
    seen, found = set(), []
    for double, single in ATTRIBUTE.findall(html or ""):
        text = (double or single).strip()
        if text and text not in seen:
            seen.add(text)
            found.append(text)
    return found


def marked(texts, marks):
    """(글귀가 든 글, 가릴 수 없는가)를 돌려준다. texts는 화면의 줄과 대체 글이다.

    marks의 글귀가 든 첫 글을 찾는다. 같은 화면에 공공누리의 다른 유형이 함께 적혀 있으면 빈 글과 True를 돌려준다.
    """
    wanted = [flat(mark).lower() for mark in marks if flat(mark)]
    found = next((text.strip() for text in texts if any(mark in flat(text).lower() for mark in wanted)), "")
    if not found:
        return "", False
    if any(other in flat(text) for text in texts for other in KOGL_OTHERS):
        return "", True
    return found, False


def field_values(lines, label):
    """이름이 label인 칸에 적힌 값들. 이름과 값이 한 줄에 있거나("공공누리: 1유형") 이어진 두 줄에 있는 것을 모두 모은다."""
    wanted = flat(label)
    values = []
    for index, line in enumerate(lines):
        squeezed = flat(line)
        if squeezed == wanted and index + 1 < len(lines):
            value = flat(lines[index + 1])
        elif squeezed.startswith(wanted):
            value = squeezed[len(wanted):].lstrip(":：-·")
        else:
            continue
        if 0 < len(value) <= FIELD_VALUE_LIMIT and value not in values:
            values.append(value)
    return values


def field_terms(lines, rule):
    """글마다 유형을 적는 칸의 값이 받아들이는 값이면 그 값을, 아니면 빈 글을 돌려준다.

    유형으로 보이는 값("유형"이 든 값)이 둘 이상 적혀 있으면 어느 것인지 가릴 수 없으므로 받아들이지 않는다.
    """
    label = (rule or {}).get("label", "")
    accept = {flat(value) for value in (rule or {}).get("accept", [])}
    if not label or not accept:
        return ""
    kinds = [value for value in field_values(lines, label) if "유형" in value]
    return kinds[0] if len(kinds) == 1 and kinds[0] in accept else ""


def hints(texts, limit=4, width=110):
    """이용 조건을 찾지 못했을 때, 화면이 저작권을 어떻게 적었는지 알 수 있게 그런 낱말이 든 글을 몇 개 돌려준다."""
    found = []
    for text in texts:
        squeezed = flat(text).lower()
        cut = text.strip()[:width]
        if any(word in squeezed for word in HINT_WORDS) and cut not in found:
            found.append(cut)
    return found[:limit]
