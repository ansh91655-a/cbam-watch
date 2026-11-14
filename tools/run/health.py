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
from tools.run import articles_health, cn_health, laws_health, reference_health, rules_health

FAIL_LIMIT = 3  # 출처를 이만큼 이어서 읽지 못하면 문제로 본다


LAG_HOURS = 3   # 사이트에 실릴 것이 main에 올라간 뒤 이만큼 지나도록 배포가 없으면 문제로 본다
SITE_PATHS = ["site", "data", "stamps", ":(exclude)data/laws-ko"]  # 바뀌면 사이트를 다시 싣는 곳(.github/workflows/pages.yml)


def _run(*args, limit=60):
    """git을 돌려 (됐는가, 출력)을 돌려준다."""
    try:
        done = subprocess.run(["git", *args], capture_output=True, timeout=limit)
        return done.returncode == 0, done.stdout.decode("utf-8", "replace").strip()
    except Exception:
        return False, ""


def _git(*args):
    return _run(*args)[1]


def _deployed():
    """배포 가지의 모습: (읽었는가, 마지막 배포 시각, 국문 PDF 목록 또는 None).

    배포 가지에는 문서 사본과 PDF가 150MB쯤 들어 있다. 시각과 작은 목록만 보면 되므로 큰 파일은 받지 않는다.
    받지 못하면 읽지 못한 것으로 돌려준다(앞서 다른 것을 받으며 남은 FETCH_HEAD를 배포로 잘못 읽지 않는다).
    """
    ok, _ = _run("fetch", "--depth", "1", "--filter=blob:limit=200k", deploy_remote(), "gh-pages", limit=180)
    if not ok:
        return False, "", None
    try:
        listing = json.loads(_git("show", "FETCH_HEAD:data/laws/pdf.json"))
    except ValueError:
        listing = None
    return True, _git("log", "-1", "--format=%cI", "FETCH_HEAD"), listing


def _pdf_problems(listing):
    """국문 PDF 나란히 보기가 빠졌거나 지난 것으로 남은 문서."""
    if not isinstance(listing, dict) or "wanted" not in listing:
        return []  # 목록에 실을 수를 적기 전의 배포
    problems = []
    shown, wanted, kept = len(listing.get("docs", {})), int(listing.get("wanted", 0)), listing.get("kept", []) or []
    if shown < wanted:
        problems.append(f"국문 PDF 나란히 보기: 문서 {wanted}건 가운데 {shown}건만 실림(빠진 {wanted - shown}건은 화면에서 PDF 보기가 나오지 않음)")
    if kept:
        problems.append(f"국문 PDF {len(kept)}건을 이번 배포에서 만들지 못해 지난 배포의 것을 그대로 실음({', '.join(kept)[:120]}). "
                        + ("배포 실행의 도구 설치가 실패함" if listing.get("tools") is False else "만들다가 오류가 남"))
    return problems


def _lag_problem(deployed):
    """사이트에 실릴 것이 올라간 지 오래인데 배포가 그보다 앞서 있으면 알린다. 기록이 얕아 알 수 없으면 넘어간다."""
    changed = _git("log", "-1", "--format=%cI", "--", *SITE_PATHS)
    try:
        last, live = datetime.datetime.fromisoformat(changed), datetime.datetime.fromisoformat(deployed)
    except ValueError:
        return []
    waited = (now_kst() - last).total_seconds() / 3600
    if live < last and waited >= LAG_HOURS:
        return [f"사이트 배포가 밀림: 실릴 것이 {last.astimezone(KST):%m-%d %H:%M}에 올라갔으나 마지막 배포는 {live.astimezone(KST):%m-%d %H:%M}임({waited:.0f}시간째)"]
    return []


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
    reached, deployed, pdf_listing = _deployed()  # 사이트만 싣는 저장소를 따로 두면 그 저장소의 배포 가지를 본다
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
    if not reached:
        problems.append("배포 가지를 읽지 못해 사이트가 제대로 실렸는지 확인하지 못함(잠시 뒤 다시 확인해야 함)")
    else:
        problems += _pdf_problems(pdf_listing) + _lag_problem(deployed)
    if workday:
        problems += _originals_problems(originals, day)
        if reached and not deployed_today:
            problems.append(f"사이트가 오늘 다시 배포되지 않음(마지막 {deployed or '알 수 없음'})")

    rule_problems, rule_counts = rules_health.problems(day, workday)
    problems += rule_problems
    problems += cn_health.problems()
    problems += reference_health.problems()
    problems += articles_health.problems()
    problems += laws_health.problems(day)

    return {
        "today": day,
        "problems": problems,
        # 해설서의 절이 가리킨 규제가 달라져 그 절을 다시 봐야 하는 것(문제가 아니다. 주간 작업이 다시 보고 기록을 고친다)
        "handbookToReview": reference_health.handbook_rule_lines(),
        **rule_counts,
        "collectCheckedAt": status.get("checkedAt", ""),
        "collectToday": collect_today,
        "sourcesChecked": len(status.get("sources", {})),
        "originalsCheckedAt": originals.get("checkedAt", ""),
        "originalsDocs": len(originals.get("docs", {})),
        "originalsPending": len(originals.get("pending", {})),
        "originalsUnreachable": int(originals.get("unreachableCount", 0) or 0),
        "originalsUnreachableNames": [str(name) for name in originals.get("unreachableNames", [])][:30],
        "siteDeployedAt": deployed,
        "siteDeployedToday": deployed_today,
        "sitePdfDocs": len((pdf_listing or {}).get("docs", {})) if reached else None,
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
