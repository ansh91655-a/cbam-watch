"""실린 번역의 표본을 뽑아 원문과 견줘 보고, 틀린 번역을 지워 다시 옮기게 한다. 주간 작업이 쓴다.

번역은 기계 검사(tools.laws.check)만 거쳐 실린다. 검사는 수와 용어는 잡지만 뜻이 틀린 문장이나 빠진 말은 잡지 못한다.
그래서 번역하는 실행과 다른 실행이 주마다 표본을 읽는다. 틀린 번역은 지우고 까닭을 적어 두며(language/translation-reviews.json),
번역하는 실행이 그 문단을 다시 받을 때 까닭이 함께 나간다(tools.laws.todo의 remarks).

쓰는 법: python -m tools.laws.review sample [--count 30] [--days 8] [--seed <글자>]   최근에 번역이 더해진 문서에서 표본을 뽑아 찍는다
        python -m tools.laws.review drop <열쇠> --why "<까닭>"                         그 번역을 지우고 까닭을 적는다
"""
import argparse
import datetime
import json
import random
import sys

from tools.common.jsonio import read_json, today, write_json
from tools.laws import check, corpus, store

LOG = "language/translation-reviews.json"
MIN_CHARS = 60   # 이보다 짧은 문단(제목, 표의 칸)은 표본에서 뺀다. 읽어서 가릴 뜻이 적다


def reviews():
    return list((read_json(LOG, {}) or {}).get("reviews", []))


def remarks():
    """{열쇠: 지운 까닭}. 같은 문단을 여러 번 지웠으면 마지막 까닭."""
    return {entry["key"]: entry["why"] for entry in reviews()}


def _recent(act_id, day, days):
    updated = str((read_json(store.path_of(act_id), {}) or {}).get("updated", ""))
    return bool(updated) and (datetime.date.fromisoformat(day) - datetime.date.fromisoformat(updated)).days <= days


def sample(count=30, days=8, seed="", day=None):
    """표본: [{"key", "act", "part", "source", "korean"}]. 최근 days일 안에 번역이 더해진 문서의 옮긴 문단 가운데서 뽑는다."""
    day = day or today()
    documents, memory = corpus.everything()
    pool, seen = [], set()
    for act, found in documents:
        if not _recent(act["id"], day, days):
            continue
        for part in found:
            for text in part["blocks"]:
                block_key = store.key(text)
                if len(text) >= MIN_CHARS and check.needs(text) and block_key in memory and block_key not in seen:
                    seen.add(block_key)
                    pool.append({"key": block_key, "act": act["id"], "part": part["id"], "source": text, "korean": memory[block_key]})
    picker = random.Random(seed or day)
    return picker.sample(pool, min(count, len(pool)))


def drop(block_key, why, day=None):
    """번역 하나를 지우고 까닭을 적는다. 지운 문서의 id들을 돌려준다(없는 열쇠이면 빈 목록)."""
    removed = []
    for act in corpus.documents():
        blocks = store.load(act["id"])
        if block_key in blocks:
            del blocks[block_key]
            store.save(act["id"], blocks, day)
            removed.append(act["id"])
    if removed:
        write_json(LOG, {"note": "표본 검토에서 틀린 것으로 보아 지운 번역과 그 까닭. 번역하는 실행이 그 문단을 다시 옮길 때 까닭을 함께 받는다.",
                         "reviews": reviews() + [{"day": day or today(), "key": block_key, "act": removed[0], "why": str(why).strip()[:200]}]})
    return removed


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["sample", "drop"])
    parser.add_argument("key", nargs="?", default="")
    parser.add_argument("--count", type=int, default=30)
    parser.add_argument("--days", type=int, default=8)
    parser.add_argument("--seed", default="")
    parser.add_argument("--why", default="")
    args = parser.parse_args(argv)
    if args.action == "sample":
        print(json.dumps(sample(args.count, args.days, args.seed), ensure_ascii=False, indent=1))
        return 0
    if not args.key or not args.why.strip():
        print("지울 열쇠와 --why(까닭)를 함께 준다.")
        return 1
    removed = drop(args.key, args.why)
    print(json.dumps({"dropped": bool(removed), "from": removed}, ensure_ascii=False))
    return 0 if removed else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
