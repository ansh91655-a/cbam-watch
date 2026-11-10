"""품목 코드 조회 자료(data/cn.json)와 기관별 입장 비교표가 낡지 않았는지 본다. 실행 확인과 보고(tools.run.health)가 불러 쓴다.

두 자료는 손으로 다시 만들어야 하는 것이라, 다시 만들 때가 되면 문제로 알린다.
- CBAM 규정의 새 통합본이 법령 데이터베이스 기록에 보이면: 부속서 I이 바뀌었을 수 있다.
- 하류제품 확대 개정안이 채택 단계에 들어가면: '개정안'과 '이사회 안' 안내, 기관별 입장 비교표가 지난 이야기가 된다.
"""
from tools.common.jsonio import read_json

CN = "data/cn.json"
RELATED = "collected/archive/eur-lex-related.json"
RULES = "data/regulations.json"
PROPOSAL_RULE = "cbam-downstream"
ADOPTED = "채택"  # 단계 이름에 이 말이 들면 채택 단계다


def newer_consolidated(used, entries):
    """쓰고 있는 통합본(예: 02023R0956-20251020)보다 새 통합본의 번호를 돌려준다. 없으면 빈 글."""
    base = used.split("-")[0]
    if not base or "-" not in used:
        return ""
    later = sorted(str(row.get("celex", "")) for row in entries if str(row.get("celex", "")).startswith(base + "-") and str(row.get("celex", "")) > used)
    return later[-1] if later else ""


def adopted(rule):
    """그 규제가 채택 단계나 그 뒤에 와 있는가."""
    path = [str(name) for name in rule.get("path", [])]
    first = next((index for index, name in enumerate(path) if ADOPTED in name), None)
    return first is not None and int(rule.get("at", 0) or 0) >= first


def problems(cn=None, entries=None, rules=None):
    cn = read_json(CN, {}) if cn is None else cn
    entries = read_json(RELATED, {}).get("entries", []) if entries is None else entries
    rules = (read_json(RULES, {}) or {}).get("regulations", []) if rules is None else rules
    found = []
    if not cn:
        return ["품목 코드 조회 자료(data/cn.json)를 읽지 못함"]
    newer = newer_consolidated(str((cn.get("law") or {}).get("celex", "")), entries)
    if newer:
        found.append(f"품목 코드 조회: CBAM 규정의 새 통합본({newer})이 나와 목록을 다시 만들어야 함")
    rule = next((row for row in rules if row.get("id") == PROPOSAL_RULE), None)
    if rule and adopted(rule):
        if cn.get("proposed") or cn.get("council"):
            found.append("품목 코드 조회: 하류제품 확대 개정안이 채택 단계에 들어가 '개정안' 안내를 손봐야 함")
        if rule.get("positions"):
            found.append("기관별 입장 비교표: 하류제품 확대 개정안이 채택 단계에 들어가 표를 손봐야 함")
    return found
