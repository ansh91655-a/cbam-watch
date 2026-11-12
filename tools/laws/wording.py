"""번역 실행들이 스스로 정한 낱말(language/translation-terms.json)을 읽고 더한다.

용어집(language/glossary.json)에 없는 전문용어를 한 실행이 어떻게 옮겼는지 적어 두어, 다음 실행이 같은 낱말로 옮기게 한다
(실행은 앞의 실행을 기억하지 못한다). 용어집이 아니다: 정부·공공기관 자료에서 확인한 표기가 아니고, 번역 검사가 강제하지도 않는다.
운영자가 살펴보고 맞는 것은 용어집으로 옮긴다. 먼저 적힌 표기가 남는다(같은 영문을 다시 더하면 건너뛴다).

쓰는 법: python -m tools.laws.wording add <파일> [--from <문서 id>]   파일은 [{"en": 영문, "ko": 국문}, …] 꼴이다
        python -m tools.laws.wording list
"""
import argparse
import json
import re
import sys

from tools.common.jsonio import read_json, today, write_json

SOURCE = "language/translation-terms.json"
GLOSSARY = "language/glossary.json"
PER_CALL = 15     # 한 번에 더할 수 있는 낱말 수
WORDS = 6         # 영문 낱말의 수
HANGUL = re.compile(r"[가-힣]")
LETTERS = re.compile(r"[A-Za-z]{3,}")


def load():
    return list((read_json(SOURCE, {}) or {}).get("terms", []))


def _glossary_forms():
    terms = (read_json(GLOSSARY, {}) or {}).get("terms", [])
    return {form.lower() for term in terms for form in term.get("en", []) + term.get("abbr", [])}


def fits(english, korean):
    """적어 둘 만한 낱말인가: 짧은 영문 낱말과 한글이 든 짧은 국문."""
    english, korean = str(english).strip(), str(korean).strip()
    return bool(LETTERS.search(english)) and len(english) <= 60 and len(english.split()) <= WORDS and bool(HANGUL.search(korean)) and len(korean) <= 40


def add(entries, origin="", day=None):
    """낱말을 더하고 (더한 것, 건너뛴 것)을 돌려준다. 용어집에 있는 것, 이미 적힌 것, 꼴이 맞지 않는 것은 건너뛴다."""
    terms = load()
    known = _glossary_forms() | {term["en"].lower() for term in terms}
    added, skipped = [], []
    for entry in entries[:PER_CALL] if isinstance(entries, list) else []:
        english, korean = str(entry.get("en", "")).strip(), str(entry.get("ko", "")).strip()
        if not fits(english, korean) or english.lower() in known:
            skipped.append(english)
            continue
        terms.append({"en": english, "ko": korean, "from": origin, "added": day or today()})
        known.add(english.lower())
        added.append(english)
    if added:
        write_json(SOURCE, {"note": "번역 실행들이 정한 낱말. 용어집(glossary.json)에 없는 전문용어를 같은 낱말로 옮기려고 적어 둔다. 확인된 표기가 아니다.", "terms": terms})
    return added, skipped + [str(entry.get("en", "")) for entry in (entries[PER_CALL:] if isinstance(entries, list) else [])]


def found(text):
    """글에 나온 낱말들: [{"en", "ko"}]. 긴 것부터."""
    lowered = str(text).lower()
    hits = [{"en": term["en"], "ko": term["ko"]} for term in load()
            if re.search(r"(?<![a-z])" + re.escape(term["en"].lower()) + r"(?:s|es)?(?![a-z])", lowered)]
    return sorted(hits, key=lambda term: len(term["en"]), reverse=True)


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["add", "list"])
    parser.add_argument("file", nargs="?", default="")
    parser.add_argument("--from", dest="origin", default="")
    args = parser.parse_args(argv)
    if args.action == "list":
        print(json.dumps(load(), ensure_ascii=False, indent=1))
        return 0
    added, skipped = add(read_json(args.file, []) or [], args.origin)
    print(json.dumps({"added": added, "skipped": skipped}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
