"""규제별 진행 상황(data/regulations.json)을 검사하고, 사이트에 실을 모양으로 바꾼다.

검사: python -m tools.publish.regulations            (문제가 있으면 0이 아닌 값으로 끝난다)
한 규제의 연혁은 사건마다 근거를 가진다.
 - basis "stored": 모아 둔 공식 자료와 맞춰 본 것. evidence에 어느 자료의 무엇과 맞추는지 적으며, 이 도구가 실제로 맞춰 본다.
 - basis "web":    공식 화면을 읽고 확인한 것(자동으로 받을 수 없는 화면). checkedOn에 확인한 날을 적는다.
 - basis "press":  공식 발표가 없어 언론 보도로만 아는 것. 글에 '보도'라는 말이 있어야 하고, 사이트에서도 따로 표시한다.
"""
import pathlib
import re
import sys

from tools.check import style_check, term_check
from tools.common.jsonio import read_json

SOURCE = "data/regulations.json"
ARCHIVE = pathlib.Path("collected/archive")
DATE = re.compile(r"^\d{4}(-\d{2}(-\d{2})?)?$")
BASES = {"stored", "web", "press"}
TEXT_FIELDS = ["summary", "status", "next", "nextTitle"]
RELATED_LIMIT = 8


def evidence_problem(evidence, date):
    """근거가 모아 둔 자료와 맞는지 본다. 맞으면 빈 글, 아니면 사유."""
    if not isinstance(evidence, dict):
        return "근거(evidence)가 없음"
    if "index" in evidence:
        entries = read_json(ARCHIVE / f"{evidence['index']}.json", {}).get("entries", [])
        where = evidence.get("where", {})
        if not where:
            return "근거에 찾을 값(where)이 없음"
        if not any(all(str(entry.get(key, "")) == str(value) for key, value in where.items()) for entry in entries):
            return f"{evidence['index']} 목록에 {where}에 맞는 줄이 없음"
        return ""
    if "path" in evidence:
        path = pathlib.Path(evidence["path"])
        if ARCHIVE not in path.parents and pathlib.Path("data") not in path.parents:
            return "근거 파일이 모아 둔 자료가 아님"
        if not path.exists():
            return f"근거 파일이 없음: {path}"
        text = path.read_text(encoding="utf-8")
        missing = [phrase for phrase in evidence.get("contains", []) if phrase not in text]
        present = [phrase for phrase in evidence.get("lacks", []) if phrase.lower() in text.lower()]  # '그런 조항이 없음'의 근거
        if not evidence.get("contains") and not evidence.get("lacks"):
            return "근거에 찾을 글(contains)이나 없어야 할 글(lacks)이 없음"
        if missing:
            return f"근거 파일에 없는 글: {missing}"
        return f"근거 파일에 없어야 할 글이 있음: {present}" if present else ""
    return "근거의 꼴을 알 수 없음"


def text_problems(text, term_index):
    found = [f"표기 규칙({hit['rule']}: {hit['sample']})" for hit in style_check.check(text) if hit["hard"]]
    found += [f"쓰지 않는 용어({hit['avoid']} → {hit['use']})" for hit in term_check.check(text, term_index) if hit["hard"]]
    return found


def position_problems(rule, term_index, kinds):
    """기관별 입장 비교표(positions)의 문제. 표가 없으면 빈 목록.

    표는 기관의 목록(parties: key, name, source, link)과 줄의 목록(rows: topic과 기관 key마다의 칸)이다.
    칸은 {"text": 글, "evidence": 근거}이고, 그 기관의 문서가 다루지 않는 줄은 칸을 비운다(없거나 text가 빈 글).
    """
    table = rule.get("positions")
    if table is None:
        return []
    where, found = f"규제 {rule.get('id')} 비교표", []
    parties = table.get("parties", [])
    keys = [party.get("key") for party in parties]
    if len(keys) < 2 or len(set(keys)) != len(keys) or not DATE.match(str(table.get("asOf", ""))):
        found.append((where, "기관이 둘보다 적거나 겹치거나, 기준일(asOf)이 날짜가 아님"))
    for party in parties:
        if not party.get("name") or not party.get("source") or not str(party.get("link", "")).startswith("https://"):
            found.append((where, f"기관의 이름, 문서 이름, 주소(https)가 온전하지 않음: {party.get('key')}"))
    found += [(where, problem) for problem in text_problems(str(table.get("note", "")), term_index)]
    if not table.get("rows"):
        found.append((where, "줄이 없음"))
    for row in table.get("rows", []):
        spot = f"{where} '{row.get('topic', '')}'"
        if not str(row.get("topic", "")).strip():
            found.append((spot, "줄의 이름(topic)이 비어 있음"))
        if not any(str((row.get(key) or {}).get("text", "")).strip() for key in keys):
            found.append((spot, "칸이 모두 비어 있음"))
        for key in keys:
            cell = row.get(key) or {}
            if not str(cell.get("text", "")).strip():
                continue
            found += [(f"{spot} {key}", problem) for problem in text_problems(cell["text"], term_index)]
            problem = evidence_problem(cell.get("evidence"), "") if "evidence" in kinds else ""
            if problem:
                found.append((f"{spot} {key}", "근거 어긋남: " + problem))
    return found


