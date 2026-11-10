"""CBAM 규정 통합본의 판을 다룬다: 어느 판이 더 새것인지, 판의 번호에서 화면에 적을 이름과 주소를 만든다.

통합본의 번호는 '02023R0956-20251020'처럼 법령 번호 뒤에 기준일(연월일)이 붙는다.
"""
BASE = "02023R0956"  # 규정 (EU) 2023/956의 통합본 번호 앞부분
FIRST = "02023R0956-20251020"  # 이 저장소가 처음에 쓴 판


def newer_consolidated(used, entries):
    """쓰고 있는 통합본(예: 02023R0956-20251020)보다 새 통합본의 번호를 돌려준다. 없으면 빈 글.

    entries는 EU 법령 데이터베이스의 연관 문서 기록(collected/archive/eur-lex-related.json의 entries)이다.
    """
    base = used.split("-")[0]
    if not base or "-" not in used:
        return ""
    later = sorted(str(row.get("celex", "")) for row in entries if str(row.get("celex", "")).startswith(base + "-") and str(row.get("celex", "")) > used)
    return later[-1] if later else ""


def day_of(celex):
    """통합본 번호의 기준일을 '2025-10-20' 꼴로 돌려준다. 읽지 못하면 빈 글."""
    tail = str(celex).split("-")[1] if "-" in str(celex) else ""
    return f"{tail[:4]}-{tail[4:6]}-{tail[6:8]}" if len(tail) == 8 and tail.isdigit() else ""


def law_meta(celex, fetched=""):
    """통합본 번호에서 화면에 적을 이름, 원문 주소를 만든다. fetched는 본문을 받은 주소다."""
    day = day_of(celex)
    when = f"{int(day[:4])}년 {int(day[5:7])}월 {int(day[8:10])}일 통합본" if day else "통합본"
    return {"name": f"규정 (EU) 2023/956 부속서 I·II({when})", "celex": celex,
            "url": f"https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:{celex}", "fetched": fetched}
