"""EU 이사회 문서 등록부에서 CBAM 입법의 이사회 쪽 문서(일반 접근 본문, 회의록)를 받아 앞부분의 글을 남긴다.

이사회 누리집의 보도자료 화면은 자동 접속을 받지 않아서, 문서 등록부의 PDF를 읽는다. PDF에서 글을 뽑는 데 pypdf가 필요하다.
"""
import io
import time

from tools.archive.store import save_index, save_text
from tools.common.htmltext import squeeze
from tools.common.net import fetch

PDF = "https://data.consilium.europa.eu/doc/document/{code}/en/pdf"
# (문서 번호, 날짜, 무엇인지). 날짜는 문서 머리에 적힌 날이며, 받은 글에 그 날짜가 있는지는 원문 대조에서 다시 본다.
DOCUMENTS = [
    ("ST-10423-2026-INIT", "2026-06-12", "CBAM 하류제품 확대·우회방지 개정안에 대한 이사회 일반 접근 본문"),
    ("ST-10684-2026-INIT", "2026-06-25", "2026년 6월 12일 경제·재무 이사회 회의록 초안"),
]
MAX_PAGES, MAX_LINES, LINE_LIMIT = 12, 260, 700


def text_of(body):
    from pypdf import PdfReader  # 워크플로에서 따로 설치한다
    reader = PdfReader(io.BytesIO(body))
    lines = []
    for page in reader.pages[:MAX_PAGES]:
        lines += [squeeze(line) for line in (page.extract_text() or "").splitlines() if squeeze(line)]
    return lines, len(reader.pages)


def crawl():
    entries, report = [], {"documents": len(DOCUMENTS), "stored": 0, "failures": []}
    for code, date, label in DOCUMENTS:
        url = PDF.format(code=code)
        status, _, body, error = fetch(url, timeout=120, retries=1)
        time.sleep(2)
        if status != 200 or not body.startswith(b"%PDF"):
            report["failures"].append(f"{code} ({status} {error[:60]})")
            continue
        try:
            lines, pages = text_of(body)
        except Exception as problem:
            report["failures"].append(f"{code} (글을 뽑지 못함: {type(problem).__name__}: {problem})"[:200])
            continue
        entries.append({"date": date, "code": code, "label": label, "pages": pages, "url": url,
                        "textPath": save_text(f"eu-council/{code}.txt", [f"[주소] {url}", ""] + [line[:LINE_LIMIT] for line in lines[:MAX_LINES]])})
        report["stored"] += 1
    save_index("eu-council", entries, report)
    return report
