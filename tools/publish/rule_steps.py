"""규제가 따르는 절차와 지금의 세부 단계를 검사하고, 화면에 실을 진행도를 셈한다. 고치는 일도 여기에서 한다(tools/publish/rule_edit.py가 부른다).

절차의 단계는 data/procedures.json의 kinds에 있다(tools/publish/procedures.py). 규제 자료(data/regulations.json)에는 다음을 적는다.
 - procedure: 그 규제가 따르는 절차의 이름. 없으면 화면이 세부 절차를 보여 주지 않는다.
 - 연혁의 사건마다 step: 그 사건이 절차의 어느 단계에서 일어난 일인지. 절차의 단계가 아닌 사건(발표, 설명 자료)에는 적지 않는다.
 - stepNow: 지금 진행 중인 단계들. 기간이 있는 일(위원회 심의, 3자 협상, 이의 제기 기간, 초안 준비)이 진행 중일 때 적는다.
   날짜가 정해진 일을 기다리는 동안(발효 대기, 채택 대기)에는 비운다. 그때는 기록이 있는 마지막 단계의 다음 단계가 '다음'으로 표시된다.
   그 단계가 진행 중이거나 그 단계를 기다리고 있다는 기록이 있을 때만 적는다. 절차상 그럴 때라는 짐작만으로는 적지 않는다
   (예: 제안이 나온 뒤 이사회도 살펴보고 있으리라는 것. 기록이 없으면 그 단계는 '남음'으로 둔다).
 - 사건에 단계를 적는 것은 그 단계의 일이 실제로 있었다는 뜻이다. 아직 일어나지 않았다는 보도나, 그 단계에 앞서 있었던 다른 일에는 적지 않는다.
 - stepNotes: {단계: {"text": 글, "evidence": 근거}}. 날짜는 연혁에 없지만 공식 글로 확인되는 단계의 사실이다
   (예: 이행규정의 전문이 밝힌 CBAM 위원회의 의견). 근거의 꼴은 연혁의 근거와 같다(tools/publish/regulations.py의 evidence_problem).
 - procedureNote: 세부 절차 위에 적는 한두 문장(한 규제가 제안 둘을 함께 다룰 때 어느 것을 기준으로 삼았는지 등).

단계의 상태(진행도의 state)
 - done: 연혁에 그 단계의 사건이 있거나 stepNotes에 적혀 있다. 절차가 끝난 규제에서는 마지막 기록 뒤의 단계도 마친 것으로 본다.
 - now:  stepNow에 든 단계.
 - next: 진행 중인 단계가 없을 때, 기록이 있는 마지막 단계의 바로 다음 단계(기다리고 있는 일).
 - none: 지나갔지만 연혁에 기록이 없는 단계(더 뒤의 단계에 기록이 있다. 같은 때에 따로 나아가는 갈래는 서로를 지나간 것으로 만들지 않는다).
 - todo: 남은 단계.
절차가 끝났다는 것은 큰 단계(at)가 마지막이고 stepNow가 비어 있다는 뜻이다.
큰 단계와의 맞춤: 절차의 단계에 적힌 reach는 그 단계에 이르면 규제의 큰 단계(at)가 적어도 어디까지 와 있어야 하는지다. 둘이 어긋나면 '단계 어긋남'으로 알린다.
 - 세부 단계는 나아갔는데 큰 단계가 그대로인 것: 기록이 있는 단계의 reach가 at보다 크다.
 - 큰 단계는 나아갔는데 세부 단계가 그대로인 것: 절차가 끝나지 않았는데, 기록이 있거나 진행 중인 단계의 reach가 모두 at보다 작다.
 어긋남은 고치는 도중에 잠깐 생길 수 있어(연혁에 줄을 더한 뒤 큰 단계를 고친다) 고치기와 사이트 만들기를 막지는 않고, 검사와 상태 점검이 알린다.

규제 하나의 단계를 찍어 보기: python -m tools.publish.rule_steps --id <규제>   (단계의 이름과 지금의 상태, 그 단계에 적힌 사건의 날짜. 고치기 전에 본다)
절차의 단계만 보기:          python -m tools.publish.rule_steps --kind <절차>
"""
import argparse
import sys

from tools.common.jsonio import read_json
from tools.publish import procedures

FIELDS = ("stepNow", "stepNotes", "procedureNote")
GAP = "단계 어긋남"   # 큰 단계(at)와 세부 단계의 기록이 서로 맞지 않는 것. 고치기와 사이트 만들기를 막지 않는다


def load_kinds():
    """절차의 이름 → 절차. 자료를 읽지 못하면 빈 것."""
    return procedures.kinds_by_key(read_json(procedures.SOURCE, None))


def finished(rule):
    path = rule.get("path") or []
    return bool(path) and rule.get("at") == len(path) - 1 and not rule.get("stepNow")


