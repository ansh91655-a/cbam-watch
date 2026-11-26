"""관보에 실리기 전의 법령 글을 받아 둔다: EU 집행위원회가 채택했으나 아직 관보에 실리지 않은 위임규정, 의견수렴 중인 초안.

이런 문서에는 CELEX 번호가 없어 법령 본문 단계(tools/archive/acts.py)가 받지 못한다. EUR-Lex는 집행위원회 문서 번호(PI_COM:…)로 같은 글을 싣고 있다.
받은 글은 규제 화면의 분석 글과 해설서가 조문을 근거로 삼는 데 쓰고, 규정 원문 화면에도 '관보 게재 전'임을 밝혀 싣는다.
법령이 관보에 실려 CELEX 번호가 붙으면 여기의 대상에서 빼고 acts.ACTS에 올린다(절차서 20의 '준비 중이던 법령이 나온 날').
손으로 돌린다: 워크플로 '소급 수집'에서 mode = crawl, steps = eu-pending. EU 기관의 문서는 출처를 밝히고 다시 쓸 수 있다.
"""
from tools.archive import fulltext
from tools.archive.store import save_index, save_text
from tools.common.net import fetch

HTML = "https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri={uri}"
PAGE = "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri={uri}"
MUST = "Article 1"  # 받은 글에 꼭 있어야 하는 말(법령의 본문인지 확인)
# name: 파일 이름, uri: EUR-Lex의 문서 번호, reference: 문서에 적힌 번호, state: adopted(채택, 관보 게재 전) 또는 draft(의견수렴 중인 초안),
# rule: 규제 자료(data/regulations.json)의 규제 id, dated: 문서의 날짜(채택일이나 초안 공개일)
TARGETS = [
    {"name": "sale-repurchase-adopted", "uri": "PI_COM:C(2026)8367", "reference": "C(2026) 8367 final", "state": "adopted",
     "what": "CBAM 인증서 판매·환매 위임규정(채택본)", "rule": "dr-sale-repurchase", "dated": "2026-11-25"},
    {"name": "declarations-draft", "uri": "PI_COM:Ares(2026)10806938", "reference": "Ares(2026)10806938", "state": "draft",
     "what": "CBAM 신고서 이행규정(안)", "rule": "ir-declarations", "dated": "2026-11-19"},
]


def read(uri):
    """(받은 주소, 줄 목록)과 사유. EUR-Lex의 HTML 글을 줄로 편다."""
    address = HTML.format(uri=uri)
    status, headers, body, error = fetch(address, timeout=180, retries=1)
    if status != 200 or not body:
        return address, [], f"응답 {status} {error[:60]}".strip()
    return address, fulltext._lines(body, headers, address), ""


def head(target, fetched):
    """받아 둔 글의 머리. 어디서 받았고 어떤 상태의 문서인지 적는다."""
    state = {"adopted": "EU 집행위원회가 채택함. 관보에 실리기 전의 글", "draft": "의견수렴 중인 초안"}[target["state"]]
    return [f"[주소] {PAGE.format(uri=target['uri'])}", f"[받은 곳] {fetched}", f"[무엇] {target['what']}",
            f"[문서 번호] {target['reference']}", f"[상태] {state}", f"[문서의 날짜] {target['dated']}", ""]


def crawl():
    entries, failures = [], []
    for target in TARGETS:
        try:
            fetched, lines, why = read(target["uri"])
        except Exception as problem:
            fetched, lines, why = "", [], f"{type(problem).__name__}: {problem}"[:160]
        if not why and not any(MUST in line for line in lines):
            why = f"받은 글에 '{MUST}'이 없음(법령 본문이 아닐 수 있음)"
        if why:
            failures.append(f"{target['name']} {target['uri']}: {why}")
            continue
        path = save_text(f"eu-pending/{target['name']}.txt", head(target, fetched) + lines)
        entries.append({"name": target["name"], "uri": target["uri"], "reference": target["reference"], "state": target["state"], "title": target["what"],
                        "rule": target["rule"], "date": target["dated"], "url": PAGE.format(uri=target["uri"]), "lines": len(lines), "textPath": path})
    save_index("eu-pending", entries, {"targets": len(TARGETS), "failures": failures})
    return {"stored": len(entries), "failures": failures}
