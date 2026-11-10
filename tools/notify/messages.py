"""'운영 보고' 이슈에 적는 글을 만든다. 저장소가 공개이므로 보고 파일에 있는 것만 쓴다."""
SITE = "https://ansh91655-a.github.io/cbam-watch/"
CONSOLE_NOTE = "자세한 내용(보류 사유, 실행 기록)은 운영 콘솔에서 봅니다."


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
