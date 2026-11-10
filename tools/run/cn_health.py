"""품목 코드 조회 자료(data/cn.json)와 기관별 입장 비교표가 낡지 않았는지 본다. 실행 확인과 보고(tools.run.health)가 불러 쓴다.

- CBAM 규정의 새 통합본이 나오면 날마다의 수집이 목록을 스스로 다시 만든다(tools.cn.refresh).
  다시 만들었으면 며칠 동안 그 사실과 바뀐 줄 수를 알리고, 다시 만들지 못했으면 사유를 알린다.
- 하류제품 확대 개정안이 채택 단계에 들어가면 화면이 '협상 전의 기록'이라는 안내를 스스로 붙인다.
  표와 안내의 내용을 최종 법령에 맞게 손보는 일은 사람이 해야 하므로 그때를 알린다.
"""
import datetime

from tools.cn.versions import newer_consolidated
from tools.common.jsonio import KST, now_kst, read_json

CN = "data/cn.json"
RELATED = "collected/archive/eur-lex-related.json"
REFRESH = "collected/cn/refresh.json"
RULES = "data/regulations.json"
PROPOSAL_RULE = "cbam-downstream"
ADOPTED = "채택"  # 단계 이름에 이 말이 들면 채택 단계다
TELL_DAYS = 2    # 목록을 다시 만든 뒤 이만큼의 날 동안 알린다


def _days_since(iso_text, now=None):
    try:
        then = datetime.datetime.fromisoformat(str(iso_text)).astimezone(KST).date()
    except Exception:
        return None
    return ((now or now_kst()).date() - then).days


def adopted(rule):
    """그 규제가 채택 단계나 그 뒤에 와 있는가."""
    path = [str(name) for name in rule.get("path", [])]
    first = next((index for index, name in enumerate(path) if ADOPTED in name), None)
    return first is not None and int(rule.get("at", 0) or 0) >= first


def refresh_notes(refresh, newer, now=None):
    """목록의 자동 갱신 기록에서 알릴 것을 고른다. newer는 지금의 자료보다 새 통합본의 번호(없으면 빈 글)."""
    state, celex = refresh.get("state", ""), refresh.get("celex", "")
    age = _days_since(refresh.get("triedAt", ""), now)
    found = []
    if state == "rebuilt" and age is not None and age <= TELL_DAYS:
        found.append(f"품목 코드 조회: 새 통합본({celex})으로 목록을 스스로 다시 만듦(더해진 줄 {len(refresh.get('added', []))}, 빠진 줄 {len(refresh.get('removed', []))}). "
                     + ("확대 개정안이 통합본에 들어온 것으로 보고 '개정안' 안내를 뺌. " if refresh.get("enacted") else "") + "화면에서 한 번 확인이 필요함")
    if newer and state == "failed" and celex == newer:
        found.append(f"품목 코드 조회: 새 통합본({newer})으로 목록을 다시 만들지 못함: {'; '.join(str(why) for why in refresh.get('problems', []))[:200]}")
    elif newer:
        found.append(f"품목 코드 조회: CBAM 규정의 새 통합본({newer})이 나왔는데 목록의 자동 갱신이 돌지 않음")
    return found


def problems(cn=None, entries=None, rules=None, refresh=None, now=None):
    cn = read_json(CN, {}) if cn is None else cn
    entries = read_json(RELATED, {}).get("entries", []) if entries is None else entries
    rules = (read_json(RULES, {}) or {}).get("regulations", []) if rules is None else rules
    refresh = (read_json(REFRESH, {}) or {}) if refresh is None else refresh
    if not cn:
        return ["품목 코드 조회 자료(data/cn.json)를 읽지 못함"]
    found = refresh_notes(refresh, newer_consolidated(str((cn.get("law") or {}).get("celex", "")), entries), now)
    rule = next((row for row in rules if row.get("id") == PROPOSAL_RULE), None)
    if rule and adopted(rule):
        if cn.get("proposed") or (cn.get("council") or {}).get("added"):
            found.append("품목 코드 조회: 하류제품 확대 개정안이 채택 단계에 들어감. 화면에는 '협상 전의 목록'이라는 안내가 붙었고, 최종 목록은 새 통합본이 나오면 스스로 바뀜")
        if rule.get("positions"):
            found.append("기관별 입장 비교표: 하류제품 확대 개정안이 채택 단계에 들어감. 화면에는 '협상 전의 기록'이라는 안내가 붙었고, 합의된 내용은 표에 손으로 더해야 함")
    return found
