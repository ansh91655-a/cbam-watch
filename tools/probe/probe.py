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
from tools.probe import forms

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
    ("pages-site", "https://ansh91655-a.github.io/cbam-watch/", {}),
    ("pages-data", "https://ansh91655-a.github.io/cbam-watch/data/site.json", {}),
    ("mcee-board", "https://mcee.go.kr/home/web/index.do?menuId=286", {}),
    ("expert-group-meetings", "https://ec.europa.eu/transparency/expert-groups-register/core/api/front/expertGroups/3927/meetings", {"Accept": "application/json"}),
    ("motir-policy-board", "https://www.motir.go.kr/kor/article/ATCLf724eb567", {}),
    ("motir-policy-trade", "https://www.motir.go.kr/kor/article/ATCLf724eb567?mno=&pageIndex=1&rowPageC=0&displayAuthor=&searchCategory=3&startDtD=&endDtD=&searchCondition=1&searchKeyword=", {}),
]
# 걸러 보기 양식(분류, 한 쪽에 보이는 건수)을 읽어 둘 목록 화면. 게시판을 출처로 더할 때 주소를 정하는 데 쓴다.
FORM_TARGETS = {"motir-policy-board", "motir-policy-trade"}

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
    if name in FORM_TARGETS and body and not row["isPdf"]:
        html = body.decode("utf-8", "replace")
        row["forms"] = forms.describe(html)
        row["postLinks"] = sorted(set(re.findall(r'href="([^"]*/view[^"]*)"', html)))[:12]
        row["rows"] = forms.rows(html)
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
    samples = pathlib.Path("originals/_probe/samples")
    samples.mkdir(parents=True, exist_ok=True)
    for name, url, extra in TARGETS:  # JSON으로 답하는 주소는 모양을 보려고 앞부분을 남긴다
        if "api" in name or "meetings" in name:
            _, _, body, _ = fetch(url, headers=extra)
            (samples / f"{name}.json").write_bytes(body[:60000])
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
