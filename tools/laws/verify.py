"""실린 번역을 원문과 견줘 보는 일(검수)을 돕는다. 번역을 한 실행과 다른 실행이 읽게 한다.

번역은 기계 검사(tools.laws.check)만 거쳐 실린다. 검사는 수와 용어는 잡지만 뜻이 틀린 문장이나 빠진 말은 잡지 못한다.
그래서 번역을 하는 실행은 일을 시작할 때, 앞의 실행들이 옮겨 둔 문단부터 원문과 견줘 읽는다(검수를 먼저 하므로 자기가 옮긴 것은 읽지 않는다).
- 틀린 번역은 지우고 까닭을 적는다(tools.laws.review.drop). 그 문단은 다시 옮겨지고, 옮기는 실행은 까닭을 함께 받는다(tools.laws.todo의 remarks).
- 틀리지 않은 번역은 검수를 마친 것으로 적는다(번역 자료의 checked).
- 검수가 제대로 읽는지 재려고, 묶음마다 번역 몇 개를 일부러 틀리게 바꿔 섞어 넣는다(tools.laws.spoil: 뜻이 뒤집히는 말 바꾸기, 문장 빼기).
  어느 것이 바꾼 것인지는 묶음에 적지 않는다. 바꾼 것을 잡아낸 비율이 낮으면 그 묶음의 검수는 버리고(적지도 지우지도 않는다) 알린다.
  바꾼 번역은 작업 파일에만 있고 번역 자료에는 들어가지 않는다.
- 같은 문단을 두 번 지웠는데 또 틀렸다고 하면 지우지 않고 '가리지 못한 문단'으로 적어 둔다(번역과 검수가 맞서 되풀이하지 않게). 사람이 볼 것이다.
- 한 묶음에서 틀렸다고 한 비율이 지나치게 높으면 반영하지 않고 알린다(검수의 기준이 어긋난 것일 수 있다).
얼마나 읽는지와 문턱값은 sources/translation.json의 verify가 정한다(tools.laws.plan.checker).

쓰는 법: python -m tools.laws.verify todo [--limit <원문 글자 수>]   검수할 묶음을 찍는다(JSON). 묶음은 작업 파일(.work/verify.json)에 적어 둔다
        python -m tools.laws.verify apply <파일>                    {"wrong": {열쇠: 까닭}} 꼴의 결과를 반영한다. 적지 않은 문단은 틀리지 않은 것으로 본다
        python -m tools.laws.verify status                          검수가 얼마나 되었는지 찍는다(마지막 줄이 보고에 쓰는 줄)
"""
import argparse
import json
import pathlib
import random
import sys

from tools.check import term_lookup
from tools.common.jsonio import read_json, today, write_json
from tools.laws import check, corpus, plan, review, spoil, store

WORK = ".work/verify.json"                # 지금 읽고 있는 묶음(실행 안에서만 쓰는 작업 파일, 저장소에 넣지 않는다)
LOG = "language/translation-checks.json"  # 날마다의 검수 결과와 가리지 못한 문단
CANARY_FROM = 20   # 문단이 이만큼은 있어야 바꾼 번역을 섞는다(작은 묶음에서는 잴 수 없다)
CANARY_MIN = 3     # 섞을 때는 적어도 이만큼 섞는다
DROPS_BEFORE_DISPUTE = 2  # 같은 문단을 이만큼 지운 뒤에 또 틀렸다고 하면 지우지 않고 적어만 둔다
HARSH_MIN = 5      # 틀렸다고 한 것이 이보다 적으면 비율이 높아도 반영한다(작은 묶음)
KEPT_DAYS = 120    # 날마다의 결과를 이만큼만 남긴다
CANARIED_KEPT = 400  # 바꿔 섞었던 문단의 열쇠를 이만큼 기억한다(그 문단은 다음에 제 번역 그대로 읽힌다)
NOTE = ("번역 검수의 결과. days는 날마다 읽은 묶음의 수(batches), 틀리지 않다고 본 문단(checked), 틀려서 지운 문단(dropped), 일부러 바꿔 섞은 번역(canaries)과 그 가운데 잡아낸 것(caught), "
        "버린 묶음(discarded: 바꾼 것을 놓침)과 반영하지 않은 묶음(held: 틀렸다고 한 비율이 지나치게 높음)이다. disputed는 두 번 다시 옮기고도 또 틀렸다고 한 문단이다(사람이 볼 것). "
        "canaried는 얼마 전에 바꿔 섞었던 문단의 열쇠다(같은 문단을 거듭 바꾸지 않으려고 적어 둔다).")


