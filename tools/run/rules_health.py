"""규제 진행 상황 자료가 제대로 굴러가는지 본다. 실행 확인과 보고(tools.run.health)가 불러 쓴다.

알리는 것: 자료의 꼴이 깨짐, 큰 단계와 세부 단계가 어긋남, 연혁이나 분석 글의 근거가 공식 기록과 달라짐, 다음 일정이 지났는데 그대로임,
          공식 기록의 변화가 며칠째 자료에 반영되지 않음, 공식 기록 갱신이 오늘 돌지 않음,
          규제가 바뀐 뒤 며칠째 분석 글이 그대로임,
          입법 절차 안내(data/procedures.json)의 꼴이 깨지거나 그 근거가 받아 둔 글과 달라짐.
"""
import datetime

from tools.common.jsonio import KST, read_json
from tools.publish import analysis, procedures, regulations, rule_steps
from tools.run import rules_watch

STALE_DAYS = 3      # 다음 일정이 이만큼 지나도록 그대로면 알린다
PENDING_DAYS = 3    # 공식 기록의 변화가 이만큼 지나도록 반영되지 않으면 알린다
ANALYSIS_DAYS = 3   # 규제가 바뀐 뒤 이만큼 지나도록 분석 글이 그대로면 알린다(그 전에는 사이트가 스스로 밝히기만 한다)
RECORDS = ["ep-oeil", "ec-hys", "eur-lex-related"]


def _days_between(earlier, later):
    try:
        return (datetime.date.fromisoformat(later[:10]) - datetime.date.fromisoformat(earlier[:10])).days
    except Exception:
        return 0


def problems(day, workday):
    body = read_json(regulations.SOURCE, None)
    if body is None:
        return ["규제 자료(data/regulations.json)를 읽지 못함"], {}
    found = []
    shaped = regulations.problems(body, kinds=("format",))
    broken = [row for row in shaped if not row[1].startswith(rule_steps.GAP)]
    if broken:
        found.append(f"규제 자료: 꼴이나 표기 문제 {len(broken)}건({broken[0][0]}: {broken[0][1]})"[:160])
    apart = [row for row in shaped if row[1].startswith(rule_steps.GAP)]   # 큰 단계는 고쳤는데 세부 단계를 고치지 않았거나, 그 반대
    if apart:
        found.append(f"규제 자료: 큰 단계와 세부 단계가 어긋남 {len(apart)}건({apart[0][0]})"[:160])
    drift = regulations.problems(body, kinds=("evidence",))
    if drift:
        found.append(f"규제 자료: 연혁이나 분석의 근거가 공식 기록과 달라짐 {len(drift)}건({drift[0][0]})"[:160])
    behind = [rule for rule in body.get("regulations", []) if analysis.stale(rule)]
    late = [rule for rule in behind if _days_between(str(rule.get("changedOn") or rule["analysis"].get("asOf", "")), day) >= ANALYSIS_DAYS]
    if late:
        found.append(f"규제 분석 {len(late)}건이 규제가 바뀐 뒤 {ANALYSIS_DAYS}일 넘게 그대로임({late[0].get('name', '')})"[:160])
    for rule in body.get("regulations", []):
        date = str(rule.get("nextDate", ""))
        if len(date) == 10 and _days_between(date, day) >= STALE_DAYS:
            found.append(f"규제 '{rule.get('name', '')}': 다음 일정({date})이 지났는데 그대로임")
    seen = read_json(rules_watch.SEEN, None)
    pending = rules_watch.changes(seen.get("seen", {}), rules_watch.snapshot()) if seen else []
    if pending and _days_between(str(seen.get("acceptedAt", "")), day) >= PENDING_DAYS:
        found.append(f"규제 기록의 변화 {len(pending)}건이 {PENDING_DAYS}일 넘게 반영되지 않음({pending[0]['group']}: {pending[0]['key']})"[:160])
    guide = guide_problems()
    found += guide
    stale = []
    for name in RECORDS:
        ran = str(read_json(f"collected/archive/report/{name}.json", {}).get("ranAt", ""))
        try:
            ran_day = datetime.datetime.fromisoformat(ran).astimezone(KST).date().isoformat()
        except Exception:
            ran_day = ""
        if workday and ran_day != day:
            stale.append(name)
    if stale:
        found.append(f"규제 기록 갱신이 오늘 돌지 않음({', '.join(stale)})")
    return found, {"regulations": len(body.get("regulations", [])), "regulationDrift": len(drift), "regulationPending": len(pending),
                   "analyses": sum(1 for rule in body.get("regulations", []) if rule.get("analysis")), "analysesBehind": len(behind),
                   "procedureProblems": len(guide)}


def guide_problems():
    """입법 절차 안내 자료의 문제를 알림 글로. 꼴이 깨진 것과, 근거로 적은 글이 받아 둔 글에서 사라진 것을 따로 알린다."""
    body = read_json(procedures.SOURCE, None)
    if body is None:
        return ["입법 절차 자료(data/procedures.json)를 읽지 못함"]
    seen = procedures.problems(body)
    broken, moved = procedures.blocking(seen), [row for row in seen if row[1].startswith(procedures.DRIFT)]
    found = []
    if broken:
        found.append(f"입법 절차 자료: 꼴이나 표기 문제 {len(broken)}건({broken[0][0]}: {broken[0][1]})"[:160])
    if moved:
        found.append(f"입법 절차 자료: 근거가 받아 둔 글과 달라짐 {len(moved)}건({moved[0][0]})"[:160])
    return found
