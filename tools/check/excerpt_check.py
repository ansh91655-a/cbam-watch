"""원문 발췌가 원문 글에 실제로 그대로 있는지 확인한다. 발췌는 사이트에서 국문 요약 옆에 보이는 원문 대목이다.

쓰는 법: python -m tools.check.excerpt_check --excerpt-file 발췌.txt --source-file 원문.txt
- 공백과 줄바꿈의 차이는 무시한다. 그 밖의 글자는 하나라도 다르면 다른 것이다.
- 발췌가 여러 대목이면 줄을 바꿔 적는다. 대목마다 따로 찾는다.
결과는 JSON 한 줄이다. 찾지 못한 대목이 있거나 너무 길면 ok는 거짓이다.
"""
import argparse
import json
import re
import sys

MAX_CHARS = 1500
MIN_SEGMENT = 12


def squeeze(text):
    return re.sub(r"\s+", " ", (text or "").replace(" ", " ")).strip()


def check(excerpt, source):
    plain_source = squeeze(source)
    segments = [squeeze(line) for line in (excerpt or "").splitlines()]
    segments = [segment for segment in segments if segment]
    missing = [segment[:60] for segment in segments if len(segment) < MIN_SEGMENT or segment not in plain_source]
    chars = sum(len(segment) for segment in segments)
    return {"ok": bool(segments) and not missing and chars <= MAX_CHARS, "missing": missing, "chars": chars, "tooLong": chars > MAX_CHARS, "segments": len(segments)}


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("--excerpt-file", required=True)
    parser.add_argument("--source-file", required=True)
    args = parser.parse_args(argv)
    with open(args.excerpt_file, encoding="utf-8") as handle:
        excerpt = handle.read()
    with open(args.source_file, encoding="utf-8") as handle:
        source = handle.read()
    print(json.dumps(check(excerpt, source), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
