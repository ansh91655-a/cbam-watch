"""자동 실행 환경에서 출처에 닿는지 알아보는 점검 프로그램.

결과를 originals/_probe/result.json에 쓴다. 저장소 맨 위에서 `python -m tools.probe.probe`로 돌린다.
"""
import datetime
import json
import pathlib
import re
import subprocess
import tempfile

from tools.common.net import fetch, sha256_hex

TARGETS = [
    ("ec-guidance-page", "https://taxation-customs.ec.europa.eu/carbon-border-adjustment-mechanism/cbam-legislation-and-guidance_en"),
    ("ec-news-page", "https://taxation-customs.ec.europa.eu/carbon-border-adjustment-mechanism/cbam-communication-and-news_en"),
    ("eurlex-pdf", "https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=CELEX:02023R0956-20251020"),
    ("eurlex-html", "https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:02023R0956-20251020"),
    ("eurlex-eli", "https://eur-lex.europa.eu/eli/reg/2023/956/oj"),
    ("have-your-say", "https://ec.europa.eu/info/law/better-regulation/have-your-say/initiatives_en?text=CBAM"),
    ("expert-groups", "https://ec.europa.eu/transparency/expert-groups-register/screen/expert-groups/consult?lang=en&groupID=3927"),
    ("me-go-kr", "https://me.go.kr/home/web/index.do?menuId=286"),
    ("compass", "https://www.compass.or.kr/eucbam/data/list"),
    ("moj", "https://www.moj.go.kr/bbs/moj/177/artclList.do"),
    ("carbon-pulse", "https://carbon-pulse.com/category/international/cbam-tariffs/"),
    ("keco", "https://www.keco.or.kr/web/lay1/bbs/S1T165C1421/A/279/list.do"),
    ("motir", "https://www.motir.go.kr/kor/article/ATCL3f49a5a8c"),
]

OUT = pathlib.Path("originals/_probe/result.json")


def pdf_text_chars(data):
    """PDF 본문의 글자 수. pdftotext가 없거나 실패하면 -1."""
    try:
        with tempfile.NamedTemporaryFile(suffix=".pdf") as handle:
            handle.write(data)
            handle.flush()
            done = subprocess.run(["pdftotext", handle.name, "-"], capture_output=True, timeout=120)
            return len(done.stdout.decode("utf-8", "replace")) if done.returncode == 0 else -1
    except Exception:
        return -1


def describe(name, url):
    status, headers, body, error = fetch(url)
    content_type = headers.get("Content-Type", headers.get("content-type", ""))
    text_head = ""
    if body and b"%PDF" not in body[:8]:
        text_head = re.sub(r"\s+", " ", body[:4000].decode("utf-8", "replace"))[:300]
    row = {
        "name": name,
        "url": url,
        "status": status,
        "contentType": content_type,
        "bytes": len(body),
        "sha256": sha256_hex(body) if body else "",
        "isPdf": body[:5] == b"%PDF-",
        "error": error[:200],
        "head": text_head,
    }
    if row["isPdf"]:
        row["pdfTextChars"] = pdf_text_chars(body)
    return row, body


def main():
    rows = []
    links = []
    for name, url in TARGETS:
        row, body = describe(name, url)
        if name == "ec-guidance-page" and body:
            html = body.decode("utf-8", "replace")
            found = re.findall(r'href="([^"]*document/download/[^"]+)"', html)
            links = sorted(set(found))
            row["documentLinks"] = len(links)
        rows.append(row)
    for index, link in enumerate(links[:3]):
        url = link if link.startswith("http") else "https://taxation-customs.ec.europa.eu" + link
        row, _ = describe(f"ec-document-{index + 1}", url.replace("&amp;", "&"))
        rows.append(row)
    result = {
        "checkedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "rows": rows,
        "sampleLinks": [link.replace("&amp;", "&") for link in links[:40]],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    for row in rows:
        print(row["name"], row["status"], row["bytes"], row["contentType"][:30], row.get("pdfTextChars", ""))


if __name__ == "__main__":
    main()
