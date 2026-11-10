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
    # (이름, 주소, 더할 머리글). 닿는지 모르는 주소만 둔다. 닿는 것이 확인된 출처는 tools.collect가 맡는다.
    ("ec-guidance-page", "https://taxation-customs.ec.europa.eu/carbon-border-adjustment-mechanism/cbam-legislation-and-guidance_en", {}),
    ("cellar-consolidated-html", "http://publications.europa.eu/resource/celex/02023R0956-20251020", {"Accept": "text/html, application/xhtml+xml", "Accept-Language": "eng"}),
    ("cellar-consolidated-pdf", "http://publications.europa.eu/resource/celex/02023R0956-20251020", {"Accept": "application/pdf", "Accept-Language": "eng"}),
    ("cellar-base-xhtml", "http://publications.europa.eu/resource/celex/32023R0956", {"Accept": "application/xhtml+xml", "Accept-Language": "eng"}),
    ("cellar-base-rdf", "http://publications.europa.eu/resource/celex/32023R0956", {"Accept": "application/rdf+xml"}),
    ("eli-oj", "http://data.europa.eu/eli/reg/2023/956/oj", {}),
    ("eurlex-html", "https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:02023R0956-20251020", {}),
    ("hys-api", "https://ec.europa.eu/info/law/better-regulation/brpapi/searchInitiatives?text=CBAM&language=EN&page=0&size=10", {"Accept": "application/json"}),
    ("expert-group-api", "https://ec.europa.eu/transparency/expert-groups-register/core/api/front/expertGroups/3927", {"Accept": "application/json"}),
    ("me-www", "https://www.me.go.kr/home/web/index.do?menuId=286", {}),
    ("mcee", "https://www.mcee.go.kr/", {}),
    ("mcee-bare", "https://mcee.go.kr/", {}),
    ("moj", "https://www.moj.go.kr/bbs/moj/177/artclList.do", {}),
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


def describe(name, url, extra=None):
    status, headers, body, error = fetch(url, headers=extra or {})
    content_type = headers.get("Content-Type", headers.get("content-type", ""))
    text_head = ""
    if body and b"%PDF" not in body[:8]:
        text_head = re.sub(r"\s+", " ", body[:6000].decode("utf-8", "replace"))[:600]
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
    for name, url, extra in TARGETS:
        row, body = describe(name, url, extra)
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
