"""번역하는 모델이나 방법을 견주는 시험. 이미 옮겨 둔 문단을 앞의 번역을 보여 주지 않고 다시 옮기게 해서 두 번역을 견준다.

시험은 trials/request.json으로 청한다: {"name": 시험 이름, "act": 문서 id, "limit": 그 문서의 처음부터 옮길 원문 글자 수, "note": 무엇을 보려는 시험인지}
시험의 번역은 trials/<이름>.json에만 쌓이고, 사이트에 싣는 번역 자료(data/laws-ko)는 건드리지 않는다.

번역을 하는 실행이 쓰는 법
  python -m tools.laws.trial todo                            다음 묶음을 찍는다(tools.laws.todo와 같은 꼴). 청한 시험이 없거나 다 옮겼으면 blocks가 비어 있다
  python -m tools.laws.trial apply <번역 파일> --model <모델>   검사해서 시험 파일에 넣는다. 걸린 문단은 까닭과 함께 찍는다(끝내는 값 1)
  python -m tools.laws.trial done                            다 옮겼으면 청한 것을 지우고 요약을 찍는다
견줄 때 쓰는 법
  python -m tools.laws.trial compare <이름> [--show <보일 문단 수>] [--out <파일>]
"""
import argparse
import json
import pathlib
import sys

from tools.common.jsonio import now_kst, read_json, write_json
from tools.laws import apply, check, plan, store, todo

FOLDER = "trials"
REQUEST = f"{FOLDER}/request.json"
BATCH = "bulk"  # 한 묶음의 분량은 이 실행의 것을 쓴다


def request():
    """청해 둔 시험. 없으면 None."""
    found = read_json(REQUEST, None)
    return found if isinstance(found, dict) and found.get("name") and found.get("act") else None


def path_of(name):
    return f"{FOLDER}/{name}.json"


def load(name):
    return read_json(path_of(name), None) or {"name": name, "model": "", "startedAt": "", "finishedAt": "", "rounds": [], "firstRejected": {}, "blocks": {}}


def target(asked):
    """시험에서 옮길 문단 모두(문서의 처음부터 limit 글자까지). 앞의 번역이 없는 것으로 보고 고른다."""
    picked, _ = todo.pick(int(asked.get("limit") or 0) or None, asked["act"], memory={})
    return picked


def pending(asked, record):
    return [block for block in target(asked) if block["key"] not in record["blocks"]]


def next_batch(asked, record):
    """다음 묶음과 그 뒤에 남는 분량."""
    limit, picked, size = plan.runner(BATCH)["limit"], [], 0
    waiting = pending(asked, record)
    for block in waiting:
        if picked and size + len(block["text"]) > limit:
            break
        picked.append(block)
        size += len(block["text"])
    rest = waiting[len(picked):]
    return picked, {"blocks": len(rest), "chars": sum(len(block["text"]) for block in rest)}


def take(record, blocks, known, model="", moment=""):
    """번역 한 묶음을 검사해 시험 기록에 넣는다: (받은 수, [(열쇠, 까닭들)], [(열쇠, 알릴 것들)])"""
    accepted, rejected, noted = apply.sort(blocks, known)
    fresh = {block_key: korean for group in accepted.values() for block_key, korean in group.items()}
    record["blocks"].update(fresh)
    for block_key, why in rejected:
        record["firstRejected"].setdefault(block_key, why)
    record["model"] = model or record["model"]
    record["startedAt"] = record["startedAt"] or moment
    record["rounds"].append({"at": moment, "sent": len(blocks), "accepted": len(fresh), "rejected": len(rejected)})
    return len(fresh), rejected, noted


def compare(name, memory=None, known=None):
    """시험의 번역과 실려 있는 번역을 견준다: {"blocks", "same", "firstRejected", "rows": [{"key", "source", "ours", "theirs"}]}"""
    record = load(name)
    memory = store.load_all() if memory is None else memory
    known = apply.sources() if known is None else known
    rows = [{"key": block_key, "source": known[block_key][1], "ours": memory[block_key], "theirs": korean}
            for block_key, korean in record["blocks"].items() if block_key in memory and block_key in known]
    flat = lambda text: "".join(str(text).split())  # noqa: E731
    return {"name": name, "model": record["model"], "startedAt": record["startedAt"], "finishedAt": record["finishedAt"],
            "blocks": len(record["blocks"]), "compared": len(rows), "same": sum(flat(row["ours"]) == flat(row["theirs"]) for row in rows),
            "firstRejected": len(record["firstRejected"]), "rounds": len(record["rounds"]),
            "sourceChars": sum(len(row["source"]) for row in rows), "oursChars": sum(len(row["ours"]) for row in rows),
            "theirsChars": sum(len(row["theirs"]) for row in rows), "rows": rows}


def _report(rows, shown):
    """견준 문단을 읽기 좋게 적는다. shown이 0이면 모두."""
    differing = [row for row in rows if "".join(row["ours"].split()) != "".join(row["theirs"].split())]
    step = max(1, len(differing) // shown) if shown else 1
    lines = []
    for row in differing[::step][:shown or None]:
        lines += [f"[{row['key']}]", f"  원문: {row['source']}", f"  실린 번역: {row['ours']}", f"  시험 번역: {row['theirs']}", ""]
    return "\n".join(lines)


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["todo", "apply", "done", "compare"])
    parser.add_argument("target", nargs="?", default="")
    parser.add_argument("--model", default="")
    parser.add_argument("--show", type=int, default=12)
    parser.add_argument("--out", default="")
    args = parser.parse_args(argv)
    if args.action == "compare":
        found = compare(args.target)
        report = _report(found.pop("rows"), 0 if args.out else args.show)
        if args.out:
            pathlib.Path(args.out).write_text(report, encoding="utf-8")
        else:
            print(report)
        print(json.dumps(found, ensure_ascii=False))
        return 0
    asked = request()
    if asked is None:
        print(json.dumps({"blocks": [], "note": "청한 시험이 없음"}, ensure_ascii=False))
        return 0
    record = load(asked["name"])
    if args.action == "todo":
        picked, left = next_batch(asked, record)
        print(json.dumps(todo.answer(picked, left, trial=asked["name"], note=asked.get("note", "")), ensure_ascii=False, indent=1))
        return 0
    if args.action == "apply":
        blocks = (read_json(args.target, {}) or {}).get("blocks", {})
        if not isinstance(blocks, dict) or not blocks:
            print("번역 파일에 blocks가 없습니다.")
            return 1
        count, rejected, noted = take(record, blocks, apply.sources(), args.model, now_kst().isoformat(timespec="seconds"))
        write_json(path_of(asked["name"]), record)
        for block_key, why in noted:
            shown = [text for text in why if not text.startswith("용어:")]
            if shown:
                print(f"알림 {block_key}: {'; '.join(shown)}")
        for block_key, why in rejected:
            print(f"걸림 {block_key}: {'; '.join(why)}")
        print(json.dumps({"accepted": count, "rejected": len(rejected), "left": len(pending(asked, record))}, ensure_ascii=False))
        return 1 if rejected else 0
    left = pending(asked, record)
    if left:
        print(json.dumps({"finished": False, "left": len(left)}, ensure_ascii=False))
        return 1
    record["finishedAt"] = record["finishedAt"] or now_kst().isoformat(timespec="seconds")
    write_json(path_of(asked["name"]), record)
    pathlib.Path(REQUEST).unlink()
    print(json.dumps({"finished": True, "name": asked["name"], "blocks": len(record["blocks"]), "firstRejected": len(record["firstRejected"]), "rounds": len(record["rounds"])}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
