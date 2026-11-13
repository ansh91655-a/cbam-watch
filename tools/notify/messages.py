"""'운영 보고' 이슈에 적는 글을 만든다. 저장소가 공개이므로 보고 파일에 있는 것만 쓴다."""
from tools.common.siteinfo import site_url

SITE = site_url()
CONSOLE_NOTE = "자세한 내용(보류 사유, 실행 기록)은 운영 콘솔에서 봅니다."
SITECHECK_LINES = 8  # 화면 점검의 문제를 이슈에 적는 줄 수


def marker(kind, key):
    """같은 보고를 두 번 적지 않으려고 글 끝에 붙이는 표시."""
    return f"<!-- cbam-watch {kind}:{key} -->"


def _hello(owner):
    return f"@{owner} " if owner else ""


def daily(report, owner):
    problems = list(report.get("problems", []))
    extra = int(report.get("runProblems", 0) or 0)
    holds = report.get("holds", [])
    counts = report.get("counts", {})
    lines = [f"{_hello(owner)}**문제 보고: {report.get('date', '')} CBAM 규제동향 사이트**", ""]
    if problems or extra:
        lines.append(f"- 문제 {len(problems) + extra}건")
        lines += [f"  - {line}" for line in problems]
        if extra:
            lines.append(f"  - 자동 실행이 적어 둔 문제 {extra}건(운영 콘솔의 실행 기록)")
    if holds:
        lines.append(f"- 사람이 봐야 하는 보류 {len(holds)}건")
        lines += [f"  - `{hold.get('id', '')}` ({hold.get('gate', '')})" for hold in holds]
    lines += ["", f"새 게시 {counts.get('published', 0)}건(누적 {counts.get('total', 0)}건). 사이트 {SITE}", CONSOLE_NOTE]
    return "\n".join(lines)


def weekly(report, owner):
    counts = report.get("counts", {})
    lines = [
        f"{_hello(owner)}**주간 요약: {report.get('from', '')} ~ {report.get('to', '')}**",
        "",
        f"- 지난주에 오른 소식 {counts.get('items', 0)}건, 주간 요약 {'실음' if counts.get('digest') else '싣지 않음'}",
        f"- 다시 대조 {counts.get('audited', 0)}건: 일치 {counts.get('match', 0)}, 어긋남 {counts.get('mismatch', 0)}, 확인 불가 {counts.get('unknown', 0)}",
    ]
    withdrawn = report.get("withdrawnIds", [])
    if withdrawn:
        lines.append(f"- 원문과 어긋나 요약을 내린 항목 {len(withdrawn)}건: " + ", ".join(f"`{item}`" for item in withdrawn))
    if report.get("runProblems"):
        lines.append(f"- 주간 작업이 적어 둔 문제 {report['runProblems']}건(운영 콘솔의 실행 기록)")
    lines += [
        f"- 지금까지 오른 소식 {report.get('publishedTotal', 0)}건(요약을 내린 것 {report.get('withdrawnTotal', 0)}건), 자동으로 받지 못하는 문서 링크 {report.get('unreachableDocs', 0)}건",
        "",
        f"사이트 {SITE}",
        "이 글은 문제가 없어도 월요일마다 옵니다. 월요일에 이 글이 오지 않으면 자동 실행이 멈춘 것입니다.",
    ]
    return "\n".join(lines)


def watch(day, health, owner):
    lines = [
        f"{_hello(owner)}**문제 보고: {day} 실행 확인과 보고가 돌지 않았습니다**",
        "",
        f"평일인 오늘 보고 파일(`reports/daily/{day}.json`)이 저장소에 올라오지 않았습니다. "
        "Claude 예약 작업(수집·작성, 검증·게시, 실행 확인과 보고)이 돌았는지 확인이 필요합니다.",
        "",
        "저장소에서 보이는 상태",
        f"- 출처 자동 수집: {'오늘 돎' if health.get('collectToday') else '오늘 돌지 않음'}(마지막 {health.get('collectCheckedAt') or '없음'})",
        f"- 사이트 배포: {'오늘 됨' if health.get('siteDeployedToday') else '오늘 안 됨'}(마지막 {health.get('siteDeployedAt') or '알 수 없음'})",
        f"- 오늘 사이트에 오른 소식 {health.get('listedToday', 0)}건(누적 {health.get('publishedItems', 0)}건)",
    ]
    problems = health.get("problems", [])
    if problems:
        lines.append("- 저장소 쪽 문제")
        lines += [f"  - {line}" for line in problems]
    return "\n".join(lines)