def holders():
    """{열쇠: 그 번역이 든 문서의 id}. 여러 문서에 나오는 문단의 번역은 한 문서의 파일에만 들어 있다."""
    found = {}
    for path in sorted(pathlib.Path(store.FOLDER).glob("*.json")):
        for block_key in (read_json(path, {}) or {}).get("blocks", {}):
            found.setdefault(block_key, path.stem)
    return found


def pending(documents=None, memory=None, checked=None):
    """옮겼지만 아직 검수하지 않은 문단을 번역하는 차례대로: [{"key", "act", "part", "source", "korean"}]"""
    if documents is None or memory is None:
        documents, memory = corpus.everything(history=True)
    checked = store.checked_all() if checked is None else checked
    found, seen = [], set()
    for act, parts in plan.ordered(documents, plan.everyone()):
        for part in parts:
            for text in corpus.texts(part):
                block_key = store.key(text)
                if check.needs(text) and block_key in memory and block_key not in checked and block_key not in seen:
                    seen.add(block_key)
                    found.append({"key": block_key, "act": act["id"], "part": part["id"], "source": text, "korean": memory[block_key]})
    return found


def batch(limit=None, seed="", waiting=None):
    """검수할 묶음 하나: (찍을 문단들, 작업 파일에 적을 것, 남은 분량). 바꾼 번역을 섞어 넣는다."""
    settings = plan.checker()
    limit = limit or settings["limit"]
    waiting = pending() if waiting is None else waiting
    picked, size = [], 0
    for block in waiting:
        if picked and size + len(block["source"]) > limit:
            break
        picked.append(dict(block))
        size += len(block["source"])
    rest = waiting[len(picked):]
    canaries = {}
    if len(picked) >= CANARY_FROM and settings["canaries"] > 0:
        # 바꿔 섞은 문단은 검수 표시가 붙지 않아 다음 묶음의 앞에 다시 선다. 또 고르면 같은 문단이 같은 꼴로 거듭 바뀌어
        # 읽는 쪽이 되풀이를 알아챌 수 있으므로(잡아낸 비율이 뜻을 잃는다), 얼마 전에 골랐던 문단은 제 번역 그대로 읽힌다.
        used = set(_log()["canaried"])
        picker = random.Random(seed or f"{today()}:{picked[0]['key']}")
        wanted = max(CANARY_MIN, round(settings["canaries"] * len(picked)))
        for at in picker.sample(range(len(picked)), len(picked)):
            if len(canaries) >= wanted:
                break
            if picked[at]["key"] in used:
                continue
            spoiled = spoil.spoil(picked[at]["korean"], picker)
            if spoiled:
                canaries[picked[at]["key"]] = {"kind": spoiled[1], "korean": picked[at]["korean"]}
                picked[at]["korean"] = spoiled[0]
    work = {"day": today(), "keys": [block["key"] for block in picked if block["key"] not in canaries], "canaries": canaries}
    left = {"blocks": len(rest), "chars": sum(len(block["source"]) for block in rest)}
    return picked, work, left


def _log():
    found = read_json(LOG, {}) or {}
    return {"note": NOTE, "days": list(found.get("days", [])), "disputed": list(found.get("disputed", [])), "canaried": list(found.get("canaried", []))}


def _record(day, **counts):
    """그날의 결과에 더한다."""
    log = _log()
    entry = next((row for row in log["days"] if row.get("day") == day), None)
    if entry is None:
        entry = {"day": day, "batches": 0, "checked": 0, "dropped": 0, "canaries": 0, "caught": 0, "discarded": 0, "held": 0}
        log["days"].append(entry)
    for name, value in counts.items():
        if name == "disputed":
            log["disputed"] += value
        elif name == "canaried":
            log["canaried"] = ([key for key in log["canaried"] if key not in value] + list(value))[-CANARIED_KEPT:]
        else:
            entry[name] = entry.get(name, 0) + value
    log["days"] = sorted(log["days"], key=lambda row: row["day"])[-KEPT_DAYS:]
    write_json(LOG, log)


