"""법령 문단의 국문 번역을 두는 곳(data/laws-ko/<법령 번호>.json)을 읽고 쓴다.

번역은 원문 문단의 글자에서 만든 열쇠(key)에 붙는다. 문단의 자리가 아니라 글자에 붙으므로
- 법령이 고쳐져 통합본이 새로 나와도 글자가 그대로인 문단의 번역은 남고, 바뀐 문단만 번역이 없는 상태가 된다.
- 여러 법령에 똑같이 나오는 문단(맺음말, 표의 머리 글자)은 한 번만 옮기면 모든 곳에 실린다.

파일은 {"act", "updated": 번역이 마지막으로 더해진 날, "blocks": {열쇠: 국문}, "checked": [검수를 마친 열쇠], "held": {열쇠: {"tries", "why"}}} 꼴이다.
checked는 번역한 실행과 다른 실행이 원문과 견줘 본 문단이다(tools.laws.verify). 번역이 바뀐 문단은 checked에서 빠진다.
held는 검사(tools.laws.check)에 걸려 넣지 못한 문단과 걸린 횟수, 마지막 까닭이다(tools.laws.apply가 적는다). 번역이 들어가면 빠진다.
걸린 문단은 번역이 없으므로 줄의 맨 앞에 남아 묶음마다 다시 나온다. 그런 문단이 쌓여 묶음을 채우면 번역이 더 나아가지 못하므로,
HOLD_AFTER번 걸린 문단은 다른 문단을 모두 옮긴 뒤로 돌리고(tools.laws.todo), 그때도 걸려 GIVE_UP번이 되면 더 주지 않는다(사람이 본다).
"""
import hashlib
import pathlib
import re

from tools.common.jsonio import read_json, today, write_json

FOLDER = "data/laws-ko"
HOLD_AFTER = 3  # 한 실행은 한 문단을 세 번까지 넣어 본다(처음과 고쳐서 두 번). 그만큼 걸리면 뒤로 돌린다
GIVE_UP = 6     # 다른 문단을 모두 옮긴 뒤 한 실행이 더 해 보고도 걸린 문단


def key(text):
    """문단의 열쇠. 띄어쓰기의 차이는 같은 문단으로 본다."""
    return hashlib.sha1(re.sub(r"\s+", " ", str(text)).strip().encode("utf-8")).hexdigest()[:12]


def path_of(act_id):
    return f"{FOLDER}/{act_id}.json"


def files():
    """번역 자료의 파일이 있는 문서의 id들(이름의 차례대로)."""
    return [path.stem for path in sorted(pathlib.Path(FOLDER).glob("*.json"))]


def load(act_id):
    """한 법령의 번역: {열쇠: 국문}."""
    return dict((read_json(path_of(act_id), {}) or {}).get("blocks", {}))


def load_all():
    """모든 법령의 번역을 합친 것: {열쇠: 국문}. 같은 글자의 문단은 어느 법령에서 옮겼든 같은 번역을 쓴다."""
    found = {}
    for path in sorted(pathlib.Path(FOLDER).glob("*.json")):
        for block_key, text in ((read_json(path, {}) or {}).get("blocks", {})).items():
            found.setdefault(block_key, text)
    return found


def load_checked(act_id):
    """한 문서의 번역 가운데 검수를 마친 것의 열쇠들(tools.laws.verify가 적는다)."""
    return set((read_json(path_of(act_id), {}) or {}).get("checked", []))


def checked_all():
    """모든 문서에서 검수를 마친 번역의 열쇠들."""
    found = set()
    for path in sorted(pathlib.Path(FOLDER).glob("*.json")):
        found |= set((read_json(path, {}) or {}).get("checked", []))
    return found


def held_all():
    """검사에 걸려 넣지 못한 문단: {열쇠: {"tries": 걸린 횟수, "why": 마지막 까닭}}. 여러 문서에 적혀 있으면 많이 걸린 쪽을 본다."""
    found = {}
    for path in sorted(pathlib.Path(FOLDER).glob("*.json")):
        for block_key, row in ((read_json(path, {}) or {}).get("held", {}) or {}).items():
            if block_key not in found or int(row.get("tries", 0)) > int(found[block_key].get("tries", 0)):
                found[block_key] = {"tries": int(row.get("tries", 0)), "why": str(row.get("why", ""))}
    return found


def hold(act_id, block_key, why):
    """검사에 걸린 문단을 적는다(걸린 횟수를 하나 올리고 까닭을 바꿔 적는다). 번역과 검수 기록, 번역이 더해진 날은 그대로 둔다."""
    current = read_json(path_of(act_id), {}) or {}
    held = dict(current.get("held", {}) or {})
    held[block_key] = {"tries": int((held.get(block_key) or {}).get("tries", 0)) + 1, "why": " ".join(str(why).split())[:200]}
    body = {"act": act_id}
    if current.get("updated"):
        body["updated"] = current["updated"]  # 한 번도 옮기지 않은 문서에는 날을 적지 않는다(번역이 멈췄는지 보는 값이다)
    body["blocks"] = dict(sorted((current.get("blocks", {}) or {}).items()))
    if current.get("checked"):
        body["checked"] = sorted(current["checked"])
    body["held"] = dict(sorted(held.items()))
    write_json(path_of(act_id), body)
    return held[block_key]["tries"]


def save(act_id, blocks, day=None, checked=None):
    """한 법령의 번역을 쓴다. 열쇠 차례로 적어 바뀐 줄만 달라지게 한다.

    검수를 마친 열쇠(checked)는 그대로 둔다. 다만 번역이 바뀌었거나 없어진 문단은 검수하지 않은 것으로 돌린다(다시 견줘 보게).
    checked를 주면 그것을 검수를 마친 열쇠로 적는다(tools.laws.verify가 쓴다).
    """
    current = read_json(path_of(act_id), {}) or {}
    before = current.get("blocks", {})
    marks = set(current.get("checked", [])) if checked is None else set(checked)
    marks = {block_key for block_key in marks if block_key in blocks and before.get(block_key, blocks[block_key]) == blocks[block_key]}
    body = {"act": act_id, "updated": day or today(), "blocks": dict(sorted(blocks.items()))}
    if marks:
        body["checked"] = sorted(marks)
    held = {block_key: row for block_key, row in (current.get("held", {}) or {}).items() if block_key not in blocks}  # 번역이 들어간 문단은 뺀다
    if held:
        body["held"] = dict(sorted(held.items()))
    write_json(path_of(act_id), body)


def mark(act_id, block_keys):
    """한 문서의 번역 가운데 block_keys를 검수를 마친 것으로 적는다. 번역이 더해진 날(updated)은 그대로 둔다(번역이 멈췄는지 보는 데 쓰는 값이다)."""
    current = read_json(path_of(act_id), {}) or {}
    blocks = current.get("blocks", {})
    fresh = {block_key for block_key in block_keys if block_key in blocks}
    if fresh - set(current.get("checked", [])):
        save(act_id, blocks, current.get("updated") or today(), set(current.get("checked", [])) | fresh)
    return len(fresh)
