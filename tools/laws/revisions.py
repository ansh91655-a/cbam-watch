"""문서의 앞선 판과 지금의 판을 견줘 '달라진 곳'을 만든다. 규정 원문 화면이 문서마다 달라진 문단을 옛 글과 나란히 보여 준다.

앞선 판
- 법령: tools.archive.earlier가 남겨 둔 글(관보에 실린 처음 글, 지난 통합본).
- EU 집행위원회 문서: 원문 대장(originals/state.json)에 남아 있는 지난 판의 글. 새 파일로 바뀐 문서는 바뀌기 전 문서(replaces)의 판까지 잇는다.
판을 이른 것부터 늘어놓고 이웃한 두 판마다 견준다(tools.laws.compare). 가장 새 대조가 맨 앞이다.

앞선 판에만 있는 문단(바뀌기 전의 글, 빠진 글)에는 번역이 없을 수 있다. 그 문단들을 옮기도록 숨은 문서를 만들어 번역과 검수의 차례에 넣는다(history).
숨은 문서의 id는 "<문서 id>-was-<판의 날짜>"이고 사이트의 목록과 검색, PDF에는 싣지 않는다(tools.laws.corpus.everything(history=True)로만 나온다).
지금의 글이 새 판으로 바뀌어 떨어져 나간 번역은 번역 자료에 남아 있으므로, 그런 문단은 다시 옮기지 않고 그대로 쓰인다.
그래서 번역 자료의 '쓰이지 않는 번역'을 지울 때에는 숨은 문서가 쓰는 것을 남겨야 한다(tools.laws.status의 unused가 숨은 문서의 것은 세지 않는다).
"""
import json
import pathlib

from tools.archive import earlier
from tools.common.jsonio import read_json
from tools.laws import compare, corpus

STATE = "originals/state.json"
MARK = "-was-"   # 숨은 문서의 id에 드는 말
TURN = 900       # 숨은 문서는 같은 갈래의 문서를 모두 옮긴 뒤에 옮긴다


def _act_chain(act):
    now = act.get("consolidated") or "9999"
    found = []
    for row in earlier.entries():
        if row.get("act") != act.get("celex") or not str(row.get("date", "")) < now or not pathlib.Path(row.get("textPath", "")).is_file():
            continue
        label = f"{row['date']} 관보에 실린 처음 글" if row.get("kind") == "adopted" else f"{row['date']} 통합본"
        found.append({"tag": row["date"].replace("-", ""), "date": row["date"], "label": label, "path": row["textPath"], "url": row.get("url", "")})
    return sorted(found, key=lambda row: row["date"])


def _document_chain(act):
    docs = (read_json(STATE, {}) or {}).get("docs") or {}
    doc = next((doc for doc in docs.values() if doc.get("versions") and doc["versions"][-1].get("text") == act.get("path")), None)
    line, seen = [], set()
    while doc and doc["id"] not in seen:   # 바뀌기 전의 문서로 거슬러 올라간다
        seen.add(doc["id"])
        line.insert(0, doc)
        doc = docs.get(doc.get("replaces", ""))
    versions = [(doc, version) for doc in line for version in doc.get("versions", [])][:-1]  # 마지막 것이 지금의 판이다
    found, tags = [], set()
    for doc, version in versions:
        path = version.get("text", "")
        if not path or path == act.get("path") or not pathlib.Path(path).is_file():
            continue
        tag = str(version.get("date", "")).replace("-", "")
        while tag in tags:   # 같은 날에 판이 둘이면 뒤의 것에 표시를 붙인다
            tag += "b"
        tags.add(tag)
        found.append({"tag": tag, "date": version.get("date", ""), "label": f"{version.get('date', '')}에 받은 판", "path": path, "url": doc.get("url", "")})
    return found


def chain(act):
    """문서의 앞선 판들을 이른 것부터: [{"tag", "date", "label", "path", "url"}]. 글을 받아 둔 것만 싣는다."""
    return _act_chain(act) if act.get("group", "act") == "act" else _document_chain(act)


def current(act):
    """지금의 판의 이름과 날짜."""
    if act.get("group", "act") == "act":
        day = act.get("consolidated", "")
        return {"tag": "", "date": day, "label": f"{day} 통합본" if day else "지금의 글"}
    day = act.get("received", "")
    return {"tag": "", "date": day, "label": f"{day}에 받은 판" if day else "지금의 판"}


def steps(act, parts):
    """이웃한 두 판의 짝을 새 것부터: [(앞선 판, 뒤의 판, 앞선 판의 조각들, 뒤의 판의 조각들)]. 조각으로 읽히지 않는 판은 건너뛴다."""
    versions = [(version, corpus.read({**act, "path": version["path"]})) for version in chain(act)]
    versions = [(version, found) for version, found in versions if found] + [(current(act), parts)]
    return [(versions[index][0], versions[index + 1][0], versions[index][1], versions[index + 1][1]) for index in range(len(versions) - 1)][::-1]