def settle(wrong, work, day=None):
    """검수 결과를 반영한다. wrong은 {열쇠: 까닭}, work는 batch()가 적어 둔 묶음. 한 일을 돌려준다:
    {"outcome": applied|discarded|held, "checked", "dropped", "disputed", "canaries", "caught", "unknown": 묶음에 없는 열쇠들}"""
    settings = plan.checker()
    day = day or today()
    keys, canaries = list(work.get("keys", [])), dict(work.get("canaries", {}))
    caught = sorted(block_key for block_key in canaries if block_key in wrong)
    real = {block_key: str(why).strip() for block_key, why in wrong.items() if block_key in keys}
    done = {"outcome": "applied", "checked": 0, "dropped": 0, "disputed": 0, "canaries": len(canaries), "caught": len(caught),
            "unknown": sorted(block_key for block_key in wrong if block_key not in keys and block_key not in canaries)}
    if canaries and len(caught) < settings["catch"] * len(canaries):
        done["outcome"] = "discarded"   # 일부러 바꾼 번역을 놓쳤다. 이 묶음은 제대로 읽지 않은 것으로 본다
        _record(day, batches=1, discarded=1, canaries=len(canaries), caught=len(caught), canaried=sorted(canaries))
        return done
    if len(real) >= HARSH_MIN and len(real) > settings["harsh"] * len(keys):
        done["outcome"] = "held"        # 틀렸다고 한 것이 지나치게 많다. 반영하지 않고 알린다
        _record(day, batches=1, held=1, canaries=len(canaries), caught=len(caught), canaried=sorted(canaries))
        return done
    earlier = {}
    for entry in review.reviews():
        earlier[entry["key"]] = earlier.get(entry["key"], 0) + 1
    disputed = []
    for block_key, why in real.items():
        if earlier.get(block_key, 0) >= DROPS_BEFORE_DISPUTE:
            disputed.append({"day": day, "key": block_key, "why": why[:200]})
        elif review.drop(block_key, why or "검수에서 틀린 것으로 봄", day):
            done["dropped"] += 1
    where = holders()
    by_act = {}
    for block_key in keys:
        if (block_key not in real or any(row["key"] == block_key for row in disputed)) and block_key in where:
            by_act.setdefault(where[block_key], set()).add(block_key)
    for act_id, block_keys in by_act.items():
        done["checked"] += store.mark(act_id, block_keys)
    done["disputed"] = len(disputed)
    _record(day, batches=1, checked=done["checked"], dropped=done["dropped"], canaries=len(canaries), caught=len(caught), disputed=disputed, canaried=sorted(canaries))
    return done


def progress(documents=None, memory=None):
    """{"translated": 옮긴 문단 수, "checked": 그 가운데 검수를 마친 수, "disputed": 가리지 못한 문단 수, "canaries", "caught"}"""
    if documents is None or memory is None:
        documents, memory = corpus.everything(history=True)
    checked = store.checked_all()
    live = {store.key(text) for _, parts in documents for part in parts for text in corpus.texts(part) if check.needs(text)}
    translated = {block_key for block_key in live if block_key in memory}
    log = _log()
    return {"translated": len(translated), "checked": len(translated & checked), "disputed": len(log["disputed"]),
            "canaries": sum(row.get("canaries", 0) for row in log["days"]), "caught": sum(row.get("caught", 0) for row in log["days"])}


def summary(found=None):
    """보고에 쓰는 한 줄."""
    found = found or progress()
    share = round(100 * found["checked"] / found["translated"]) if found["translated"] else 100
    seeded = f", 일부러 바꾼 번역 {found['canaries']:,}개 가운데 {found['caught']:,}개를 잡음" if found["canaries"] else ""
    disputed = f", 가리지 못한 문단 {found['disputed']:,}개" if found["disputed"] else ""
    return f"검수: 옮긴 문단 {found['translated']:,}개 가운데 {found['checked']:,}개({share}%)를 원문과 견줌{seeded}{disputed}"


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["todo", "apply", "status"])
    parser.add_argument("file", nargs="?", default="")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--seed", default="")
    args = parser.parse_args(argv)
    if args.action == "status":
        print(summary())
        return 0
    if args.action == "todo":
        picked, work, left = batch(args.limit, args.seed)
        if picked:
            write_json(WORK, work)
        text = "\n".join(block["source"] for block in picked)
        print(json.dumps({"blocks": picked, "chars": sum(len(block["source"]) for block in picked), "left": left, "rounds": plan.checker()["rounds"],
                          "glossary": [{"en": term["en"], "ko": term["ko"]} for term in term_lookup.lookup(text, limit=80)] if picked else []},
                         ensure_ascii=False, indent=1))
        return 0
    work = read_json(WORK, None)
    if not work:
        print("읽고 있는 묶음이 없습니다. 먼저 python -m tools.laws.verify todo 로 묶음을 받습니다.")
        return 1
    wrong = (read_json(args.file, {}) or {}).get("wrong")
    if not isinstance(wrong, dict):
        print('결과 파일은 {"wrong": {열쇠: 까닭}} 꼴입니다(틀린 것이 없으면 {"wrong": {}}).')
        return 1
    done = settle(wrong, work)
    pathlib.Path(WORK).unlink(missing_ok=True)
    print(json.dumps(done, ensure_ascii=False))
    return 0 if done["outcome"] == "applied" else 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
