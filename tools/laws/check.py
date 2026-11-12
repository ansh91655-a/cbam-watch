"""번역한 문단을 원문과 견줘 본다. 기계로 가릴 수 있는 잘못만 잡는다(사람의 감수를 대신하지 않는다).

막는 것(hard): 빈 번역, 옮기지 않은 글, 원문의 수가 빠진 것, 부속서·장의 로마 숫자가 빠진 것, 용어집이 쓰지 않기로 한 표기,
            원문에 핵심 용어(용어집의 core)가 나왔는데 번역에 그 국문 표기가 없는 것(모든 법령에서 같은 낱말을 쓰게 하려는 것).
알리는 것(soft): 원문에 없는 수가 번역에 있는 것, 길이가 지나치게 다른 것.

웹 주소 안의 낱말은 옮길 말도, 용어집과 견줄 말도 아니다(…/module-for-non-eu-installation-operators 의 installation).
번역이 영문 그대로 둔 용어(화면에 적힌 이름 “Third country Operator”, 역할 이름 Admin Operator)에는 국문 표기를 요구하지 않는다.
등록부 안내서는 화면의 이름을 원문대로 두게 되어 있다. 옮겨야 할 영문을 남긴 것인지는 검수(tools.laws.verify)가 본다.
핵심 용어가 다른 뜻으로 쓰인 자리(installation of wind turbines의 '설치')는 sources/translation.json의 senses에 적힌 표기를 쓰면 막지 않고 알린다.
용어집이 쓰지 않기로 한 표기도, 원문에 그 표기가 맞는 다른 낱말이 있으면(accuracy and precision의 '정밀도', the CBAM rules의 'CBAM 규칙') senses를 보고 알리기만 한다.
옮길 글이 없어 원문대로 둔 줄은 '옮기지 않음'으로 막지 않는다: 식(E = eec + el – esca, EFheat,default = 62,3 t CO2e / TJ)과 화면에 뜨는 번호 붙은 알림 글(VAL748 The attribute …).
PDF에서 각주 번호가 수 뒤에 붙어 버린 것(Equation 5516 = Equation 55와 각주 16)은 번역이 "55[16]"으로 갈라 적으면 수가 빠진 것으로 보지 않는다.
주소에는 앞머리 없이 적은 사이트 이름(example.com), 전자우편 주소, 파일 이름(….xlsx)도 든다.
등록부 안내서(screen)에서는 따옴표 안의 화면 이름만 늘어놓은 줄(“Start Request for change”.)도 원문대로 둘 수 있다.
그래도 남는 한두 문단은 sources/translation.json의 excused에 열쇠와 까닭을 적어 예외로 둔다: 그 문단은 용어와 '옮기지 않음'으로는 막지 않고 알리기만 한다.
주소와 번호만 있는 줄(주소 하나만 적은 각주)은 옮기지 않고 그대로 싣는다. 주소 안의 수는 번역에 그대로 남아 있어야 한다.
"""
import collections
import re

from tools.check import term_check
from tools.laws import plan, terms

DIGITS = re.compile(r"\d+")
HANGUL = re.compile(r"[가-힣]")
WORD = re.compile(r"(?<![A-Za-z])[a-z]{4,}")  # 소문자로 시작하는 낱말. 사람 이름이나 약어만 있는 줄(Ursula VON DER LEYEN)과 가린다
LETTERS = re.compile(r"[A-Za-z]{2,}")
THOUSANDS = re.compile(r"(?<=\d)[   ,](?=\d{3}(?!\d))")
URL = re.compile(r"(?:https?://|www\.)\S+|\S+@\S+\.\S+"
                 r"|(?<![A-Za-z0-9@])(?:[A-Za-z0-9_-]+\.)+(?:com|org|net|eu|int|gov|edu|io|info|xlsx|xls|pdf|docx|doc|csv|zip|xml|json|pptx|txt)\b(?:/\S*)?")
QUOTED = re.compile(r"[“\"][^”\"]*[”\"]")
WAIVABLE = ("용어집의 표기가 없음", "용어: ", "국문으로 옮기지 않음")  # 예외로 둔 문단에서 막지 않는 것(수와 번호는 그대로 막는다)
RELATION = re.compile(r"[=≤≥]")
RUNNING = re.compile(r"[A-Za-z]{3,}\s+[A-Za-z]{3,}")   # 낱말 둘이 나란히 놓인 곳(식에는 없고 글에는 있다)
CODED = re.compile(r"^\W*[A-Z]{2,}[0-9]{2,}\b")       # 화면에 뜨는 알림 글의 번호(VAL748)
ROMAN_REF = re.compile(r"\b(?:Annex(?:es)?|ANNEX|Chapter|CHAPTER|Title|Part|Section)\s+([IVXLC]+)\b")
# 글자로 적힌 수와 달 이름. 번역에서는 숫자로 적히므로 '원문에 없는 수'로 보지 않는다
SPELLED = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
           "first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5, "sixth": 6, "seventh": 7, "eighth": 8, "ninth": 9, "tenth": 10,
           "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "ninety": 90, "hundred": 100, "twentieth": 20, "single": 1, "both": 2,
           "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6, "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12}
