"""국문 정리에 나온 수치와 날짜가 원문 글에 실제로 있는지 대조한다.

쓰는 법: python -m tools.check.fact_check --summary-file 정리.txt --source-file 원문.txt
- 정리 글의 날짜는 (연, 월, 일)로 바꿔 원문에서 찾은 날짜와 견준다. 표기 형식이 달라도 같은 날이면 같은 것으로 본다.
- 날짜가 아닌 수는 자릿수 그대로 원문에 있어야 한다. 한 자리 수와 분기·연도처럼 원문이 다르게 적는 수는 따로 본다.
  원문이 소수점을 쉼표로 적은 수(97,5 %)는 정리 글의 97.5와 같은 것으로 본다.
결과는 JSON 한 줄이다. 원문에서 찾지 못한 것이 있으면 ok는 거짓이다.
"""
import argparse
import json
import re
import sys

from tools.check import dates

NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?(?:/\d+)?")


def numbers(text):
    """글에서 수를 뽑는다. 천 단위 쉼표는 떼고, '2025/2621' 같은 문서 번호는 통째로 둔다."""
    found = []
    for token in NUMBER.findall(text):
        token = token.rstrip(",")
        plain = token.replace(",", "") if re.fullmatch(r"\d{1,3}(,\d{3})+(\.\d+)?", token) else token
        found.append(plain)
    return found


def check(summary, source):
    summary_dates, summary_rest = dates.find(summary)
    source_dates, _ = dates.find(source)
    source_plain = re.sub(r"(?<=\d)[,\u00a0\u202f ](?=\d{3}\b)", "", source)  # 천 단위의 쉼표나 띄움을 뗀다
    source_numbers = set(numbers(source_plain))
    missing_dates = sorted(f"{y}-{m:02d}-{d:02d}" for (y, m, d) in summary_dates - source_dates)
    missing_numbers = []
    for number in numbers(summary_rest):
        if len(number) < 2:  # 한 자리 수는 순서나 개수를 뜻하는 일이 많아 대조하지 않는다
            continue
        if number in source_numbers or number in source_plain:
            continue
        # EU 법령의 영문본은 소수점을 쉼표로 적기도 한다('97,5 %'). 정리 글의 '97.5'는 원문의 '97,5'와 같은 수로 본다.
        if "." in number and number.replace(".", ",") in source_numbers:
            continue
        missing_numbers.append(number)
    return {"ok": not missing_dates and not missing_numbers, "missingDates": missing_dates, "missingNumbers": sorted(set(missing_numbers)),
            "checkedDates": len(summary_dates), "checkedNumbers": len([n for n in numbers(summary_rest) if len(n) >= 2])}


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("--summary", default="")
    parser.add_argument("--summary-file", default="")
    parser.add_argument("--source-file", required=True)
    args = parser.parse_args(argv)
    summary = args.summary
    if args.summary_file:
        with open(args.summary_file, encoding="utf-8") as handle:
            summary += "\n" + handle.read()
    with open(args.source_file, encoding="utf-8") as handle:
        source = handle.read()
    print(json.dumps(check(summary, source), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
