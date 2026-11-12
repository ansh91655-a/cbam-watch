"""번역을 하는 실행마다 무엇을 얼마나 옮기는지 정한 것(sources/translation.json)을 읽는다.

runner는 번역을 하는 실행의 이름이다. 절차서는 이름만 부르고(python -m tools.laws.todo --runner bulk), 무엇을 얼마나 옮길지는 그 파일이 정한다.
그래서 문서의 갈래를 다른 실행으로 옮길 때 절차서와 예약 작업은 그대로 두고 그 파일만 고치면 된다.
"""
from tools.common.jsonio import read_json

SOURCE = "sources/translation.json"
DEFAULT = "daily"
FALLBACK = {"groups": ["act"], "first": [], "limit": 20000, "rounds": 1}
CHECKER = {"limit": 30000, "rounds": 4, "canaries": 0.05, "catch": 0.6, "harsh": 0.3}  # 검수의 기본 설정(파일에 verify가 없을 때)


def runners():
    return (read_json(SOURCE, {}) or {}).get("runners", {})


def runner(name=DEFAULT):
    """실행 하나의 설정: {"groups": 옮기는 갈래들, "first": 먼저 옮기는 문서들, "limit": 한 묶음의 원문 글자 수, "rounds": 한 번의 실행에서 하는 묶음 수}. 모르는 이름이면 KeyError."""
    found = runners()
    if name not in found:
        if name == DEFAULT:
            return dict(FALLBACK)
        raise KeyError(f"번역 실행 이름을 모름: {name}")
    return {**FALLBACK, **found[name]}


def checker():
    """검수(tools.laws.verify)의 설정: {"limit": 한 묶음의 원문 글자 수, "rounds": 한 번의 실행에서 하는 묶음 수, "canaries": 일부러 틀리게 바꿔 섞는 비율,
    "catch": 그 가운데 잡아내야 하는 비율, "harsh": 틀렸다고 한 비율이 이보다 높으면 반영하지 않는 값}"""
    return {**CHECKER, **((read_json(SOURCE, {}) or {}).get("verify") or {})}


def senses():
    """용어집의 핵심 용어가 다른 뜻으로도 쓰일 때 그 뜻의 국문 표기: {영문 낱말(소문자): [국문 표기]}. 검사(tools.laws.check)가 쓴다."""
    found = (read_json(SOURCE, {}) or {}).get("senses") or {}
    return {str(english).lower(): [str(form) for form in forms if str(form).strip()] for english, forms in found.items()}


def everyone():
    """번역을 하는 모든 실행이 맡은 문서를 한 차례로 늘어놓는 설정(검수가 문서를 훑는 차례로 쓴다): first와 groups를 실행의 차례대로 이은 것."""
    first, groups = [], []
    for settings in runners().values():
        first += [act_id for act_id in settings.get("first", []) if act_id not in first]
        groups += [group for group in settings.get("groups", []) if group not in groups]
    return {"first": first, "groups": groups or list(FALLBACK["groups"])}


def ordered(documents, settings):
    """[(문서, 조각들)]을 옮기는 차례대로 돌려준다. settings는 runner()가 준 설정이다.

    first에 적힌 문서가 적힌 차례대로 먼저 오고, 나머지는 groups에 적힌 갈래의 차례, 갈래 안에서는 turn(없으면 목록의 차례)을 따른다.
    first에도 없고 groups의 갈래도 아닌 문서는 뺀다.
    """
    groups, first = list(settings.get("groups", [])), list(settings.get("first", []))
    kept = []
    for index, (act, found) in enumerate(documents):
        group = act.get("group", "act")
        if act["id"] in first:
            kept.append((0, first.index(act["id"]), 0, index, act, found))
        elif group in groups:
            kept.append((1, groups.index(group), act.get("turn", 0), index, act, found))
    return [(act, found) for *_, act, found in sorted(kept, key=lambda row: row[:4])]
