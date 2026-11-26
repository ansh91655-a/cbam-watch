"""관보에 실리기 전의 법령 글을 받아 둔다: EU 집행위원회가 채택했으나 아직 관보에 실리지 않은 위임규정, 의견수렴 중인 초안.

이런 문서에는 CELEX 번호가 없어 법령 본문 단계(tools/archive/acts.py)가 받지 못한다. EU 출판국 자료 창구는 집행위원회 문서 번호(pi_com)로 같은 글을 내준다.
(EUR-Lex의 문서 번호 주소는 자동 실행에 확인 요청 화면(202)을 내므로 쓰지 않는다. 2026-11-26에 확인.)
받은 글은 규제 화면의 분석 글과 해설서가 조문을 근거로 삼는 데 쓰고, 규정 원문 화면에도 '관보 게재 전'임을 밝혀 싣는다.
법령이 관보에 실려 CELEX 번호가 붙으면 여기의 대상에서 빼고 acts.ACTS에 올린다(절차서 20의 '준비 중이던 법령이 나온 날').
손으로 돌린다: 워크플로 '소급 수집'에서 mode = crawl, steps = eu-pending. EU 기관의 문서는 출처를 밝히고 다시 쓸 수 있다.
"""
import urllib.parse

from tools.archive import fulltext
from tools.archive.store import save_index, save_text
from tools.common.htmltext import parse

RESOURCE = "http://publications.europa.eu/resource/pi_com/{code}"   # 번호의 괄호는 %28, %29로 적어야 찾는다
PAGE = "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=PI_COM:{number}"
MUST = "Article 1"  # 받은 글에 꼭 있어야 하는 말(법령의 본문인지 확인)
# name: 파일 이름, number: 집행위원회 문서 번호(EUR-Lex와 자료 창구가 함께 쓴다), reference: 문서에 적힌 번호,
# state: adopted(채택, 관보 게재 전) 또는 draft(의견수렴 중인 초안), rule: 규제 자료(data/regulations.json)의 규제 id, dated: 문서의 날짜(채택일이나 초안 공개일)
TARGETS = [
    {"name": "sale-repurchase-adopted", "number": "C(2026)8367", "reference": "C(2026) 8367 final", "state": "adopted",
     "what": "CBAM 인증서 판매·환매 위임규정(채택본)", "rule": "dr-sale-repurchase", "dated": "2026-11-25"},
    {"name": "declarations-draft", "number": "Ares(2026)10806938", "reference": "Ares(2026)10806938", "state": "draft",
     "what": "CBAM 신고서 이행규정(안)", "rule": "ir-declarations", "dated": "2026-11-19"},
]


def address_of(number):
    return RESOURCE.format(code=urllib.parse.quote(number, safe=""))


def read(number):
    """(받은 주소, 줄 목록)과 사유. 파일이 여럿이면(본문과 부속서) 차례대로 이어 붙인다."""
    pages, why = fulltext.resource_pages(address_of(number))
    if why:
        return address_of(number), [], why
    return pages[0][1], [line for _, address, html in pages for line in parse(html, address)[1]], ""


def head(target, fetched):
    """받아 둔 글의 머리. 어디서 받았고 어떤 상태의 문서인지 적는다."""
    state = {"adopted": "EU 집행위원회가 채택함. 관보에 실리기 전의 글", "draft": "의견수렴 중인 초안"}[target["state"]]
    return [f"[주소] {PAGE.format(number=target['number'])}", f"[받은 곳] {fetched}", f"[무엇] {target['what']}",
            f"[문서 번호] {target['reference']}", f"[상태] {state}", f"[문서의 날짜] {target['dated']}", ""]


def crawl():
    entries, failures = [], []
    for target in TARGETS:
        try:
            fetched, lines, why = read(target["number"])
        except Exception as problem:
            fetched, lines, why = "", [], f"{type(problem).__name__}: {problem}"[:160]
        if not why and not any(MUST in line for line in lines):
            why = f"받은 글에 '{MUST}'이 없음(법령 본문이 아닐 수 있음)"
        if why:
            failures.append(f"{target['name']} {target['number']}: {why}")
            continue
        path = save_text(f"eu-pending/{target['name']}.txt", head(target, fetched) + lines)
        entries.append({"name": target["name"], "number": target["number"], "reference": target["reference"], "state": target["state"], "title": target["what"],
                        "rule": target["rule"], "date": target["dated"], "url": PAGE.format(number=target["number"]), "lines": len(lines), "textPath": path})
    save_index("eu-pending", entries, {"targets": len(TARGETS), "failures": failures})
    return {"stored": len(entries), "failures": failures}
