"""법령의 관보 PDF를 받아 둔다. 규정 원문 화면이 법령의 원문 PDF와 번역 PDF를 나란히 보여 주는 데 쓴다.

받는 곳은 EU 출판국 자료 창구다. 글을 받는 단계(tools/archive/fulltext.py)와 같은 주소에 PDF를 달라고 청한다.
EU 법령은 출처를 밝히고 다시 쓸 수 있다. 한 법령에 파일이 여럿이면(본문과 부속서) 차례대로 이어 붙여 하나로 둔다.
받은 파일은 collected/archive/pdfs/<CELEX 번호>.pdf에, 목록은 collected/archive/eu-pdfs.json에 둔다.
손으로 돌린다: 워크플로 '소급 수집'에서 mode = crawl, steps = eu-pdfs.
"""
import hashlib
import io
import time

from tools.archive import acts
from tools.archive.fulltext import CELLAR, CHOICE, STORED
from tools.archive.store import ROOT, save_index
from tools.cn import versions
from tools.common.htmltext import decode, parse
from tools.common.jsonio import read_json
from tools.common.net import fetch, header

# 자료 창구는 PDF의 꼴(type)까지 맞아야 내준다. 관보의 꼴은 해마다 달랐으므로 차례대로 청해 본다.
KINDS = ("application/pdf;type=pdfa2a", "application/pdf;type=pdfa1a", "application/pdf;type=pdfa1b", "application/pdf;type=pdfx", "application/pdf")
FOLDER = ROOT / "pdfs"
LIMIT = 45 * 1024 * 1024   # 파일 하나의 크기 한도. 넘으면 받지 않고 알린다
MOST = 12                  # 한 법령에서 받는 파일 수의 한도
PAUSE = 1.5


def targets():
    """받을 법령: 사이트가 싣는 CBAM 규정 통합본과 하위 법령들. [(CELEX 번호, 무엇인지)]"""
    used = next((entry.get("celex") for entry in read_json(STORED, {}).get("entries", []) if entry.get("name") == "cbam-consolidated"), None)
    return [(used or versions.FIRST, "CBAM 규정 통합본")] + list(acts.ACTS)


def _pdf(address, kinds=KINDS):
    """주소에 PDF를 청한다. 받았거나 여럿 가운데 고르라는 답이 올 때까지 꼴을 바꿔 가며 청한다. 마지막 답과 그때의 꼴을 돌려준다."""
    answer = (0, {}, b"", "청해 보지 않음")
    for kind in kinds:
        answer = fetch(address, timeout=300, retries=1, headers={"Accept": kind, "Accept-Language": "eng"})
        time.sleep(PAUSE)
        status, _, body, _ = answer
        if (status == 200 and body.startswith(b"%PDF")) or status == 300:
            return answer + (kind,)
    return answer + ("",)


def files(celex):
    """법령 하나의 PDF 파일들(차례대로)과 사유. 파일이 하나면 그대로, 여럿을 고르라는 답이면 모두 받는다."""
    address = CELLAR.format(celex=celex)
    status, headers, body, error, kind = _pdf(address)
    if status == 200 and body.startswith(b"%PDF"):
        return [body], ""
    if status != 300 or not body:
        return [], f"응답 {status} {error[:60]}".strip()
    links, _, _ = parse(decode(body, header(headers, "Content-Type")), address)
    choices = sorted({url for url, _ in links if CHOICE.search(url)}, key=lambda url: int(CHOICE.search(url).group(1)))
    found = []
    for choice in choices[:MOST]:
        status, headers, body, error, _ = _pdf(choice, (kind,))
        if status == 200 and body.startswith(b"%PDF"):
            found.append(body)
        else:
            return [], f"고를 파일 {CHOICE.search(choice).group(1)}번: 응답 {status} {error[:60]}".strip()
    return found, "" if found else "고를 파일이 없음"


def join(parts):
    """파일 여럿을 차례대로 이어 붙인 PDF와 쪽 수. 하나면 그대로 둔다."""
    import pikepdf  # 워크플로에서 따로 설치한다

    if len(parts) == 1:
        with pikepdf.open(io.BytesIO(parts[0])) as only:
            return parts[0], len(only.pages)
    whole = pikepdf.Pdf.new()
    for data in parts:
        with pikepdf.open(io.BytesIO(data)) as part:
            whole.pages.extend(part.pages)
    out = io.BytesIO()
    whole.save(out, deterministic_id=True)
    return out.getvalue(), len(whole.pages)


def crawl():
    entries, failures = [], []
    FOLDER.mkdir(parents=True, exist_ok=True)
    before = {entry["celex"]: entry for entry in read_json(ROOT / "eu-pdfs.json", {}).get("entries", [])}
    for celex, what in targets():
        kept = before.get(celex)
        if kept and (FOLDER / f"{celex}.pdf").exists():   # 이미 받아 둔 법령은 다시 받지 않는다(관보의 글은 바뀌지 않는다)
            entries.append(kept)
            continue
        try:
            parts, why = files(celex)
            data, pages = join(parts) if parts else (b"", 0)
        except Exception as problem:
            data, pages, why = b"", 0, f"{type(problem).__name__}: {problem}"[:160]
        if not why and len(data) > LIMIT:
            why = f"파일이 너무 큼({len(data) // (1024 * 1024)}MB)"
        if why:
            failures.append(f"{celex}: {why}")
            continue
        path = FOLDER / f"{celex}.pdf"
        path.write_bytes(data)
        entries.append({"celex": celex, "title": what, "url": f"https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=CELEX:{celex}",
                        "from": CELLAR.format(celex=celex), "file": str(path), "bytes": len(data), "pages": pages, "parts": len(parts),
                        "sha256": hashlib.sha256(data).hexdigest()})
    save_index("eu-pdfs", entries, {"targets": len(targets()), "failures": failures})
    return {"stored": len(entries), "failures": failures}
