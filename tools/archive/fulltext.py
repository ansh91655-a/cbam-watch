"""CBAM 규정의 통합본과 하류제품 확대 개정안의 세 기관 문서를 온전히 받아 둔다.

품목 코드 조회(부속서의 품목 목록)와 기관별 입장 비교의 근거로 쓴다. 다른 단계와 달리 글을 줄이지 않고 모두 남긴다.
- EU 출판국 자료 창구: CBAM 규정 통합본, 집행위 제안(본문과 부속서). 한 문서에 파일이 여럿이면 모두 받는다.
- EU 이사회 문서 등록부: 이사회 일반적 접근의 본문(PDF, pypdf가 필요하다).
- 유럽의회: 본회의가 채택한 문서.
"""
import io
import re
import time

from tools.archive.store import save_index, save_text
from tools.common.htmltext import decode, parse, squeeze
from tools.common.net import fetch, header

CELLAR = "http://publications.europa.eu/resource/celex/{celex}"
ACCEPT = {"Accept": "application/xhtml+xml, text/html;q=0.9", "Accept-Language": "eng"}
COUNCIL = "https://data.consilium.europa.eu/doc/document/{code}/en/pdf"
PARLIAMENT = "https://www.europarl.europa.eu/doceo/document/{code}_EN.html"
# (이름, 종류, 번호, 받은 글에 꼭 있어야 하는 말)
TARGETS = [
    ("cbam-consolidated", "celex", "02023R0956-20251020", "ANNEX I"),
    ("downstream-commission", "celex", "52025PC0989", "2023/956"),
    ("downstream-council", "council", "ST-10423-2026-INIT", "2023/956"),
    ("downstream-parliament", "parliament", "TA-10-2026-0276", "2023/956"),
    # 기관 간 협상에 쓰는 대조 문서(집행위 제안, 유럽의회 수정안, 이사회 안을 나란히 실은 것). 이사회 문서 등록부에 공개되어 있다.
    # 유럽의회 누리집은 자동 실행에 문서를 내주지 않아, 유럽의회가 채택한 수정안의 문안은 이 문서에서 확인한다.
    ("downstream-fourcolumn", "council", "WK-14239-2026-INIT", "2025/0419"),
    # 유럽의회 입법 관측소가 절차의 문서마다 붙인 요약(집행위 제안, 위원회 보고서, 본회의 채택 문서)
    ("downstream-oeil-summary", "oeil", "2025/0419(COD)", "CBAM"),
]
OEIL = "https://oeil.europarl.europa.eu/oeil/en/procedure-file?reference={reference}"
OEIL_SUMMARY = "https://oeil.europarl.europa.eu/oeil/en/document-summary?id={number}"
SUMMARY_LINK = re.compile(r"document-summary\?id=(\d+)")
CHOICE = re.compile(r"/resource/cellar/[0-9a-f\-]+\.\d+\.\d+/DOC_(\d+)$")


def _lines(body, headers, address):
    _, lines, _ = parse(decode(body, header(headers, "Content-Type")), address)
    return lines


def celex_parts(celex):
    """[(파일 이름 꼬리, 주소, 줄 목록)]과 사유. 파일이 여럿이면(본문과 부속서) 차례대로 모두 받는다."""
    address = CELLAR.format(celex=celex)
    status, headers, body, error = fetch(address, timeout=240, retries=1, headers=ACCEPT)
    time.sleep(1)
    if status == 200 and body:
        return [("", address, _lines(body, headers, address))], ""
    if status != 300 or not body:
        return [], f"응답 {status} {error[:60]}".strip()
    links, _, _ = parse(decode(body, header(headers, "Content-Type")), address)
    choices = sorted({url for url, _ in links if CHOICE.search(url)}, key=lambda url: int(CHOICE.search(url).group(1)))
    parts = []
    for choice in choices[:8]:
        status, headers, body, error = fetch(choice, timeout=240, retries=1, headers=ACCEPT)
        time.sleep(1)
        if status == 200 and body:
            parts.append((f"-DOC_{CHOICE.search(choice).group(1)}", choice, _lines(body, headers, choice)))
    return parts, "" if parts else "고를 파일을 받지 못함"


def council_parts(code):
    from pypdf import PdfReader  # 워크플로에서 따로 설치한다
    address = COUNCIL.format(code=code)
    status, _, body, error = fetch(address, timeout=180, retries=1)
    if status != 200 or not body.startswith(b"%PDF"):
        return [], f"응답 {status} {error[:60]}".strip()
    lines = []
    for number, page in enumerate(PdfReader(io.BytesIO(body)).pages, start=1):
        lines.append(f"[쪽 {number}]")
        lines += [squeeze(line) for line in (page.extract_text() or "").splitlines() if squeeze(line)]
    return [("", address, lines)], ""


def parliament_parts(code):
    address = PARLIAMENT.format(code=code)
    status, headers, body, error = fetch(address, timeout=180, retries=1)
    if status != 200 or not body:
        return [], f"응답 {status} {error[:60]}".strip()
    return [("", address, _lines(body, headers, address))], ""


def oeil_parts(reference):
    address = OEIL.format(reference=reference)
    status, headers, body, error = fetch(address, timeout=120, retries=1)
    time.sleep(1)
    if status != 200 or not body:
        return [], f"응답 {status} {error[:60]}".strip()
    numbers = list(dict.fromkeys(SUMMARY_LINK.findall(decode(body, header(headers, "Content-Type")))))
    parts = []
    for number in numbers[:10]:
        page = OEIL_SUMMARY.format(number=number)
        status, headers, body, error = fetch(page, timeout=120, retries=1)
        time.sleep(1)
        if status == 200 and body:
            parts.append((f"-{number}", page, _lines(body, headers, page)))
    return parts, "" if parts else "요약 링크를 찾지 못함"


READERS = {"celex": celex_parts, "council": council_parts, "parliament": parliament_parts, "oeil": oeil_parts}


def crawl():
    entries, failures = [], []
    for name, kind, code, must in TARGETS:
        try:
            parts, why = READERS[kind](code)
        except Exception as problem:
            parts, why = [], f"{type(problem).__name__}: {problem}"[:160]
        if not why and not any(must in line for _, _, lines in parts for line in lines):
            why = f"받은 글에 '{must}'가 없음(다른 문서일 수 있음)"
        if why:
            failures.append(f"{name} {code}: {why}")
            continue
        for tail, address, lines in parts:
            path = save_text(f"eu-fulltext/{name}{tail}.txt", [f"[주소] {address}", ""] + lines)
            entries.append({"name": f"{name}{tail}", "code": code, "url": address, "lines": len(lines), "textPath": path})
    save_index("eu-fulltext", entries, {"targets": len(TARGETS), "failures": failures})
    return {"stored": len(entries), "failures": failures}
