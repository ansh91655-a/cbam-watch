"""EU 법령 데이터베이스 문서의 PDF 첫 장을 그림으로 받는다(kind가 "pdf"인 것만).

쓰는 법: python -m tools.thumbs.pdfcover <할 일 파일> <그림을 둘 폴더>   결과는 <폴더>/pdfs.json에 쓴다.
EU 출판국의 자료 창구에서 CELEX 번호로 PDF를 받아 pdftoppm으로 첫 장을 그린다. 한 문서에 파일이 여럿이면 첫 파일(본문)을 받는다.
"""
import pathlib
import re
import subprocess
import sys
import time

from tools.common.jsonio import read_json, write_json
from tools.common.net import fetch

CELLAR = "http://publications.europa.eu/resource/celex/{celex}"
ACCEPT = {"Accept": "application/pdf", "Accept-Language": "eng"}
CHOICE = re.compile(rb"https?://publications\.europa\.eu/resource/cellar/[0-9a-f\-]+\.\d+\.\d+/DOC_\d+")


def pdf_of(celex):
    """(PDF 바이트, 사유). 받지 못하면 (b"", 사유)."""
    status, _, body, error = fetch(CELLAR.format(celex=celex), timeout=120, retries=1, headers=ACCEPT)
    time.sleep(1)
    if status == 300 and body:
        choices = sorted({match.decode() for match in CHOICE.findall(body)}, key=lambda url: (not url.endswith("DOC_1"), url))
        for choice in choices[:3]:
            status, _, body, error = fetch(choice, timeout=120, retries=1, headers=ACCEPT)
            time.sleep(1)
            if status == 200 and body[:5] == b"%PDF-":
                break
    if status == 200 and body[:5] == b"%PDF-":
        return body, ""
    return b"", f"응답 {status} {error[:60]}".strip()


def first_page(pdf, target):
    """PDF 바이트의 첫 장을 target(확장자 없는 경로).png로 그린다. 됐으면 빈 글, 아니면 사유."""
    source = pathlib.Path(f"{target}.pdf")
    source.write_bytes(pdf)
    done = subprocess.run(["pdftoppm", "-f", "1", "-l", "1", "-r", "110", "-png", "-singlefile", str(source), str(target)], capture_output=True)
    source.unlink(missing_ok=True)
    return "" if done.returncode == 0 and pathlib.Path(f"{target}.png").exists() else f"첫 장을 그리지 못함: {done.stderr.decode('utf-8', 'replace')[:80]}"


def main(argv):
    todo, out = argv[0], pathlib.Path(argv[1])
    out.mkdir(parents=True, exist_ok=True)
    results = []
    for job in [job for job in read_json(todo, []) if job.get("kind") == "pdf"]:
        pdf, why = pdf_of(job["celex"])
        why = why or first_page(pdf, out / job["name"])
        results.append({"name": job["name"], "ok": not why, **({"why": why} if why else {})})
        print("받음" if not why else "실패", job["celex"], why, flush=True)
    write_json(out / "pdfs.json", results)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