def problems(body, term_index=None, kinds=("format", "evidence")):
    """자료 전체의 문제를 (어디, 무엇) 목록으로 돌려준다.

    kinds로 볼 것을 고른다. "format"은 자료의 꼴과 글의 표기, "evidence"는 연혁의 근거가 모아 둔 자료와 맞는지다.
    모아 둔 자료는 날마다 바뀌므로(예: 새 판결이 올라옴) 근거가 어긋난 것은 사이트 만들기를 멈추지 않고 점검 결과로만 알린다.
    """
    term_index = term_index or term_check.load()
    found = []
    if not DATE.match(str(body.get("asOf", ""))):
        found.append(("머리", "기준일(asOf)이 날짜가 아님"))
    groups = [group.get("code") for group in body.get("groups", [])]
    for group in body.get("groups", []):
        for field in ("name", "about"):
            found += [(f"묶음 {group.get('code')}", problem) for problem in text_problems(str(group.get(field, "")), term_index)]
    seen = set()
    for rule in body.get("regulations", []):
        where = f"규제 {rule.get('id')}"
        if not rule.get("id") or rule["id"] in seen or not re.match(r"^[a-z0-9-]+$", rule["id"]):
            found.append((where, "id가 없거나 겹치거나 소문자·숫자·붙임표가 아님"))
        seen.add(rule.get("id"))
        if rule.get("group") not in groups:
            found.append((where, f"없는 묶음: {rule.get('group')}"))
        for field in ("name", "official", "kind", "stage", "summary", "status"):
            if not str(rule.get(field, "")).strip():
                found.append((where, f"{field}이(가) 비어 있음"))
        path, at = rule.get("path", []), rule.get("at")
        if path and not (isinstance(at, int) and 0 <= at < len(path)):
            found.append((where, "단계 위치(at)가 단계 목록(path) 밖임"))
        if rule.get("nextDate") and not DATE.match(str(rule["nextDate"])):
            found.append((where, "다음 일정 날짜(nextDate)가 날짜가 아님"))
        for field in TEXT_FIELDS:
            found += [(f"{where} {field}", problem) for problem in text_problems(str(rule.get(field, "")), term_index)]
        timeline = rule.get("timeline", [])
        if not timeline:
            found.append((where, "연혁이 비어 있음"))
        if [event.get("date", "") for event in timeline] != sorted(event.get("date", "") for event in timeline):
            found.append((where, "연혁이 날짜순이 아님"))
        for event in timeline:
            spot = f"{where} {event.get('date')}"
            if not DATE.match(str(event.get("date", ""))):
                found.append((spot, "날짜가 아님"))
            if not str(event.get("link", "")).startswith("https://") or not event.get("source"):
                found.append((spot, "원문 주소(https)나 출처 이름이 없음"))
            found += [(spot, problem) for problem in text_problems(str(event.get("text", "")), term_index)]
            basis = event.get("basis")
            if basis not in BASES:
                found.append((spot, f"근거 종류가 {sorted(BASES)} 가운데 하나가 아님"))
            elif basis == "stored":
                problem = evidence_problem(event.get("evidence"), event.get("date")) if "evidence" in kinds else ""
                if problem:
                    found.append((spot, "근거 어긋남: " + problem))
            else:
                if not DATE.match(str(event.get("checkedOn", ""))):
                    found.append((spot, "확인한 날(checkedOn)이 없음"))
                if basis == "press" and "보도" not in str(event.get("text", "")):
                    found.append((spot, "언론 보도로만 아는 일인데 글에 '보도'라는 말이 없음"))
        for link in rule.get("links", []):
            if not str(link.get("url", "")).startswith("https://") or not link.get("text"):
                found.append((where, f"링크가 온전하지 않음: {link}"))
        found += position_problems(rule, term_index, kinds)
    return found if "format" in kinds else [row for row in found if row[1].startswith("근거 어긋남")]


def related_items(rule, items):
    """이 규제와 이어진 소식의 id. 출처 코드가 같거나 제목·요약에 정해 둔 낱말이 든 소식을 새 것부터 고른다."""
    related = rule.get("related", {})
    sources, words, fixed = set(related.get("sources", [])), related.get("words", []), related.get("items", [])
    picked = []
    for item in items:
        text = f"{item.get('title', '')} {item.get('summary', '')}"
        if item.get("id") in fixed or item.get("sourceCode") in sources or any(word in text for word in words):
            picked.append(item)
    picked.sort(key=lambda item: str(item.get("published") or ""), reverse=True)
    return [item["id"] for item in picked[:RELATED_LIMIT]]


def public(body, items):
    """사이트에 실을 모양. 안에서만 쓰는 값(근거, 확인한 날, 소식 고르는 조건)은 뺀다."""
    rules = []
    for rule in body.get("regulations", []):
        row = {key: value for key, value in rule.items() if key not in ("related", "timeline")}
        row["timeline"] = [{"date": event["date"], "text": event["text"], "source": event["source"], "link": event["link"],
                            **({"press": True} if event.get("basis") == "press" else {})} for event in rule.get("timeline", [])]
        if rule.get("positions"):  # 비교표: 칸의 근거는 빼고 글만 싣는다
            keys = [party.get("key") for party in rule["positions"].get("parties", [])]
            row["positions"] = {**rule["positions"], "rows": [{"topic": line.get("topic", ""), **{key: {"text": (line.get(key) or {}).get("text", "")} for key in keys}}
                                                             for line in rule["positions"].get("rows", [])]}
        row["relatedItems"] = related_items(rule, items)
        rules.append(row)
    return {"asOf": body.get("asOf", ""), "groups": body.get("groups", []), "regulations": rules}


def main(argv):
    body = read_json(argv[0] if argv else SOURCE, None)
    if body is None:
        print("자료를 읽지 못함")
        return 1
    found = problems(body)
    for where, what in found:
        print(f"문제: {where}: {what}")
    kinds = {}
    for rule in body.get("regulations", []):
        for event in rule.get("timeline", []):
            kinds[event.get("basis")] = kinds.get(event.get("basis"), 0) + 1
    print(f"규제 {len(body.get('regulations', []))}건, 연혁 {sum(kinds.values())}줄(근거별 {kinds}), 문제 {len(found)}건")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