def _passed(steps, index, reached):
    """기록은 없지만 지나간 단계인가: 더 뒤의 단계에 기록이 있고, 그 단계가 같은 갈래(track)이거나 둘 가운데 하나가 갈래 없는 단계일 때다.

    갈래는 같은 때에 따로 나아가는 일들이다(유럽의회의 심의와 EU 이사회의 심의). 한 갈래가 나아갔다고 다른 갈래가 지나간 것은 아니다.
    """
    mine = steps[index].get("track")
    return any(later > index and (not mine or not steps[later].get("track") or steps[later].get("track") == mine) for later in reached)


def progress(rule, kind):
    """화면에 실을 진행도. 단계마다 상태와 그 단계의 사건(연혁에서의 차례 번호)을 적는다."""
    steps = kind.get("steps", [])
    order = {step["key"]: index for index, step in enumerate(steps)}
    events = {}
    for index, event in enumerate(rule.get("timeline", [])):
        if event.get("step") in order:
            events.setdefault(event["step"], []).append(index)
    notes = {key: note for key, note in (rule.get("stepNotes") or {}).items() if key in order}
    now = [key for key in rule.get("stepNow") or [] if key in order]
    reached = {order[key] for key in list(events) + list(notes) + now}
    done_all = finished(rule)
    rows, next_key = [], ""
    for index, step in enumerate(steps):
        key = step["key"]
        if key in now:
            state = "now"
        elif key in events or key in notes:
            state = "done"
        elif _passed(steps, index, reached):
            state = "none"
        elif done_all:
            state = "done"
        elif not now and not next_key and not step.get("optional") and reached:
            state, next_key = "next", key
        else:
            state = "todo"
        row = {"key": key, "state": state}
        if key in events:
            row["events"] = events[key]
        if key in notes:
            row["note"] = notes[key].get("text", "")
        rows.append(row)
    main = [row for row, step in zip(rows, steps) if not step.get("optional")]
    return {"kind": kind["key"], "steps": rows, "passed": sum(row["state"] in ("done", "none") for row in main), "total": len(main),
            "now": now, "next": next_key, "finished": done_all, **({"note": rule["procedureNote"]} if rule.get("procedureNote") else {})}


def problems(rule, kinds, text_problems, evidence_problem, check=("format", "evidence")):
    """규제 하나의 문제. text_problems(글)과 evidence_problem(근거, 날짜)는 규제 자료의 검사가 쓰는 것을 넘겨받는다."""
    where, found = f"규제 {rule.get('id')}", []
    tagged = [event for event in rule.get("timeline", []) if "step" in event]
    name = rule.get("procedure")
    if not name:
        if tagged or any(field in rule for field in FIELDS):
            found.append((where, "절차(procedure)가 없는데 세부 단계(step, stepNow, stepNotes, procedureNote)가 적혀 있음"))
        return found
    kind = (kinds or {}).get(name)
    if not kind:
        return found + [(where, f"없는 절차: {name}")]
    steps = {step["key"]: step for step in kind.get("steps", [])}
    for event in tagged:
        if event["step"] not in steps:
            found.append((f"{where} {event.get('date')}", f"절차 {name}에 없는 단계: {event['step']}"))
    now = rule.get("stepNow", [])
    if not isinstance(now, list) or len(set(now)) != len(now) or not set(now) <= set(steps):
        found.append((where, f"진행 중인 단계(stepNow)가 절차 {name}의 단계가 아니거나 겹침: {now}"))
    notes = rule.get("stepNotes", {})
    if not isinstance(notes, dict) or not set(notes) <= set(steps):
        found.append((where, f"단계의 사실(stepNotes)이 절차 {name}의 단계가 아님"))
        notes = {}
    for key, note in notes.items():
        spot = f"{where} 단계 {key}"
        if not str((note or {}).get("text", "")).strip():
            found.append((spot, "글(text)이 비어 있음"))
        found += [(spot, problem) for problem in text_problems(str((note or {}).get("text", "")))]
        problem = evidence_problem((note or {}).get("evidence"), "") if "evidence" in check else ""
        if problem:
            found.append((spot, "근거 어긋남: " + problem))
        elif not isinstance((note or {}).get("evidence"), dict):
            found.append((spot, "근거(evidence)가 없음"))
    if "procedureNote" in rule:
        if not str(rule["procedureNote"]).strip():
            found.append((where, "절차 덧붙임(procedureNote)이 비어 있음"))
        found += [(f"{where} procedureNote", problem) for problem in text_problems(str(rule["procedureNote"]))]
    recorded = {event["step"] for event in tagged if event["step"] in steps} | set(notes)
    if not recorded and not now:
        found.append((where, "세부 단계의 기록이 하나도 없음(연혁의 step이나 stepNow)"))
    if isinstance(rule.get("at"), int):
        need = max((steps[key]["reach"] for key in recorded if "reach" in steps[key]), default=None)
        if need is not None and rule["at"] < need:
            found.append((where, f"{GAP}: 큰 단계(at {rule['at']})가 세부 단계의 기록보다 뒤처져 있음(적어도 {need}이어야 함)"))
        came = max((steps[key]["reach"] for key in recorded | (set(now) & set(steps)) if "reach" in steps[key]), default=None)
        if came is not None and not finished(rule) and came < rule["at"]:
            found.append((where, f"{GAP}: 큰 단계(at {rule['at']})는 나아갔는데 세부 단계의 기록이 따라오지 못함(연혁의 step이나 stepNow를 고칠 것)"))
    return found


