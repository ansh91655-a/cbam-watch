"""법령 번역이 용어집(language/glossary.json)을 따르게 하는 도우미.

원문 문단에 나온 용어집의 낱말을 찾는다. 긴 낱말부터 찾고, 긴 낱말에 든 짧은 낱말은 세지 않는다
("economic operator"가 나온 자리의 "operator"는 따로 세지 않는다). 번역 검사(check)와 영문 병기(gloss)가 함께 쓴다.
"""
import re

from tools.common.jsonio import read_json

GLOSSARY = "language/glossary.json"
_entries = None


def _forms(text):
    return [form.strip() for form in re.split(r"\s*/\s*", str(text)) if form.strip()]


def _bare(form):
    """괄호 안의 풀이를 뗀 표기: "전문(前文)" → "전문"."""
    return re.sub(r"\([^)]*\)", "", form).strip()


def entries(path=GLOSSARY):
    """용어집의 낱말들: {"en": [영문 표기(소문자)], "show": 화면에 병기할 영문, "ko": [국문 표기], "core": 핵심 용어인가}. 긴 영문부터."""
    global _entries
    if _entries is None or path != GLOSSARY:
        found = []
        for term in (read_json(path, {}) or {}).get("terms", []):
            english = [_bare(form) for item in term.get("en", []) for form in _forms(item)]
            english = [form for form in english if len(form) >= 4]
            korean = [_bare(form) for form in _forms(term.get("preferred", "")) + list(term.get("allowed", []))]
            if english and any(korean):
                found.append({"en": [form.lower() for form in english], "show": english[0], "ko": [form for form in korean if form], "core": bool(term.get("core"))})
        found.sort(key=lambda entry: max(len(form) for form in entry["en"]), reverse=True)
        if path != GLOSSARY:
            return found
        _entries = found
    return _entries


def found(source, path=GLOSSARY):
    """원문 문단에 나온 용어집의 낱말들(긴 것부터). 복수형(-s, -es)도 같은 낱말로 본다."""
    text = str(source).lower()
    hits = []
    for entry in entries(path):
        for form in entry["en"]:
            pattern = re.compile(r"(?<![a-z])" + re.escape(form) + r"(?:s|es)?(?![a-z])")
            if pattern.search(text):
                text = pattern.sub(lambda match: " " * len(match.group(0)), text)  # 이 자리에 든 짧은 낱말은 다시 세지 않는다
                hits.append(entry)
                break
    return hits


def spans(korean, forms):
    """국문 글에서 표기들이 나온 자리 [(시작, 끝)]. 띄어쓰기까지 같은 것만 본다."""
    return sorted((match.start(), match.end()) for form in forms for match in re.finditer(re.escape(form), korean))
