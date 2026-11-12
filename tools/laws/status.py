"""규정 번역의 진행 상황을 본다.

쓰는 법: python -m tools.laws.status
법령마다 옮길 문단과 옮긴 문단의 수, 원문 글자 수로 본 비율을 찍는다. summary()는 보고에 쓰는 한 줄을 돌려준다.
"""
import sys

from tools.laws import corpus


def rows():
    """[(법령, 진행)]"""
    acts, memory = corpus.everything()
    return [(act, corpus.progress(found, memory)) for act, found in acts if found]


def percent(progress):
    return round(100 * progress["doneChars"] / progress["chars"]) if progress["chars"] else 100


def summary(found=None):
    found = found if found is not None else rows()
    chars = sum(progress["chars"] for _, progress in found)
    done = sum(progress["doneChars"] for _, progress in found)
    finished = sum(progress["done"] == progress["blocks"] for _, progress in found)
    return f"규정 번역: 원문 {chars:,}자 가운데 {done:,}자({round(100 * done / chars) if chars else 100}%), 법령 {len(found)}건 가운데 {finished}건을 모두 옮김"


def main(argv):
    found = rows()
    for act, progress in found:
        print(f"{act['id']}  {percent(progress):>3}%  문단 {progress['done']:>4}/{progress['blocks']:<4}  원문 {progress['chars']:>7,}자  {act['name']}")
    print(summary(found))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