def history(documents):
    """[(숨은 문서, 조각들)]: 앞선 판에만 있는 문단을 번역과 검수의 차례에 넣으려고 만든 문서. documents는 [(문서, 조각들)]이다."""
    found = []
    for act, parts in documents:
        if not parts or act.get("hidden"):
            continue
        for before, _, old_parts, new_parts in steps(act, parts):
            changed, _ = compare.rows(old_parts, new_parts)
            wanted = {(row["old"]["part"], row["old"]["at"]) for row in changed if row["old"]}
            kept = []
            for part in old_parts:
                blocks = [text for index, text in enumerate(part["blocks"]) if (part["id"], index) in wanted]
                title = part["title"] if (part["id"], -1) in wanted else ""
                if blocks or title:
                    kept.append({"id": part["id"], "kind": part["kind"], "label": part["label"], "title": title, "level": part.get("level", 0), "blocks": blocks})
            if kept:
                found.append(({"id": f"{act['id']}{MARK}{before['tag']}", "celex": act.get("celex", ""), "name": f"{act['name']}({before['label']})", "short": act.get("short", act["name"]),
                               "url": before.get("url", ""), "path": before["path"], "consolidated": "", "rule": "", "group": act.get("group", "act"),
                               "format": act.get("format", "act"), "turn": TURN, "hidden": True, "of": act["id"]}, kept))
    return found


def _row(row, memory):
    """달라진 문단 하나의 공개용 자료: 옛 글과 새 글의 [원문, 국문]. 국문이 아직 없으면 빈 글이다."""
    made = {"op": row["op"]}
    for side in ("old", "new"):
        if row[side]:
            made[side] = [row[side]["text"], corpus.korean(row[side]["text"], memory)]
    if row["new"]:
        made["at"] = row["new"]["at"] + 1   # 지금의 글에서 조각 안의 몇 번째 문단인가(이름은 0). 화면이 그 문단으로 가는 링크를 단다
    elif row["old"]["at"] < 0:
        made["at"] = 0
    return made


def _grouped(changed, old_parts, new_parts, memory):
    """달라진 문단을 조각마다 묶는다. 지금의 판에 없는 조각(통째로 빠진 조)은 그 앞에 있던 조각 뒤에 놓는다."""
    new_ids = {part["id"]: part for part in new_parts}
    old_ids = {part["id"]: part for part in old_parts}
    groups, after, last = {}, {}, ""
    for row in changed:
        home = row["new"]["part"] if row["new"] else row["old"]["part"]
        if home not in groups:
            groups[home] = []
            if home not in new_ids:
                after.setdefault(last, []).append(home)
        groups[home].append(_row(row, memory))
        if row["new"]:
            last = row["new"]["part"]
    order = list(after.get("", []))
    for part in new_parts:
        if part["id"] in groups:
            order.append(part["id"])
        order += after.get(part["id"], [])
    found = []
    for part_id in dict.fromkeys(order):
        part = new_ids.get(part_id) or old_ids[part_id]
        found.append({"id": part_id, "kind": part["kind"], "label": part["label"], "ko": corpus.label_ko(part), "title": part["title"],
                      "titleKo": corpus.korean(part["title"], memory) if part["title"] else "", "gone": part_id not in new_ids, "rows": groups[part_id]})
    return found


def public(act, parts, memory):
    """문서 하나의 '달라진 곳'(공개용 자료). 앞선 판이 없거나 달라진 문단이 없으면 None."""
    made = []
    for before, after, old_parts, new_parts in steps(act, parts):
        changed, same = compare.rows(old_parts, new_parts)
        if not changed:
            continue   # 글은 그대로이고 파일만 바뀐 판
        grouped = _grouped(changed, old_parts, new_parts, memory)
        made.append({"from": {"label": before["label"], "date": before["date"], "url": before.get("url", "")}, "to": {"label": after["label"], "date": after["date"]},
                     "stats": {**compare.stats(changed), "same": same, "parts": len(grouped)}, "parts": grouped})
    if not made:
        return None
    return {"id": act["id"], "group": act.get("group", "act"), "name": act["name"], "official": act.get("official", ""), "revisions": made}


def brief(body):
    """목록과 문서의 머리에 싣는 한 줄: 가장 새 대조에서 달라진 문단의 수와 두 판의 이름.

    parts는 조각마다 달라진 문단의 수다({조각 id: 수}. 지금의 판에 있는 조각만). 규정 원문 화면이 조각의 머리에서 그 조각의 달라진 곳으로 잇는 데 쓴다.
    """
    newest = body["revisions"][0]
    return {"rows": sum(newest["stats"][name] for name in ("changed", "added", "removed")), "from": newest["from"]["label"], "to": newest["to"]["label"], "date": newest["to"]["date"],
            "parts": {part["id"]: len(part["rows"]) for part in newest["parts"] if not part["gone"]}}


def write(folder, documents, memory):
    """folder(사이트의 data/laws) 아래 changes/<문서 id>.json을 쓰고 {문서 id: 한 줄}을 돌려준다."""
    found = {}
    for act, parts in documents:
        body = public(act, parts, memory) if parts else None
        if body is None:
            continue
        path = pathlib.Path(folder) / "changes" / f"{act['id']}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(body, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        found[act["id"]] = brief(body)
    return found
