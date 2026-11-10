"""규제 진행 상황 자료(data/regulations.json)를 고치는 도구. 손으로 JSON을 고치다 생기는 실수를 막는다.

연혁에 한 줄 더하기:
  python -m tools.publish.rule_edit add-event --id cbam-downstream --date 2026-12-01 --text "…했습니다." --source "유럽의회 입법 관측소" \\
      --link "https://…" --index ep-oeil --where procedure="2025/0419(COD)" --where date=2026-12-01
  (모아 둔 글에서 근거를 찾을 때는 --path collected/archive/pages/… --contains "1 December 2026")
  (공식 화면을 읽고 확인했으면 --basis web, 언론 보도면 --basis press. 이때는 근거 대신 확인한 날이 오늘로 적힌다)
연혁에서 한 줄 빼기:   python -m tools.publish.rule_edit drop-event --id <규제> --date <날짜> --starts "<글의 앞부분>"
단계와 설명 고치기:    python -m tools.publish.rule_edit set --id <규제> [--stage "…"] [--at 2] [--tone progress] [--status "…"] [--next "…"] [--next-date 2026-12-14] [--next-title "…"]
                      (--next "", --next-date "", --next-title ""는 그 값을 지운다. --next-title은 일정 화면에 보일 이름으로, 그 날 있을 일을 적은 짧은 구다)
새 규제 더하기:        python -m tools.publish.rule_edit add-rule --file rule.json   (rule.json은 규제 하나의 JSON)
고칠 때마다 기준일(asOf)이 오늘로 바뀌고, 연혁은 날짜순으로 다시 놓인다. 끝에 자료 전체를 검사해 문제를 찍는다(문제가 있으면 1로 끝난다).
"""
import argparse
import json
import sys

from tools.common.jsonio import read_json, today, write_json
from tools.publish import regulations

TONES = ["live", "progress", "planned", "adopted", "dispute", "ended"]


def find(body, rule_id):
    for rule in body.get("regulations", []):
        if rule.get("id") == rule_id:
            return rule
    raise SystemExit(f"없는 규제: {rule_id}")


def add_event(body, args):
    rule = find(body, args.id)
    event = {"date": args.date, "text": args.text, "source": args.source, "link": args.link, "basis": args.basis}
    if args.basis == "stored":
        if args.index:
            event["evidence"] = {"index": args.index, "where": dict(pair.split("=", 1) for pair in args.where)}
        else:
            event["evidence"] = {"path": args.path, "contains": args.contains}
    else:
        event["checkedOn"] = today()
    if any(old["date"] == event["date"] and old["text"] == event["text"] for old in rule["timeline"]):
        raise SystemExit("같은 줄이 이미 있음")
    rule["timeline"] = sorted(rule["timeline"] + [event], key=lambda row: row["date"])


def drop_event(body, args):
    rule = find(body, args.id)
    kept = [row for row in rule["timeline"] if not (row["date"] == args.date and row["text"].startswith(args.starts))]
    if len(kept) != len(rule["timeline"]) - 1:
        raise SystemExit(f"뺄 줄이 하나로 정해지지 않음(맞는 줄 {len(rule['timeline']) - len(kept)}개)")
    rule["timeline"] = kept


def set_fields(body, args):
    rule = find(body, args.id)
    for field, value in (("stage", args.stage), ("tone", args.tone), ("status", args.status)):
        if value is not None:
            rule[field] = value
    if args.at is not None:
        rule["at"] = args.at
    for field, value in (("next", args.next), ("nextDate", args.next_date), ("nextTitle", args.next_title)):
        if value == "":
            rule.pop(field, None)
        elif value is not None:
            rule[field] = value


def add_rule(body, args):
    rule = read_json(args.file, None)
    if not isinstance(rule, dict) or not rule.get("id"):
        raise SystemExit("규제 파일을 읽지 못함")
    if any(old.get("id") == rule["id"] for old in body["regulations"]):
        raise SystemExit("같은 id의 규제가 이미 있음")
    rule["timeline"] = sorted(rule.get("timeline", []), key=lambda row: row.get("date", ""))
    last = max((index for index, old in enumerate(body["regulations"]) if old.get("group") == rule.get("group")), default=len(body["regulations"]) - 1)
    body["regulations"].insert(last + 1, rule)


def main(argv):
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    event = commands.add_parser("add-event")
    for name in ("--id", "--date", "--text", "--source", "--link"):
        event.add_argument(name, required=True)
    event.add_argument("--basis", choices=sorted(regulations.BASES), default="stored")
    event.add_argument("--index", default="")
    event.add_argument("--where", action="append", default=[])
    event.add_argument("--path", default="")
    event.add_argument("--contains", action="append", default=[])
    drop = commands.add_parser("drop-event")
    for name in ("--id", "--date", "--starts"):
        drop.add_argument(name, required=True)
    change = commands.add_parser("set")
    change.add_argument("--id", required=True)
    change.add_argument("--stage")
    change.add_argument("--at", type=int)
    change.add_argument("--tone", choices=TONES)
    change.add_argument("--status")
    change.add_argument("--next")
    change.add_argument("--next-date")
    change.add_argument("--next-title")
    new = commands.add_parser("add-rule")
    new.add_argument("--file", required=True)
    args = parser.parse_args(argv)

    body = read_json(regulations.SOURCE, None)
    if body is None:
        print("자료를 읽지 못함")
        return 1
    {"add-event": add_event, "drop-event": drop_event, "set": set_fields, "add-rule": add_rule}[args.command](body, args)
    body["asOf"] = today()
    found = regulations.problems(body)
    for where, what in found:
        print(f"문제: {where}: {what}")
    if found:
        print("문제가 있어 고치지 않았습니다.")
        return 1
    write_json(regulations.SOURCE, body)
    print(json.dumps({"ok": True, "command": args.command, "id": getattr(args, "id", ""), "asOf": body["asOf"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
