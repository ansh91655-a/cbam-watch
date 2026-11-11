"""CBAM 법령(개정 규정, 이행규정, 위임규정)의 본문을 온전히 받아 둔다. 규제 화면의 분석 글이 조문을 근거로 삼을 수 있게 하려는 것이다.

날마다의 수집(tools/archive/eurlex.py)은 제목과 날짜, 전문의 앞부분, 마지막 조문만 남긴다. 이 단계는 전문과 조문을 모두 남긴다.
부속서는 값의 표가 수천 줄에 이르는 것이 있어(나라별 기본값), 부속서마다 앞부분만 남기고 몇 줄을 뺐는지 적는다.
받는 곳은 EU 출판국 자료 창구이고, EU 법령은 출처를 밝히고 다시 쓸 수 있다.
손으로 돌린다: 워크플로 '소급 수집'에서 mode = crawl, steps = eu-acts.
"""
import re

from tools.archive import fulltext
from tools.archive.store import save_index, save_text

# (CELEX 번호, 무엇인지). 규제 화면(data/regulations.json)의 규제가 근거로 삼는 법령들이다.
ACTS = [
    ("32025R2083", "CBAM 간소화·강화 개정 규정"),
    ("32025R2547", "내재배출량 산정 방법 이행규정"),
    ("32025R2546", "내재배출량 검증 원칙 이행규정"),
    ("32025R2551", "검증기관 인정 조건 위임규정"),
    ("32025R2548", "CBAM 인증서 가격 산정·공개 이행규정"),
    ("32025R2620", "무상할당 조정 이행규정"),
    ("32025R2621", "기본값 이행규정"),
    ("32026R1740", "기본값 이행규정의 정정 규정"),
    ("32025R0486", "승인된 CBAM 신고인 지위 이행규정"),
    ("32025R2549", "승인된 CBAM 신고인 지위 이행규정의 개정·정정 규정"),
    ("32024R3210", "CBAM 등록부 이행규정"),
    ("32025R2550", "CBAM 등록부 이행규정의 개정·정정 규정"),
    ("32025R2619", "세관당국 정보 전달 이행규정"),
    ("32025R2210", "대륙붕·배타적 경제수역 반입 제품 이행규정"),
    ("32023R1773", "전환기간 보고 의무 이행규정"),
    # EU 배출권거래제의 무상할당에 곱하는 교차부문 조정계수(2026~2030년). 무상할당 조정 계산식의 한 항이라 인증서 비용 추정기의 근거로 쓴다.
    ("32026D1862", "교차부문 조정계수 이행결정(2026~2030년)"),
]
ANNEX = re.compile(r"^ANNEX(?: [IVXLC]+)?$")
ANNEX_LINES = 120   # 부속서마다 남기는 줄 수
MUST = "Article 1"  # 받은 글에 꼭 있어야 하는 말(법령의 본문인지 확인)


def trim(lines, keep=ANNEX_LINES):
    """전문과 조문은 그대로 두고, 부속서는 저마다 앞의 keep줄만 남긴다. 뺀 줄 수를 그 자리에 적는다."""
    out, inside, kept, dropped = [], False, 0, 0

    def note():
        if inside and dropped:
            out.append(f"[이 부속서의 나머지 {dropped}줄은 싣지 않음]")

    for line in lines:
        if ANNEX.match(line.strip()):
            note()
            inside, kept, dropped = True, 0, 0
            out.append(line)
        elif not inside or kept < keep:
            out.append(line)
            kept += 1 if inside else 0
        else:
            dropped += 1
    note()
    return out


def crawl():
    entries, failures = [], []
    for celex, what in ACTS:
        try:
            parts, why = fulltext.celex_parts(celex)
        except Exception as problem:
            parts, why = [], f"{type(problem).__name__}: {problem}"[:160]
        lines = [line for _, _, part in parts for line in part]
        if not why and not any(MUST in line for line in lines):
            why = f"받은 글에 '{MUST}'이 없음(법령 본문이 아닐 수 있음)"
        if why:
            failures.append(f"{celex}: {why}")
            continue
        kept = trim(lines)
        address = f"https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:{celex}"
        path = save_text(f"eu-acts/{celex}.txt", [f"[주소] {address}", f"[받은 곳] {parts[0][1]}", f"[무엇] {what}", ""] + kept)
        entries.append({"celex": celex, "title": what, "url": address, "lines": len(kept), "fullLines": len(lines), "textPath": path})
    save_index("eu-acts", entries, {"targets": len(ACTS), "failures": failures})
    return {"stored": len(entries), "failures": failures}
