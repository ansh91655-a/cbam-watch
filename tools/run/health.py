"""저장소 쪽의 상태를 모아 한 줄 JSON으로 출력한다. 실행 확인과 보고에 쓴다.

쓰는 법: python -m tools.run.health
출력의 problems는 사람에게 알릴 문제의 목록이다(규칙은 이 파일에 있다). 나머지 값은 근거가 되는 수치다.
"""
import datetime
import json
import subprocess
import sys

from tools.common.jsonio import KST, now_kst, read_json, today

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


def _source_problems(status, claude):
    problems = []
    for code, row in sorted(status.get("sources", {}).items()):
        if int(row.get("failCount", 0) or 0) >= FAIL_LIMIT:
            problems.append(f"출처 {code}: {row['failCount']}회 연속 읽지 못함({str(row.get('note', ''))[:60]})")
        if "구조가 바뀐" in str(row.get("note", "")):
            problems.append(f"출처 {code}: 화면 구조가 바뀐 것으로 보임")
    for code, row in sorted(claude.get("sources", {}).items()):
        if row.get("ok") is False and int(row.get("failCount", 0) or 0) >= FAIL_LIMIT:
            problems.append(f"출처 {code}: 직접 열람이 {row['failCount']}회 연속 실패")
    return problems


def _originals_problems(originals, day):
    problems = []
    if originals and not str(originals.get("checkedAt", "")).startswith(day):
        problems.append(f"원문 문서 점검이 오늘 돌지 않음(마지막 {originals.get('checkedAt', '없음')})")
    for note in originals.get("notes", []):
        if "화면을 읽지 못함" in note or "그만 받음" in note or "문서 링크를 하나도" in note:
            problems.append(f"원문 문서: {note}")
    return problems


def main():
    day = today()
    workday = now_kst().weekday() < 5
    status = read_json("collected/status.json", {"sources": {}})
    claude = read_json("collected/claude-status.json", {"sources": {}})
    originals = read_json("originals/state.json", {})
    items = read_json("data/items.json", {"items": []})["items"]
    _git("fetch", "--depth", "1", "origin", "gh-pages")
    deployed = _git("log", "-1", "--format=%cI", "FETCH_HEAD")
    collect_today = str(status.get("checkedAt", "")).startswith(day)
    deployed_today = _kst_date(deployed) == day

    problems = []
    if workday and not collect_today:
        problems.append(f"출처 자동 수집이 오늘 돌지 않음(마지막 {status.get('checkedAt', '없음')})")
    problems += _source_problems(status, claude)
    if workday:
        problems += _originals_problems(originals, day)
        if not deployed_today:
            problems.append(f"사이트가 오늘 다시 배포되지 않음(마지막 {deployed or '알 수 없음'})")

    report = {
        "today": day,
        "problems": problems,
        "collectCheckedAt": status.get("checkedAt", ""),
        "collectToday": collect_today,
        "sourcesChecked": len(status.get("sources", {})),
        "originalsCheckedAt": originals.get("checkedAt", ""),
        "originalsDocs": len(originals.get("docs", {})),
        "originalsPending": len(originals.get("pending", {})),
        "originalsUnreachable": int(originals.get("unreachableCount", 0) or 0),
        "siteDeployedAt": deployed,
        "siteDeployedToday": deployed_today,
        "publishedItems": len(items),
        "listedToday": sum(1 for item in items if item.get("listed") == day),
        "withdrawn": sum(1 for item in items if item.get("withdrawn")),
    }
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
