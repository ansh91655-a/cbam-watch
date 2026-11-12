"""다음에 번역할 문단을 고른다. 예약 실행과 사람이 번역할 분량을 받아 가는 데 쓴다.

쓰는 법: python -m tools.laws.todo [--runner <실행 이름>] [--act <문서 id>] [--limit <원문 글자 수>] [--titles] [--part <조각 id>]
- 무엇을 얼마나 옮길지는 실행(runner)마다 sources/translation.json이 정한다. 이름을 주지 않으면 daily다. --limit을 주면 그 분량으로 한다.
- 문서는 그 실행이 맡은 갈래의 차례대로(tools.laws.plan), 문단은 글의 차례대로 고른다. 이미 옮긴 문단과 옮길 글이 없는 줄(수와 기호)은 건너뛴다.
  법령의 서명과 각주는 다른 문단을 모두 옮긴 뒤에 고른다.
  검사에 거듭 걸린 문단(tools.laws.store의 held, HOLD_AFTER번 이상)은 그 뒤에 한 번 더 고르고, 그때도 걸리면(GIVE_UP번) 더 고르지 않는다.
  그런 문단이 줄의 앞에 남아 묶음을 채우면 번역이 나아가지 못하기 때문이다. left의 held가 그렇게 뒤로 돌린 문단의 수다.
  --act로 문서를 가리키면 갈래와 상관없이 그 문서에서 고른다.
- --titles는 조와 부속서, 장의 이름만 고른다(차례를 국문으로 먼저 보이게 할 때 쓴다).
- 결과(JSON)의 blocks가 옮길 문단이다: {"key": 열쇠, "act": 문서, "part": 조각, "text": 원문}. glossary는 그 글에 나온 용어집의 낱말,
  wording은 용어집에는 없지만 앞의 실행들이 정해 둔 낱말(tools.laws.wording), remarks는 앞의 번역이 표본 검토에서 지워진 문단과 그 까닭(tools.laws.review)이나
  앞에서 검사에 걸린 문단과 그 까닭,
  left는 이 묶음 뒤에 남는 분량, rounds는 한 번의 실행에서 하는 묶음 수다.
  옮긴 것은 {"blocks": {열쇠: 국문}} 꼴의 파일로 만들어 python -m tools.laws.apply 에 넘긴다.
"""
import argparse
import json
import sys

from tools.check import term_lookup
from tools.laws import check, corpus, plan, review, store, wording

LIMIT = 20000
SKIPPED = ("closing", "notes")  # 서명과 각주는 다른 문단을 모두 옮긴 뒤에 옮긴다(--part로 가리키면 바로 옮긴다)


def _gather(documents, memory, limit, titles, part_id, skipped, late=frozenset(), only_late=False):
    """문서들에서 옮길 문단을 차례대로 모은다: (고른 문단들, 그 뒤에 남는 분량). skipped에 든 종류의 조각은 건너뛴다.

    late는 검사에 거듭 걸려 뒤로 돌린 문단의 열쇠다. 보통은 건너뛰고, only_late이면 그것만 고른다.
    """
    picked, taken, size, full = [], set(), 0, False
    left = {"blocks": 0, "chars": 0, "held": 0}
    for act, found in documents:
        for part in found:
            if part_id and part["id"] != part_id:
                continue
            if not part_id and part["kind"] in skipped:
                continue
            for text in ([part["title"]] if part["title"] else []) + ([] if titles else list(part["blocks"])):
                block_key = store.key(text)
                if not check.needs(text) or block_key in memory or block_key in taken:
                    continue
                if (block_key in late) != only_late:
                    if not only_late:
                        left["held"] += 1
                        taken.add(block_key)
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


def pick(limit=None, act_id="", titles=False, part_id="", runner=plan.DEFAULT, memory=None, held=None):
    """옮길 문단들과 남은 분량을 돌려준다. memory를 주면 그것을 이미 옮긴 번역으로 본다(견주기 시험에서 빈 것을 준다).

    서명과 각주(SKIPPED)는 그 실행이 맡은 다른 문단을 모두 옮긴 뒤에야 고른다.
    검사에 거듭 걸린 문단(held: {열쇠: {"tries", "why"}}, 주지 않으면 번역 자료에 적힌 것)은 그보다도 뒤에 고른다. --part로 조각을 가리키면 가리지 않는다.
    """
    settings = plan.runner(runner)
    limit = limit or settings["limit"]
    documents, stored = corpus.everything()
    held = (store.held_all() if memory is None else {}) if held is None else held
    memory = stored if memory is None else memory
    documents = [(act, found) for act, found in documents if act["id"] == act_id] if act_id else plan.ordered(documents, settings)
    late = frozenset() if part_id else frozenset(block_key for block_key, row in held.items() if row.get("tries", 0) >= store.HOLD_AFTER)
    picked, left = _gather(documents, memory, limit, titles, part_id, SKIPPED, late)
    if not picked and not part_id:
        picked, left = _gather(documents, memory, limit, titles, part_id, (), late)
    if not picked and late:
        again = frozenset(block_key for block_key in late if held[block_key].get("tries", 0) < store.GIVE_UP)
        picked, more = _gather(documents, memory, limit, titles, part_id, (), again, only_late=True)
        left = {**more, "held": left["held"] - len(picked)}
    return picked, left


def answer(picked, left, **extra):
    """고른 문단을 찍을 꼴로 만든다. 그 글에 나온 용어집의 낱말을 함께 싣는다."""
    text = "\n".join(block["text"] for block in picked)
    glossary = term_lookup.lookup(text, limit=80) if picked else []
    noted = review.remarks()
    stuck = store.held_all() if picked else {}
    remarks = {block["key"]: "앞에서 검사에 걸림: " + stuck[block["key"]]["why"] for block in picked if block["key"] in stuck}
    remarks.update({block["key"]: noted[block["key"]] for block in picked if block["key"] in noted})
    return {"blocks": picked, "chars": len(text) - max(0, len(picked) - 1), "left": left,
            "glossary": [{"en": term["en"], "ko": term["ko"]} for term in glossary], "wording": wording.found(text) if picked else [],
            "remarks": remarks, **extra}


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("--runner", default=plan.DEFAULT)
    parser.add_argument("--act", default="")
    parser.add_argument("--part", default="")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--titles", action="store_true")
    args = parser.parse_args(argv)
    picked, left = pick(args.limit, args.act, args.titles, args.part, args.runner)
    print(json.dumps(answer(picked, left, runner=args.runner, rounds=plan.runner(args.runner)["rounds"]), ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