RATIO = (0.2, 2.2)  # 번역 길이 ÷ 원문 길이가 이 범위를 벗어나면 알린다(원문이 40자보다 길 때)

_terms = None


def prose(text):
    """웹 주소를 뺀 글."""
    return URL.sub(" ", str(text))


def needs(text):
    """옮길 글이 있는 문단인가. 수와 기호만 있는 줄(표의 값, 번호)과 주소만 있는 줄은 옮기지 않고 그대로 싣는다."""
    return bool(LETTERS.search(prose(text)))


def _numbers(text):
    return collections.Counter(DIGITS.findall(THOUSANDS.sub("", str(text))))


def as_is(text, screen=False):
    """원문대로 두어도 되는 줄인가: 식이거나, 화면에 뜨는 번호 붙은 알림 글. 등록부 안내서(screen)에서는 따옴표 안의 화면 이름만 있는 줄도."""
    if (RELATION.search(text) and not RUNNING.search(text)) or CODED.search(text):
        return True
    bare = QUOTED.sub(" ", text)
    return bool(screen and bare != text and not WORD.search(bare))


def _joined(number, got, korean):
    """각주 번호가 뒤에 붙어 버린 수인가: 앞쪽이 번역의 수에 있고 뒤쪽이 "[번호]"로 적혀 있으면 그렇다(5516 → 55와 [16])."""
    return any(number[:cut] in got and f"[{number[cut:]}]" in korean for cut in range(1, len(number)) if len(number) - cut <= 3)


def problems(source, korean, screen=False, excused=False):
    """{"hard": [막는 까닭], "soft": [알릴 것]}. screen은 등록부 안내서의 문단, excused는 예외로 둔 문단(tools.laws.plan.excused)."""
    global _terms
    hard, soft = [], []
    korean = str(korean or "").strip()
    if not korean:
        return {"hard": ["번역이 비어 있음"], "soft": []}
    plain = prose(source)
    if WORD.search(plain) and not HANGUL.search(korean) and not as_is(plain, screen):
        hard.append("국문으로 옮기지 않음")
    wanted, got = _numbers(source), _numbers(korean)
    missing = sorted(number for number in (wanted - got).elements() if not _joined(number, got, korean))
    if missing:
        hard.append("원문의 수가 빠짐: " + ", ".join(missing[:8]))
    spelled = {str(value) for word, value in SPELLED.items() if re.search(rf"\b{word}\b", source.lower())}
    split = {part for number in wanted if _joined(number, got, korean) for cut in range(1, len(number)) for part in (number[:cut], number[cut:])}
    extra = sorted(number for number in (got - wanted).elements() if number not in spelled and number not in split)
    if extra:
        soft.append("원문에 없는 수: " + ", ".join(extra[:8]))
    lost = sorted({numeral for numeral in ROMAN_REF.findall(source) if not re.search(rf"(?<![A-Za-z]){numeral}(?![A-Za-z])", korean)})
    if lost:
        hard.append("부속서·장의 번호가 빠짐: " + ", ".join(lost))
    flat = re.sub(r"\s+", "", korean)
    kept = {entry["show"] for entry in terms.found(prose(korean))}  # 번역이 영문 그대로 둔 용어(화면에 적힌 이름 따위)
    other = plan.senses()
    for entry in terms.found(plain):
        if not entry["core"] or entry["show"] in kept or any(re.sub(r"\s+", "", form) in flat for form in entry["ko"]):
            continue
        used = [form for english in entry["en"] for form in other.get(english, []) if re.sub(r"\s+", "", form) in flat]
        if used:
            soft.append(f"용어집의 뜻({entry['ko'][0]})이 아닌 다른 뜻으로 옮김: {entry['show']} → {used[0]}")
        else:
            hard.append(f"용어집의 표기가 없음: {entry['show']} → {entry['ko'][0]}")
    if _terms is None:
        _terms = term_check.load()
    low = plain.lower()
    for hit in term_check.check(korean, _terms):
        meant = [english for english, forms in other.items() if hit["avoid"] in forms and terms._pattern(english).search(low)]
        if hit["hard"] and meant:
            soft.append(f"용어집이 쓰지 않는 표기 '{hit['avoid']}'를 원문의 {meant[0]}의 뜻으로 씀")
        else:
            (hard if hit["hard"] else soft).append(f"용어: '{hit['avoid']}' 대신 '{hit['use']}'")
    if len(source) > 40 and not RATIO[0] <= len(korean) / len(source) <= RATIO[1]:
        soft.append(f"길이가 원문의 {len(korean) / len(source):.1f}배")
    if excused:
        waived = [why for why in hard if why.startswith(WAIVABLE)]
        hard = [why for why in hard if why not in waived]
        soft = [f"예외로 둔 문단: {why}" for why in waived] + soft
    return {"hard": hard, "soft": soft}
