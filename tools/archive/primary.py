"""EU 조약의 조문과 입법 절차를 정한 문서의 글을 받아 둔다. 사이트의 '입법 절차' 화면이 기관의 역할과 절차를 설명할 때 근거로 쓴다.

- EU 조약(TEU)과 EU 기능조약(TFEU)의 조문: 2016년 통합본. 조문마다 문서 하나다(번호 12016M013은 EU 조약 제13조, 12016E294는 EU 기능조약 제294조).
- 집행위원회의 이행 권한 행사를 회원국이 통제하는 규칙을 정한 규정 (EU) No 182/2011.
- 더 나은 법 제정에 관한 기관 간 합의(2016년): 위임규정과 이행규정을 준비할 때의 협의, 기관 간 협상의 원칙.
- EEA 협정: 길어서 기관과 결정 절차를 다룬 제7부만 남긴다(다른 법령을 협정에 넣는 EEA 공동위원회 결정이 어떻게 발효하는지).
받는 곳은 EU 출판국 자료 창구이고, EU 법령은 출처를 밝히고 다시 쓸 수 있다.
손으로 돌린다: 워크플로 '소급 수집'에서 mode = crawl, steps = eu-primary. 조약은 거의 바뀌지 않으므로 평소의 수집은 이 단계를 돌리지 않는다.
"""
import urllib.parse

from tools.archive import fulltext
from tools.archive.store import save_index, save_text

EURLEX = "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:{celex}"
# (이름, CELEX 번호, 무엇인지, 받은 글에 꼭 있어야 하는 말)
TARGETS = [
    ("teu-13", "12016M013", "EU 조약 제13조(기관의 틀)", "institutional framework"),
    ("teu-14", "12016M014", "EU 조약 제14조(유럽의회)", "European Parliament"),
    ("teu-15", "12016M015", "EU 조약 제15조(유럽이사회)", "European Council"),
    ("teu-16", "12016M016", "EU 조약 제16조(이사회)", "qualified majority"),
    ("teu-17", "12016M017", "EU 조약 제17조(집행위원회)", "Commission"),
    ("teu-19", "12016M019", "EU 조약 제19조(EU 사법재판소)", "Court of Justice"),
    ("tfeu-192", "12016E192", "EU 기능조약 제192조(환경 정책의 입법 절차)", "ordinary legislative procedure"),
    ("tfeu-218", "12016E218", "EU 기능조약 제218조(국제 협정)", "negotiations"),
    ("tfeu-238", "12016E238", "EU 기능조약 제238조(이사회의 표결)", "qualified majority"),
    ("tfeu-263", "12016E263", "EU 기능조약 제263조(취소 소송)", "legality"),
    ("tfeu-287", "12016E287", "EU 기능조약 제287조(유럽감사원)", "Court of Auditors"),
    ("tfeu-288", "12016E288", "EU 기능조약 제288조(법령의 종류)", "directive"),
    ("tfeu-289", "12016E289", "EU 기능조약 제289조(입법 절차)", "ordinary legislative procedure"),
    ("tfeu-290", "12016E290", "EU 기능조약 제290조(위임규정)", "delegated"),
    ("tfeu-291", "12016E291", "EU 기능조약 제291조(이행규정)", "implementing"),
    ("tfeu-294", "12016E294", "EU 기능조약 제294조(통상입법절차)", "first reading"),
    ("tfeu-297", "12016E297", "EU 기능조약 제297조(서명, 게재, 발효)", "Official Journal"),
    ("tfeu-304", "12016E304", "EU 기능조약 제304조(유럽경제사회위원회의 자문)", "Economic and Social Committee"),
    ("tfeu-311", "12016E311", "EU 기능조약 제311조(자체 재원)", "own resources"),
    ("tfeu-322", "12016E322", "EU 기능조약 제322조(재정 규칙)", "Court of Auditors"),
    ("comitology", "32011R0182", "규정 (EU) No 182/2011(이행 권한 행사의 통제)", "examination procedure"),
    ("better-law-making", "32016Q0512(01)", "더 나은 법 제정에 관한 기관 간 합의(2016년)", "delegated acts"),
    ("eea-agreement", "21994A0103(01)", "EEA 협정 제7부(기관과 결정 절차)", "EEA Joint Committee"),
]
# 긴 문서에서 남길 곳: 이름 → (이 줄부터, 이 줄 앞까지). 줄의 앞뒤 빈칸을 떼고 견준다.
PART = {"eea-agreement": ("PART VII", "PART VIII")}
LINE_LIMIT = 6000   # 남길 곳을 찾지 못한 긴 문서는 이만큼만 둔다


def cut(lines, start, end):
    """start로 시작하는 첫 줄부터 그 뒤에 end와 같은 첫 줄 앞까지. 찾지 못하면 빈 목록."""
    first = next((index for index, line in enumerate(lines) if line.strip() == start), None)
    if first is None:
        return []
    last = next((index for index in range(first + 1, len(lines)) if lines[index].strip() == end), len(lines))
    return lines[first:last]


def read(celex):
    """[줄]과 받은 주소, 사유. 번호에 괄호나 빗금이 있으면 풀어 쓴 주소로도 묻는다. 파일이 여럿이면 차례대로 이어 붙인다."""
    codes = [celex] + ([urllib.parse.quote(celex, safe="")] if not celex.isalnum() else [])
    why = ""
    for code in codes:
        parts, why = fulltext.celex_parts(code)
        if parts:
            return [line for _, _, lines in parts for line in lines], parts[0][1], ""
    return [], "", why or "받지 못함"


def crawl():
    entries, failures = [], []
    for name, celex, what, must in TARGETS:
        try:
            lines, address, why = read(celex)
        except Exception as problem:
            lines, address, why = [], "", f"{type(problem).__name__}: {problem}"[:160]
        if not why and not any(must in line for line in lines):
            why = f"받은 글에 '{must}'가 없음(다른 문서일 수 있음)"
        if why:
            failures.append(f"{name} {celex}: {why}")
            continue
        note = []
        if name in PART:
            kept = cut(lines, *PART[name])
            if kept:
                note = [f"[남긴 곳] {PART[name][0]}부터 {PART[name][1]} 앞까지 {len(kept)}줄(문서 전체 {len(lines)}줄)"]
                lines = kept
            elif len(lines) > LINE_LIMIT:
                note = [f"[남긴 곳] 앞의 {LINE_LIMIT}줄(문서 전체 {len(lines)}줄. 남길 곳 {PART[name][0]}을 찾지 못함)"]
                lines = lines[:LINE_LIMIT]
        path = save_text(f"eu-primary/{name}.txt", [f"[문서] {what}", f"[주소] {address}", f"[원문] {EURLEX.format(celex=celex)}"] + note + [""] + lines)
        entries.append({"name": name, "celex": celex, "title": what, "url": EURLEX.format(celex=celex), "lines": len(lines), "textPath": path})
    save_index("eu-primary", entries, {"targets": len(TARGETS), "failures": failures})
    return {"stored": len(entries), "failures": failures}