def test(text, owner):
    return "\n".join([
        f"{_hello(owner)}**알림 시험**",
        "",
        str(text or "알림 시험"),
        "",
        "이 글은 알림이 메일로 오는지 확인하려고 보낸 것입니다. 실제 문제가 아닙니다.",
    ])


# 실패했을 때 무엇이 멈추는지: 실행 이름 → 한 줄 설명
FAILED = {
    "도구 검사": "사이트에 실린 내용은 그대로이지만, 고치기 전까지 자동 실행의 도구가 잘못 돌 수 있습니다.",
    "출처 수집과 원문 판 점검": "오늘의 새 소식 후보와 원문 판 점검이 빠졌을 수 있습니다. 다음 수집 때까지 사이트에 새 자료가 실리지 않을 수 있습니다.",
    "사이트 배포": "사이트는 마지막으로 배포된 모습 그대로입니다. 그 뒤에 올라온 소식과 번역은 다음 배포가 될 때까지 보이지 않습니다.",
    "썸네일 만들기": "새 소식의 미리보기 그림이 만들어지지 않았습니다. 소식 자체는 그대로 실립니다.",
}


def workflow_failed(name, sha, url, owner):
    """GitHub 쪽 자동 실행(도구 검사, 수집, 배포, 썸네일)이 실패했을 때의 글."""
    lines = [
        f"{_hello(owner)}**문제 보고: {name}{_particle(name)} 실패했습니다**",
        "",
        f"커밋 `{sha[:7] or '알 수 없음'}`에서 돈 자동 실행 '{name}'{_particle(name, '이', '가')} 실패로 끝났습니다. {FAILED.get(name, '')}".rstrip(),
    ]
    if str(url).startswith("https://"):
        lines += ["", f"실행 기록: {url}"]
    return "\n".join(lines)


def _particle(word, closed="이", open_="가"):
    """받침에 맞는 조사."""
    last = word.rstrip()[-1:]
    if "가" <= last <= "힣":
        return closed if (ord(last) - 0xAC00) % 28 else open_
    return open_


def tests_failed(sha, url, owner):
    """도구 검사가 실패했을 때의 글. 사이트는 마지막으로 배포된 모습 그대로이고, 고치기 전까지 도구가 잘못 돌 수 있다."""
    return workflow_failed("도구 검사", sha, url, owner)


def sitecheck_failed(sha, url, owner, report=None):
    """화면 점검(넘침, 화면 오류, 접근성)이 실패했을 때의 글. 어느 화면이 왜 걸렸는지를 몇 줄 적는다.

    사이트는 이 검사와 상관없이 이미 배포되므로, 걸린 화면이 그대로 보이고 있을 수 있다.
    """
    report = report if isinstance(report, dict) else {}
    failures = [row for row in report.get("failures", []) if isinstance(row, dict)]
    lines = [
        f"{_hello(owner)}**문제 보고: 화면 점검이 실패했습니다**",
        "",
        f"커밋 `{sha[:7] or '알 수 없음'}`의 사이트를 브라우저로 열어 본 검사에서 문제가 나왔습니다. 사이트는 이 검사와 상관없이 배포되므로, 아래 화면이 지금 그대로 보이고 있을 수 있습니다.",
    ]
    if failures:
        lines += ["", f"- 문제 {len(failures)}건"]
        lines += [f"  - {str(row.get('where', ''))[:80]}: {str(row.get('why', ''))[:200]}" for row in failures[:SITECHECK_LINES]]
        if len(failures) > SITECHECK_LINES:
            lines.append(f"  - 이 밖에 {len(failures) - SITECHECK_LINES}건")
    elif report.get("crashed"):
        lines += ["", "- 검사가 끝까지 돌지 못했습니다(검사 도구나 브라우저의 문제일 수 있습니다)."]
    else:
        lines += ["", "- 어느 화면인지는 실행 기록에서 확인해야 합니다(결과 파일을 읽지 못했습니다)."]
    if str(url).startswith("https://"):
        lines += ["", f"실행 기록: {url}"]
    return "\n".join(lines)
