"""번역의 진행 상황을 본다.

쓰는 법: python -m tools.laws.status [--group act|guide|manual|paper]
문서마다 옮길 문단과 옮긴 문단의 수, 원문 글자 수로 본 비율과, 어느 문서에도 붙지 않는 번역의 수를 찍고, 검수(tools.laws.verify)가 얼마나 되었는지와
갈래마다의 진행을 한 줄씩 간추린다. 마지막 줄이 보고에 쓰는 줄이다(갈래를 주지 않으면 법령의 줄이 마지막이다). summary()가 갈래의 한 줄을 돌려준다.
"""
import argparse
import sys

from tools.laws import corpus, store, verify

NAMES = {"act": "규정 번역", "guide": "가이던스 번역", "manual": "등록부 안내서 번역", "paper": "보고서·안내 자료 번역"}
UNITS = {"act": "법령", "guide": "문서", "manual": "문서", "paper": "문서"}
ORDER = ("paper", "manual", "guide", "act")  # 간추린 줄을 찍는 차례(법령이 마지막 줄)


def rows(group=""):
    """[(문서, 진행)]. group을 주면 그 갈래만."""
    documents, memory = corpus.everything()
    return [(act, corpus.progress(found, memory)) for act, found in documents if found and group in ("", act.get("group", "act"))]


def percent(progress):
    return round(100 * progress["doneChars"] / progress["chars"]) if progress["chars"] else 100


def summary(found=None, group="act"):
    """갈래 하나의 한 줄: 규정 번역: 원문 …자 가운데 …자(…%), 법령 …건 가운데 …건을 모두 옮김"""
    found = [(act, progress) for act, progress in (rows() if found is None else found) if act.get("group", "act") == group]
    chars = sum(progress["chars"] for _, progress in found)
    done = sum(progress["doneChars"] for _, progress in found)
    finished = sum(progress["done"] == progress["blocks"] for _, progress in found)
    return f"{NAMES[group]}: 원문 {chars:,}자 가운데 {done:,}자({round(100 * done / chars) if chars else 100}%), {UNITS[group]} {len(found)}건 가운데 {finished}건을 모두 옮김"


def unused():
    """어느 문서에도 붙지 않는 번역의 수. 원문이 새 판으로 바뀌었거나 문단 나누기가 달라지면 생긴다(번역 자료에는 남아 있다)."""
    documents, memory = corpus.everything()
    live = {store.key(text) for _, found in documents for part in found for text in corpus.texts(part)}
    return sum(block_key not in live for block_key in memory)


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("--group", default="", choices=["", *NAMES])
    args = parser.parse_args(argv)
    found = rows(args.group)
    for act, progress in found:
        print(f"{act['id']:<22} {percent(progress):>3}%  문단 {progress['done']:>4}/{progress['blocks']:<4}  원문 {progress['chars']:>7,}자  {act['name']}")
    print(f"쓰이지 않는 번역: {unused()}개")
    print(verify.summary())
    for group in ([args.group] if args.group else ORDER):
        print(summary(found, group))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
