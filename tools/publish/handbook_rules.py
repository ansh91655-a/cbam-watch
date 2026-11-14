"""해설서의 절이 가리키는 규제가, 해설서를 맞춰 본 뒤에 달라졌는지 본다.

해설서의 절은 관련 화면(see)으로 규제 화면(#rules-<id>)을 가리킨다: 그 절의 내용을 정하거나 바꿀 규제다.
규제의 단계가 바뀌거나 연혁에 줄이 더해지면 그 절의 글도 다시 봐야 할 수 있다. 그래서 해설서에는 맞춰 본 때의 규제 모습을 적어 둔다.
  "rulesSeen": {"ir-carbon-price": {"stage": "채택 보도(공식 확인 전)", "events": 5}, …}     (data/handbook.json의 맨 위. 규제의 분석 글이 쓰는 것과 같은 꼴)
지금의 규제 자료(data/regulations.json)가 이 기록과 다르면 상태 점검이 일일 보고에 올린다(tools/run/reference_health.py).
글이 틀렸다는 뜻은 아니므로 사이트 만들기는 멈추지 않는다. 그 절을 원문과 다시 맞춰 본 뒤에 기록을 지금 모습으로 고친다.

쓰는 법: python -m tools.publish.handbook_rules            달라진 규제와 그 규제를 가리키는 절을 찍는다
        python -m tools.publish.handbook_rules --accept   지금의 규제 모습을 '맞춰 본 것'으로 적는다(절을 다시 본 뒤에 돌린다)
"""
import re
import sys

from tools.common.jsonio import read_json, write_json
from tools.publish import analysis

SOURCE = "data/handbook.json"
RULES = "data/regulations.json"
RULE_VIEW = re.compile(r"^#rules-([a-z0-9-]+)$")


def pointed(body, rule_ids=None):
    """해설서의 절이 관련 화면으로 가리킨 규제: {규제 id: ["장.절", …]}. rule_ids를 주면 그 가운데 있는 것만(규제 묶음의 주소와 가른다)."""
    found = {}
    for chapter in (body or {}).get("chapters", []):
        for section in chapter.get("sections", []):
            for link in section.get("see") or []:
                hit = RULE_VIEW.match(str(link.get("href", "")))
                if hit and (rule_ids is None or hit.group(1) in rule_ids):
                    found.setdefault(hit.group(1), []).append(f"{chapter['id']}.{section['id']}")
    return found


def changed(body, rules):
    """[(규제 id, 규제의 이름, ["장.절", …], 달라진 것)]: 해설서를 맞춰 본 뒤에 단계나 연혁이 달라진 규제. rules는 규제 자료의 regulations다."""
    by_id = {rule.get("id"): rule for rule in rules or []}
    seen = (body or {}).get("rulesSeen") or {}
    found = []
    for rule_id, sections in pointed(body, set(by_id)).items():
        rule, before = by_id[rule_id], seen.get(rule_id)
        now = analysis.based_on(rule)
        if before == now:
            continue
        if not isinstance(before, dict):
            why = "맞춰 본 기록이 없음"
        elif before.get("stage") != now["stage"]:
            why = f"단계가 '{before.get('stage', '')}'에서 '{now['stage']}'(으)로 바뀜"
        else:
            why = f"연혁이 {before.get('events', 0)}줄에서 {now['events']}줄로 달라짐"
        found.append((rule_id, rule.get("name", rule_id), sections, why))
    return found


def accept(body, rules):
    """맞춰 본 기록을 지금의 규제 모습으로 고친 해설서를 돌려준다(가리키는 규제만 적는다)."""
    by_id = {rule.get("id"): rule for rule in rules or []}
    return {**body, "rulesSeen": {rule_id: analysis.based_on(by_id[rule_id]) for rule_id in sorted(pointed(body, set(by_id)))}}


def lines(body, rules):
    """일일 보고에 올리는 줄."""
    return [f"규제 '{name}'이(가) 해설서를 맞춰 본 뒤에 달라짐({why}). 이 규제를 가리키는 절을 다시 볼 것: {', '.join(sections)}" for _, name, sections, why in changed(body, rules)]


def main(argv):
    body = read_json(SOURCE, None)
    rules = (read_json(RULES, {}) or {}).get("regulations", [])
    if body is None or not rules:
        print(f"읽지 못함: {SOURCE} 또는 {RULES}")
        return 1
    if argv == ["--accept"]:
        write_json(SOURCE, accept(body, rules))
        print(f"맞춰 본 규제 {len(pointed(body, {rule.get('id') for rule in rules}))}건을 지금 모습으로 적음")
        return 0
    if argv:
        print(__doc__.strip().split("쓰는 법:")[1].strip())
        return 2
    found = lines(body, rules)
    for line in found:
        print(line)
    print(f"해설서가 가리키는 규제 {len(pointed(body, {rule.get('id') for rule in rules}))}건, 달라진 것 {len(found)}건")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