# 아래는 고치는 일이다(rule_edit가 부른다). rule은 규제 하나, args는 명령줄의 값이다.

def tag(rule, args):
    """연혁의 한 줄에 단계를 적거나(--step <이름>) 지운다(--step "")."""
    hits = [event for event in rule.get("timeline", []) if event["date"] == args.date and event["text"].startswith(args.starts)]
    if len(hits) != 1:
        raise SystemExit(f"고칠 줄이 하나로 정해지지 않음(맞는 줄 {len(hits)}개)")
    if args.step:
        hits[0]["step"] = args.step
    else:
        hits[0].pop("step", None)


def note(rule, args):
    """날짜 없이 공식 글로 확인되는 단계의 사실을 적거나(--text), 지운다(--text "")."""
    notes = dict(rule.get("stepNotes") or {})
    if not args.text:
        notes.pop(args.step, None)
    elif args.index:
        notes[args.step] = {"text": args.text, "evidence": {"index": args.index, "where": dict(pair.split("=", 1) for pair in args.where)}}
    else:
        notes[args.step] = {"text": args.text, "evidence": {"path": args.path, "contains": args.contains}}
    if notes:
        rule["stepNotes"] = notes
    else:
        rule.pop("stepNotes", None)


def set_fields(rule, args):
    """set 명령의 절차 값: --procedure, --step-now(쉼표로 여럿, ""는 지움), --procedure-note(""는 지움)."""
    procedure = getattr(args, "procedure", None)
    if procedure == "":
        for field in ("procedure",) + FIELDS:
            rule.pop(field, None)
        for event in rule.get("timeline", []):
            event.pop("step", None)
    elif procedure is not None:
        rule["procedure"] = procedure
    now = getattr(args, "step_now", None)
    if now == "":
        rule.pop("stepNow", None)
    elif now is not None:
        rule["stepNow"] = [key.strip() for key in now.split(",") if key.strip()]
    text = getattr(args, "procedure_note", None)
    if text == "":
        rule.pop("procedureNote", None)
    elif text is not None:
        rule["procedureNote"] = text


STATES = {"done": "마침", "now": "진행 중", "next": "다음", "none": "기록 없음", "todo": "남음"}


def table(kind, rule=None):
    """절차의 단계를 한 줄씩 적은 글. 규제를 주면 단계마다의 상태와 그 단계에 적힌 사건의 날짜를 붙인다."""
    seen = {row["key"]: row for row in progress(rule, kind)["steps"]} if rule else {}
    timeline = (rule or {}).get("timeline", [])
    lines = []
    for step in kind.get("steps", []):
        row = seen.get(step["key"], {})
        dates = ", ".join(timeline[index]["date"] for index in row.get("events", []))
        parts = [STATES.get(row.get("state"), "") if rule else "", step["key"], step.get("name", ""),
                 f"reach {step['reach']}" if "reach" in step else "", "(없을 수 있는 단계)" if step.get("optional") else "", dates, "(날짜 없는 사실 있음)" if row.get("note") else ""]
        lines.append("  " + " | ".join(part for part in parts if part))
    return lines


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", default="")
    parser.add_argument("--kind", default="")
    args = parser.parse_args(argv)
    kinds = load_kinds()
    if args.kind:
        if args.kind not in kinds:
            print(f"없는 절차: {args.kind}(있는 절차: {', '.join(kinds)})")
            return 1
        print(f"{args.kind}: {kinds[args.kind].get('name', '')}")
        print("\n".join(table(kinds[args.kind])))
        return 0
    rule = next((row for row in (read_json("data/regulations.json", {}) or {}).get("regulations", []) if row.get("id") == args.id), None)
    if rule is None:
        print(f"없는 규제: {args.id}")
        return 1
    if rule.get("procedure") not in kinds:
        print(f"{args.id}: 세부 절차가 적혀 있지 않음(있는 절차: {', '.join(kinds)})")
        return 0
    kind = kinds[rule["procedure"]]
    path = rule.get("path") or []
    at = rule.get("at")
    print(f"{args.id}: 절차 {kind['key']}({kind.get('name', '')}), 큰 단계 at {at}({path[at] if isinstance(at, int) and at < len(path) else ''}) / 마지막 {len(path) - 1}, "
          f"진행 중 {rule.get('stepNow') or '없음'}")
    print("\n".join(table(kind, rule)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
