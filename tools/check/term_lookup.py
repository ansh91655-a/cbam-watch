"""원문에 나온 영문 용어의 국문 표기를 용어집에서 찾아 준다. 글을 쓰기 전에 돌린다.

쓰는 법: python -m tools.check.term_lookup --text-file 원문.txt   (또는 --text "영문 글")
결과는 JSON 한 줄이다. 긴 용어부터 찾고, 약어는 대문자가 같은 것만 맞춘다.
"""
import argparse
import json
import re
import sys

GLOSSARY = "language/glossary.json"
STATUS = {"confirmed": "확인", "partial": "부분 확인", "candidate": "확인 필요"}


def lookup(text, path=GLOSSARY, limit=60):
    with open(path, encoding="utf-8") as handle:
        terms = json.load(handle)["terms"]
    lowered = text.lower()
    found = []
    for term in terms:
        hit = ""
        for form in term.get("en", []):
            for variant in re.split(r"\s*/\s*", form):
                variant = variant.strip()
                if len(variant) >= 4 and re.search(r"(?<![a-z])" + re.escape(variant.lower()) + r"(?:s|es)?(?![a-z])", lowered):
                    hit = variant
        for abbr in term.get("abbr", []):
            if len(abbr) >= 2 and re.search(r"(?<![A-Za-z])" + re.escape(abbr) + r"(?![A-Za-z])", text):
                hit = hit or abbr
        if hit:
            found.append({"en": hit, "ko": term["preferred"], "allowed": term.get("allowed", []), "status": STATUS.get(term.get("status"), "")})
    found.sort(key=lambda row: len(row["en"]), reverse=True)
    return found[:limit]


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("--text", default="")
    parser.add_argument("--text-file", default="")
    args = parser.parse_args(argv)
    text = args.text
    if args.text_file:
        with open(args.text_file, encoding="utf-8") as handle:
            text += "\n" + handle.read()
    print(json.dumps(lookup(text), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
