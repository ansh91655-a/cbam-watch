"""번역한 문단을 원문과 견줘 본다. 기계로 가릴 수 있는 잘못만 잡는다(사람의 감수를 대신하지 않는다).

막는 것(hard): 빈 번역, 옮기지 않은 글, 원문의 수가 빠진 것, 부속서·장의 로마 숫자가 빠진 것, 용어집이 쓰지 않기로 한 표기,
            원문에 핵심 용어(용어집의 core)가 나왔는데 번역에 그 국문 표기가 없는 것(모든 법령에서 같은 낱말을 쓰게 하려는 것).
알리는 것(soft): 원문에 없는 수가 번역에 있는 것, 길이가 지나치게 다른 것.

웹 주소 안의 낱말은 옮길 말도, 용어집과 견줄 말도 아니다(…/module-for-non-eu-installation-operators 의 installation).
주소와 번호만 있는 줄(주소 하나만 적은 각주)은 옮기지 않고 그대로 싣는다. 주소 안의 수는 번역에 그대로 남아 있어야 한다.
"""
import collections
import re

from tools.check import term_check
from tools.laws import terms

DIGITS = re.compile(r"\d+")
HANGUL = re.compile(r"[가-힣]")
WORD = re.compile(r"(?<![A-Za-z])[a-z]{4,}")  # 소문자로 시작하는 낱말. 사람 이름이나 약어만 있는 줄(Ursula VON DER LEYEN)과 가린다
LETTERS = re.compile(r"[A-Za-z]{2,}")
THOUSANDS = re.compile(r"(?<=\d)[   ,](?=\d{3}(?!\d))")
URL = re.compile(r"(?:https?://|www\.)\S+")
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


def problems(source, korean):
    """{"hard": [막는 까닭], "soft": [알릴 것]}"""
    global _terms
    hard, soft = [], []
    korean = str(korean or "").strip()
    if not korean:
        return {"hard": ["번역이 비어 있음"], "soft": []}
    plain = prose(source)
    if WORD.search(plain) and not HANGUL.search(korean):
        hard.append("국문으로 옮기지 않음")
    wanted, got = _numbers(source), _numbers(korean)
    missing = sorted((wanted - got).elements())
    if missing:
        hard.append("원문의 수가 빠짐: " + ", ".join(missing[:8]))
    spelled = {str(value) for word, value in SPELLED.items() if re.search(rf"\b{word}\b", source.lower())}
    extra = sorted(number for number in (got - wanted).elements() if number not in spelled)
    if extra:
        soft.append("원문에 없는 수: " + ", ".join(extra[:8]))
    lost = sorted({numeral for numeral in ROMAN_REF.findall(source) if not re.search(rf"(?<![A-Za-z]){numeral}(?![A-Za-z])", korean)})
    if lost:
        hard.append("부속서·장의 번호가 빠짐: " + ", ".join(lost))
    flat = re.sub(r"\s+", "", korean)
    for entry in terms.found(plain):
        if entry["core"] and not any(re.sub(r"\s+", "", form) in flat for form in entry["ko"]):
            hard.append(f"용어집의 표기가 없음: {entry['show']} → {entry['ko'][0]}")
    if _terms is None:
        _terms = term_check.load()
    for hit in term_check.check(korean, _terms):
        (hard if hit["hard"] else soft).append(f"용어: '{hit['avoid']}' 대신 '{hit['use']}'")
    if len(source) > 40 and not RATIO[0] <= len(korean) / len(source) <= RATIO[1]:
        soft.append(f"길이가 원문의 {len(korean) / len(source):.1f}배")
    return {"hard": hard, "soft": soft}
