"""다음에 번역할 문단을 고른다. 예약 실행과 사람이 번역할 분량을 받아 가는 데 쓴다.

쓰는 법: python -m tools.laws.todo [--act <법령 번호>] [--limit <원문 글자 수>] [--titles] [--part <조각 id>]
- 법령은 화면에 싣는 차례대로, 문단은 글의 차례대로 고른다. 이미 옮긴 문단과 옮길 글이 없는 줄(수와 기호)은 건너뛴다.
- --titles는 조와 부속서, 장의 이름만 고른다(차례를 국문으로 먼저 보이게 할 때 쓴다).
- 결과(JSON)의 blocks가 옮길 문단이다: {"key": 열쇠, "act": 법령, "part": 조각, "text": 원문}. glossary는 그 글에 나온 용어집의 낱말이다.
  옮긴 것은 {"blocks": {열쇠: 국문}} 꼴의 파일로 만들어 python -m tools.laws.apply 에 넘긴다.
"""
import argparse
import json
import sys

from tools.check import term_lookup
from tools.laws import check, corpus, store

LIMIT = 20000
SKIPPED = ("closing", "notes")  # 서명과 각주는 맨 나중에 옮긴다(--part로 가리키면 옮긴다)


def pick(limit=LIMIT, act_id="", titles=False, part_id=""):
    """옮길 문단들과 남은 분량을 돌려준다."""
    acts, memory = corpus.everything()
    picked, taken, size, full = [], set(), 0, False
    left = {"blocks": 0, "chars": 0}
    for act, found in acts:
        if act_id and act["id"] != act_id:
            continue
        for part in found:
            if part_id and part["id"] != part_id:
                continue
            if not part_id and part["kind"] in SKIPPED:
                continue
            for text in ([part["title"]] if part["title"] else []) + ([] if titles else list(part["blocks"])):
                block_key = store.key(text)
                if not check.needs(text) or block_key in memory or block_key in taken:
                    continue
                if full or (size + len(text) > limit and picked):
                    full = True  # 들어가지 않는 문단을 만나면 거기서 멈춘다(글의 차례가 끊기지 않게)
                    left["blocks"] += 1
                    left["chars"] += len(text)
                    taken.add(block_key)
                    continue
                picked.append({"key": block_key, "act": act["id"], "part": part["id"], "text": text})
                taken.add(block_key)
                size += len(text)
    return picked, left


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("--act", default="")
    parser.add_argument("--part", default="")
    parser.add_argument("--limit", type=int, default=LIMIT)
    parser.add_argument("--titles", action="store_true")
    args = parser.parse_args(argv)
    picked, left = pick(args.limit, args.act, args.titles, args.part)
    glossary = term_lookup.lookup("\n".join(block["text"] for block in picked), limit=80) if picked else []
    print(json.dumps({"blocks": picked, "chars": sum(len(block["text"]) for block in picked), "left": left,
                      "glossary": [{"en": term["en"], "ko": term["ko"]} for term in glossary]}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
