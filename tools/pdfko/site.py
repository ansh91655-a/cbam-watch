"""사이트에 싣는 국문 PDF: 문서마다 만들어 pdf/ 아래에 두고, 원문 PDF의 자리와 함께 목록(data/laws/pdf.json)에 적는다.

만드는 데 시간이 걸리므로 만든 파일을 .cache/pdfko에 두고, 입력(원문 PDF, 단위, 앉힐 번역, 만드는 프로그램, 글꼴)이 같으면 다시 만들지 않는다.
필요한 꾸러미(pikepdf, reportlab, pdfminer)나 pdftotext가 없는 환경에서는 아무것도 만들지 않고 빈 목록을 쓴다(화면은 PDF 보기를 감춘다).
"""

import hashlib
import json
import pathlib
import shutil

CACHE = pathlib.Path(".cache/pdfko")
FOLDER = "pdf"


def _code():
    """만드는 프로그램과 글꼴이 바뀌면 달라지는 값."""
    digest = hashlib.sha256()
    for path in sorted(pathlib.Path(__file__).parent.glob("*.py")) + sorted(pathlib.Path("assets/fonts").glob("*.ttf")):
        digest.update(path.name.encode("utf-8"))
        digest.update(path.read_bytes() if path.suffix == ".py" else str(path.stat().st_size).encode("ascii"))
    return digest.hexdigest()


def _digest(code, source, wanted):
    digest = hashlib.sha256(code.encode("ascii"))
    digest.update(pathlib.Path(source).read_bytes())
    digest.update(json.dumps(wanted, ensure_ascii=False, sort_keys=True).encode("utf-8"))
    return digest.hexdigest()[:20]


def _made(document, parts, memory, code):
    """문서 하나의 국문 PDF(캐시에 든 파일)와 보고. 앉힐 번역이 없으면 (None, None)."""
    from tools.laws import corpus
    from tools.pdfko import build

    source = build.source(document)
    if source is None:
        return None, None
    units = corpus.units(document)
    wanted = build.items(parts, units, memory) if units else build.paragraphs(parts, memory)
    if not wanted:
        return None, None
    name = f"{document['id']}.{_digest(code, source, wanted)}"
    made, noted = CACHE / f"{name}.pdf", CACHE / f"{name}.json"
    if not (made.is_file() and noted.is_file()):
        CACHE.mkdir(parents=True, exist_ok=True)
        for old in CACHE.glob(f"{document['id']}.*"):
            old.unlink()
        half = CACHE / f"{name}.part"
        report = build.build(source, wanted, half, document.get("name", ""), document.get("official", ""), units)
        report.pop("notes", None)
        half.replace(made)
        noted.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
    return made, {**json.loads(noted.read_text(encoding="utf-8")), "source": str(source)}


def write(out):
    """out(사이트 폴더)에 국문 PDF와 목록을 쓰고, 실은 문서의 수를 돌려준다."""
    out = pathlib.Path(out)
    listing = out / "data" / "laws" / "pdf.json"
    listing.parent.mkdir(parents=True, exist_ok=True)
    docs = {}
    try:
        from tools.laws import corpus
        from tools.pdfko import build  # noqa: F401 — 꾸러미가 있는지 여기에서 안다
        from tools.publish import derive
        ready = shutil.which("pdftotext") is not None
    except ImportError:
        ready = False
    if ready:
        documents, memory = corpus.everything()
        code = _code()
        for document, parts in documents:
            if document.get("format") != "pdf" or not parts:
                continue
            try:
                made, report = _made(document, parts, memory, code)
            except Exception as error:  # 한 문서가 안 되어도 나머지와 사이트는 만든다
                print(f"국문 PDF를 만들지 못함: {document['id']}: {error!r}"[:300])
                continue
            if made is None:
                continue
            target = out / FOLDER / f"{document['id']}-ko.pdf"
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(made, target)
            source = report["source"]
            sizes = [tuple(size) for size in report["sizes"]]
            usual = max(set(sizes), key=sizes.count)
            docs[document["id"]] = {
                "pages": report["pages"], "ko": f"{FOLDER}/{target.name}", "koBytes": target.stat().st_size,
                "en": derive.PUBLIC_FILES + source[len(derive.STORE):], "enBytes": pathlib.Path(source).stat().st_size,
                "paragraphs": report["paragraphs"], "placed": report["placed"],
                # 쪽의 크기(pt): 거의 모든 쪽의 크기와, 그와 다른 쪽들(쪽 번호: 크기). 화면이 그리기 전에 자리를 잡는 데 쓴다
                "size": list(usual), "odd": {str(number + 1): list(size) for number, size in enumerate(sizes) if size != usual},
            }
    else:
        print("알림: 국문 PDF를 만드는 도구(pikepdf, reportlab, pdftotext)가 없어 PDF 보기를 싣지 않습니다.")
    listing.write_text(json.dumps({"docs": docs}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return len(docs)
