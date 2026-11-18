"""법령의 관보 PDF를 받아 둔다. 규정 원문 화면이 법령의 원문 PDF와 번역 PDF를 나란히 보여 주는 데 쓴다.

받는 곳은 EU 출판국 자료 창구다. 글을 받는 단계(tools/archive/fulltext.py)와 같은 주소에 PDF를 달라고 청한다.
EU 법령은 출처를 밝히고 다시 쓸 수 있다. 한 법령에 파일이 여럿이면(본문과 부속서) 차례대로 이어 붙여 하나로 둔다.
받은 파일은 collected/archive/pdfs/<CELEX 번호>.pdf에, 목록은 collected/archive/eu-pdfs.json에 둔다.
나라별 기본값의 표가 수천 쪽에 이르는 법령은 일부 쪽만 둔다(KEEP). 목록에 온 파일의 쪽 수(fullPages)와 남긴 쪽(kept)을 적는다.
날마다의 수집(.github/workflows/collect.yml)이 돌린다. 받아 두지 않은 것만 받으므로 평소에는 아무것도 청하지 않는다.
손으로 돌릴 때는 워크플로 '소급 수집'에서 mode = crawl, steps = eu-pdfs. 받지 못한 법령은 실행 확인(tools.run.laws_health)이 알린다.
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
# 일부 쪽만 두는 법령: [(첫 쪽, 끝 쪽)]. 관보의 파일은 바뀌지 않으므로 쪽 번호로 적는다.
KEEP = {
    # 기본값 이행규정(2,400쪽): 조문과 부속서 I의 머리말(1~4쪽), 부속서 II와 III(간접배출과 전력의 기본값, 2350~2354쪽).
    # 부속서 I과 IV의 표는 정정 규정 (EU) 2026/1740이 통째로 바꿔 넣었으므로 두지 않는다.
    "32025R2621": [(1, 4), (2350, 2354)],
    # 정정 규정(1,913쪽): 조문과 새 부속서 I의 머리말(1~4쪽), 대한민국의 표(821~862쪽), '그 밖의 나라와 영역'의 표와 새 부속서 IV(1840~1913쪽).
    "32026R1740": [(1, 4), (821, 862), (1840, 1913)],
}
# 남긴 쪽에 무엇이 있는지. 목록에 적어 두고(about) 화면이 그대로 알린다.
ABOUT = {
    "32025R2621": "조문과 부속서 I의 머리말, 부속서 II와 III(간접배출과 전력의 기본값)",
    "32026R1740": "조문과 새 부속서 I의 머리말, 대한민국의 표, '그 밖의 나라와 영역'의 표, 새 부속서 IV",
}


def targets():
    """받을 법령: 사이트가 싣는 CBAM 규정 통합본과 하위 법령들. [(CELEX 번호, 무엇인지)]"""
    used = next((entry.get("code") for entry in read_json(STORED, {}).get("entries", []) if entry.get("name") == "cbam-consolidated"), None)
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


def join(parts, keep=None):
    """파일 여럿을 차례대로 이어 붙인 PDF, 그 쪽 수, 온 파일의 쪽 수. keep을 주면 그 쪽들만 남긴다.

    손대지 않아도 되는 파일(하나이고 모든 쪽을 두는 것)은 받은 그대로 돌려준다.
    쪽을 덜어 낸 파일은 새로 엮으므로 원문의 꼬리표 짜임이 따라오지 않는다.
    """
    import pikepdf  # 워크플로에서 따로 설치한다

    if len(parts) == 1 and not keep:
        with pikepdf.open(io.BytesIO(parts[0])) as only:
            return parts[0], len(only.pages), len(only.pages)
    opened = [pikepdf.open(io.BytesIO(data)) for data in parts]
    try:
        whole = pikepdf.Pdf.new()
        pages = [page for part in opened for page in part.pages]
        wanted = [number for first, last in keep for number in range(first, last + 1)] if keep else range(1, len(pages) + 1)
        if any(number < 1 or number > len(pages) for number in wanted):
            raise ValueError(f"남길 쪽이 파일의 쪽 수({len(pages)})를 벗어남")
        for number in wanted:
            whole.pages.append(pages[number - 1])
        out = io.BytesIO()
        whole.save(out, deterministic_id=True)
        return out.getvalue(), len(whole.pages), len(pages)
    finally:
        for part in opened:
            part.close()


def entry(celex, what, parts):
    """받은 파일들로 저장할 PDF와 목록의 한 줄을 만든다: (파일의 바이트, 목록의 줄)."""
    keep = KEEP.get(celex)
    data, pages, full = join(parts, keep)
    line = {"celex": celex, "title": what, "url": f"https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=CELEX:{celex}",
            "from": CELLAR.format(celex=celex), "file": str(FOLDER / f"{celex}.pdf"), "bytes": len(data), "pages": pages, "parts": len(parts),
            "sha256": hashlib.sha256(data).hexdigest()}
    if keep:
        line.update({"fullPages": full, "kept": [list(span) for span in keep], "about": ABOUT.get(celex, "")})
    return data, line


def crawl():
    """받아 두지 않은 법령의 PDF만 받는다. 이미 받은 것은 다시 청하지 않고(관보의 글은 바뀌지 않는다), 받을 것이 없으면 목록도 그대로 둔다.

    더는 싣지 않는 판의 파일(CBAM 규정의 지난 통합본)은 지운다.
    """
    entries, failures, fetched = [], [], 0
    FOLDER.mkdir(parents=True, exist_ok=True)
    before = {line["celex"]: line for line in read_json(ROOT / "eu-pdfs.json", {}).get("entries", [])}
    wanted = targets()
    for celex, what in wanted:
        kept = before.get(celex)
        if kept and (FOLDER / f"{celex}.pdf").exists():
            entries.append(kept)
            continue
        try:
            parts, why = files(celex)
            data, line = entry(celex, what, parts) if parts else (b"", None)
        except Exception as problem:
            data, line, why = b"", None, f"{type(problem).__name__}: {problem}"[:160]
        if not why and len(data) > LIMIT:
            why = f"파일이 너무 큼({len(data) // (1024 * 1024)}MB)"
        if why:
            failures.append(f"{celex}: {why}")
            continue
        (FOLDER / f"{celex}.pdf").write_bytes(data)
        entries.append(line)
        fetched += 1
    names = {celex for celex, _ in wanted}
    stale = [path for path in FOLDER.glob("*.pdf") if path.stem not in names]
    for path in stale:
        path.unlink()
    if fetched or stale or len(entries) != len(before):
        save_index("eu-pdfs", entries, {"targets": len(wanted), "failures": failures}, incomplete=False)
    return {"stored": len(entries), "fetched": fetched, "removed": len(stale), "failures": failures}
