"""국문 글의 표기 규칙을 검사한다: 조문 인용, 숫자 표기, 문장 끝.

쓰는 법: python -m tools.check.style_check --text-file 글.txt
결과는 JSON 한 줄이다. hard가 참인 것이 하나라도 있으면 ok는 거짓이다.
"""
import argparse
import json
import re
import sys

RULES = [
    ("citation", True, re.compile(r"제\s?\d+\s?조\s?제\s?\d+\s?항"), "조문은 '제6조(1)' 꼴로 적는다"),
    ("decimal-comma", True, re.compile(r"(?<![\d,.])\d{1,3},\d{1,2}(?![\d,])"), "소수점은 마침표로 적는다(예: 82.32)"),
    ("space-thousands", True, re.compile(r"(?<![\d.])\d{1,3}(?:[   ]\d{3})+(?![\d])"), "천 단위는 쉼표로 적는다(예: 15,000)"),
    ("polite-ending", False, re.compile(r"(습니다|입니다|됩니다)[.\s]"), "정리 글은 '~다'로 끝맺는다"),
    ("double-space", False, re.compile(r"[^\s] {2,}[^\s]"), "공백이 두 칸 이상이다"),
]


def check(text):
    hits = []
    for code, hard, pattern, message in RULES:
        found = pattern.findall(text)
        if found:
            sample = pattern.search(text).group(0)
            hits.append({"rule": code, "hard": hard, "count": len(found), "sample": sample[:40], "message": message})
    return hits


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("--text", default="")
    parser.add_argument("--text-file", default="")
    args = parser.parse_args(argv)
    text = args.text
    if args.text_file:
        with open(args.text_file, encoding="utf-8") as handle:
            text += "\n" + handle.read()
    hits = check(text)
    print(json.dumps({"ok": not any(hit["hard"] for hit in hits), "hits": hits}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
