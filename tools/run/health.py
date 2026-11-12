"""저장소 쪽의 상태를 모아 한 줄 JSON으로 출력한다. 실행 확인과 보고에 쓴다.

쓰는 법: python -m tools.run.health
출력의 problems는 사람에게 알릴 문제의 목록이다(규칙은 이 파일에 있다). 나머지 값은 근거가 되는 수치다.
"""
import datetime
import json
import subprocess
import sys
import urllib.parse

from tools.common import robots
from tools.common.jsonio import KST, now_kst, read_json, today
from tools.common.siteinfo import deploy_remote
from tools.run import cn_health, reference_health, rules_health

FAIL_LIMIT = 3  # 출처를 이만큼 이어서 읽지 못하면 문제로 본다


def _git(*args):
    try:
        done = subprocess.run(["git", *args], capture_output=True, timeout=60)
        return done.stdout.decode("utf-8", "replace").strip()
    except Exception:
        return ""


def _kst_date(iso_text):
    """ISO 시각을 한국 날짜로 바꾼다. 읽지 못하면 빈 글."""
    try:
        return datetime.datetime.fromisoformat(iso_text).astimezone(KST).date().isoformat()
    except Exception:
        return ""


def _source_problems(status, claude, active=None):
    """출처를 읽지 못한 문제. active는 지금 예약 실행이 직접 여는 출처의 code들이다(주면 그 밖의 옛 기록은 보지 않는다)."""
    problems = []
    for code, row in sorted(status.get("sources", {}).items()):
        if int(row.get("failCount", 0) or 0) >= FAIL_LIMIT:
            problems.append(f"출처 {code}: {row['failCount']}회 연속 읽지 못함({str(row.get('note', ''))[:60]})")
        if "구조가 바뀐" in str(row.get("note", "")):
            problems.append(f"출처 {code}: 화면 구조가 바뀐 것으로 보임")
    # 예약 실행이 직접 여는 출처. 사이트 쪽의 사정이나 검색 결과에 주소가 나오지 않아 못 읽은 것은 몇 번 이어질 때 알린다.
    # 웹 읽기 도구가 사람의 확인을 기다리다 끝난 것(승인, PROVENANCE_REQUIRED)은 사람 없이는 열리지 않는 주소를 연 것이라
    # 날마다 되풀이된다. 첫날에 한 줄로 묶어 알린다. 예약 작업의 자동 승인 설정으로는 풀리지 않는다(2026-11-12에 확인).
    unapproved = []
    for code, row in sorted(claude.get("sources", {}).items()):
        if row.get("ok") is not False or (active is not None and code not in active):
            continue
        note = str(row.get("note", ""))
        if "승인" in note or "PROVENANCE" in note:
            unapproved.append(code)
        elif int(row.get("failCount", 0) or 0) >= FAIL_LIMIT:
            problems.append(f"출처 {code}: 직접 열람이 {row['failCount']}회 연속 실패({note[:60]})")
    if unapproved:
        problems.append(f"예약 실행이 웹 읽기 승인을 받지 못해 출처 {len(unapproved)}곳을 열지 못함({', '.join(unapproved)}). "
                        "사람의 확인이 필요한 주소를 열려고 한 것이므로 절차서의 웹 읽기 규칙을 확인해야 함")
    return problems


def _originals_problems(originals, day):
    problems = []
    if originals and not str(originals.get("checkedAt", "")).startswith(day):
        problems.append(f"원문 문서 점검이 오늘 돌지 않음(마지막 {originals.get('checkedAt', '없음')})")
    for note in originals.get("notes", []):
        if "화면을 읽지 못함" in note or "그만 받음" in note or "문서 링크를 하나도" in note:
            problems.append(f"원문 문서: {note}")
    return problems


def _price_problems(prices):
    rows = prices.get("unparsed", []) or []
    return [f"인증서 가격표에서 읽지 못한 행 {len(rows)}건(표의 꼴이 바뀐 것으로 보임): {str(rows[0])[:80]}"] if rows else []


def _robots_problems(day, blocked=None):
    """그날 robots.txt에 막혀 받지 않은 주소가 있으면 사이트별로 묶어 알린다."""
    blocked = robots.blocked_today(day) if blocked is None else blocked
    if not blocked:
        return []
    hosts = sorted({urllib.parse.urlsplit(url).netloc for url, _ in blocked})
    return [f"robots.txt가 자동 읽기를 막아 받지 않은 주소 {len(blocked)}건({', '.join(hosts)[:140]}). 출처 대장에서 빼거나 받는 방법을 바꿔야 함"]


def report():
    """저장소의 상태를 사전으로 돌려준다. problems가 사람에게 알릴 문제다."""
    day = today()
    workday = now_kst().weekday() < 5
    status = read_json("collected/status.json", {"sources": {}})
    claude = read_json("collected/claude-status.json", {"sources": {}})
    originals = read_json("originals/state.json", {})
    items = read_json("data/items.json", {"items": []})["items"]
    _git("fetch", "--depth", "1", deploy_remote(), "gh-pages")  # 사이트만 싣는 저장소를 따로 두면 그 저장소의 배포 가지를 본다
    deployed = _git("log", "-1", "--format=%cI", "FETCH_HEAD")
    collect_today = str(status.get("checkedAt", "")).startswith(day)
    deployed_today = _kst_date(deployed) == day

    problems = []
    if workday and not collect_today:
        problems.append(f"출처 자동 수집이 오늘 돌지 않음(마지막 {status.get('checkedAt', '없음')})")
    registry = read_json("sources/registry.json", {"sources": []}).get("sources", [])
    problems += _source_problems(status, claude, {source["code"] for source in registry if source.get("collector") == "claude"})
    prices = read_json("data/prices.json", {}) or {}
    problems += _price_problems(prices)
    switched_off = {source.get("url") for source in registry if source.get("collector") == "off"}  # 이미 수집에서 뺀 출처는 다시 알리지 않는다
    problems += _robots_problems(day, [(url, why) for url, why in robots.blocked_today(day) if url not in switched_off])
    if workday:
        problems += _originals_problems(originals, day)
        if not deployed_today:
            problems.append(f"사이트가 오늘 다시 배포되지 않음(마지막 {deployed or '알 수 없음'})")

    rule_problems, rule_counts = rules_health.problems(day, workday)
    problems += rule_problems
    problems += cn_health.problems()
    problems += reference_health.problems()

    return {
        "today": day,
        "problems": problems,
        **rule_counts,
        "collectCheckedAt": status.get("checkedAt", ""),
        "collectToday": collect_today,
        "sourcesChecked": len(status.get("sources", {})),
        "originalsCheckedAt": originals.get("checkedAt", ""),
        "originalsDocs": len(originals.get("docs", {})),
        "originalsPending": len(originals.get("pending", {})),
        "originalsUnreachable": int(originals.get("unreachableCount", 0) or 0),
        "siteDeployedAt": deployed,
        "siteDeployedToday": deployed_today,
        "prices": len(prices.get("prices", [])),
        "publishedItems": len(items),
        # 지난 소식을 한꺼번에 채운 항목(backfill)은 그날의 새 소식으로 세지 않는다
        "listedToday": sum(1 for item in items if item.get("listed") == day and not item.get("backfill")),
        "withdrawn": sum(1 for item in items if item.get("withdrawn")),
    }


def main():
    print(json.dumps(report(), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
