"""사이트에 싣는 국문 PDF: 문서마다 만들어 pdf/ 아래에 두고, 원문 PDF의 자리와 함께 목록(data/laws/pdf.json)에 적는다.

만드는 데 시간이 걸리므로 만든 파일을 .cache/pdfko에 두고, 입력(원문 PDF, 단위, 앉힐 번역, 만드는 프로그램, 글꼴)이 같으면 다시 만들지 않는다.
필요한 꾸러미(pikepdf, reportlab, pdfminer)나 pdftotext가 없는 환경에서는 아무것도 만들지 않고 빈 목록을 쓴다(화면은 PDF 보기를 감춘다).
목록에는 실어야 할 문서의 수(wanted)와 만들지 못한 문서(failed), 도구가 있었는지(tools)도 적는다. 배포할 때 빠진 문서가 있으면
지난 배포의 것을 그대로 두고(keep), 그 사실도 목록에 남는다(kept). 상태 점검(tools.run.health)이 이 값들을 보고 알린다.

    python3 -m tools.pdfko.site keep <사이트 폴더>   # 배포 직전: 이번에 빠진 문서의 국문 PDF를 지난 배포(origin/gh-pages)에서 가져온다
"""

import hashlib
import json
import pathlib
import shutil
import subprocess
import sys

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
    docs, failed = {}, []
    from tools.laws import corpus
    documents, memory = corpus.published()   # 검수를 거친 번역만 앉힌다
    # 도안으로 된 자료(sources/guides.json에 "side": false로 적은 문서)는 싣지 않는다: 그림으로 박힌 제목 위에 번역이 겹치고
    # 기관의 표지가 그대로 남아, 공식 문서처럼 보이지 않게 해야 하는 번역본의 조건을 채우지 못한다. 글로 보기에는 그대로 실린다.
    documents = [(document, parts) for document, parts in documents if document.get("side", True)]
    wanted = [document["id"] for document, parts in documents if document.get("format") == "pdf" and parts]
    try:
        from tools.pdfko import build  # noqa: F401 — 꾸러미가 있는지 여기에서 안다
        from tools.publish import derive
        ready = shutil.which("pdftotext") is not None
    except ImportError:
        ready = False
    if ready:
        code = _code()
        for document, parts in documents:
            if document.get("format") != "pdf" or not parts:
                continue
            state = corpus.progress(parts, memory)
            if state["done"] < state["blocks"]:
                wanted.remove(document["id"])  # 번역이 다 준비되지 않은 문서의 국문 PDF는 싣지 않는다(원문과 번역이 섞인 PDF를 내지 않는다)
                continue
            try:
                made, report = _made(document, parts, memory, code)
            except Exception as error:  # 한 문서가 안 되어도 나머지와 사이트는 만든다
                print(f"::warning::국문 PDF를 만들지 못함: {document['id']}: {error!r}"[:300])
                failed.append(document["id"])
                continue
            if made is None:
                wanted.remove(document["id"])  # 앉힐 번역이 아직 없는 문서는 실을 것으로 세지 않는다
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
        print("::warning::국문 PDF를 만드는 도구(pikepdf, reportlab, pdftotext)가 없어 이번에는 국문 PDF를 만들지 못했습니다.")
    listing.write_text(json.dumps({"docs": docs, "wanted": len(wanted), "failed": failed, "tools": ready}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return len(docs)


def _git(folder, *arguments):
    done = subprocess.run(["git", "-C", str(folder), *arguments], capture_output=True, timeout=600)
    return done.returncode == 0, done.stdout.decode("utf-8", "replace")


def keep(out, ref="origin/gh-pages"):
    """이번에 만들지 못한 문서의 국문 PDF를 지난 배포에서 가져와 그대로 싣는다. 돌려주는 것은 그렇게 둔 문서들.

    out은 지난 배포를 받아 둔(git fetch) 사이트 폴더다. 지난 배포가 없거나 가져오지 못한 문서는 빠진 채로 둔다(목록의 수가 wanted보다 적게 남는다).
    """
    out = pathlib.Path(out)
    listing = out / "data" / "laws" / "pdf.json"
    now = json.loads(listing.read_text(encoding="utf-8"))
    if len(now.get("docs", {})) >= int(now.get("wanted", 0)):
        return []
    found, text = _git(out, "show", f"{ref}:data/laws/pdf.json")
    try:
        before = json.loads(text).get("docs", {}) if found else {}
    except ValueError:
        before = {}
    kept = []
    for name, entry in sorted(before.items()):
        if name in now["docs"] or not (out / entry.get("en", "")).is_file():
            continue
        if _git(out, "checkout", ref, "--", entry["ko"])[0] and (out / entry["ko"]).is_file():
            now["docs"][name] = entry
            kept.append(name)
    if kept:
        now["kept"] = kept
        listing.write_text(json.dumps(now, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return kept


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "keep":
        names = keep(sys.argv[2])
        if names:
            print(f"::warning::국문 PDF {len(names)}건은 이번에 만들지 못해 지난 배포의 것을 그대로 실었습니다: {', '.join(names)}"[:400])
    else:
        print(__doc__)
