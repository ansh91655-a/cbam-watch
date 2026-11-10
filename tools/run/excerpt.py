"""원문 파일에서 줄 번호로 대목을 그대로 잘라 발췌 파일을 만든다. 손으로 옮겨 적다 글자가 달라지는 일을 막는다.

쓰는 법: python -m tools.run.excerpt --source-file 원문.txt --lines 99-101 --out /tmp/run/src/<항목 id>.excerpt.txt
        여러 대목이면 --lines 99-101,113-114 처럼 쉼표로 잇는다. 줄 번호는 `grep -n`이 보여 주는 번호(1부터)다.
잘라 낸 글을 출력하고, 글자 수가 한도를 넘으면 0이 아닌 값으로 끝난다.
"""
import argparse
import pathlib
import sys

from tools.check.excerpt_check import MAX_CHARS, squeeze


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-file", required=True)
    parser.add_argument("--lines", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    lines = pathlib.Path(args.source_file).read_text(encoding="utf-8").splitlines()
    picked = []
    for part in args.lines.split(","):
        start, _, end = part.strip().partition("-")
        first, last = int(start), int(end or start)
        picked += [squeeze(line) for line in lines[first - 1:last] if squeeze(line)]
    text = "\n".join(picked)
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text + "\n", encoding="utf-8")
    print(text)
    if not picked or len(text) > MAX_CHARS:
        print(f"발췌 {len(text)}자: 비어 있거나 한도({MAX_CHARS}자)를 넘음", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
