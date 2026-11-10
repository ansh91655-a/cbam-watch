"""미국 연방관보(Federal Register)에서 EU CBAM을 다룬 미국 무역대표부 공고를 모은다. 미국 연방정부의 저작물은 자유롭게 쓸 수 있다."""
import json
import time
import urllib.parse

from tools.archive.store import SINCE, save_index, save_text
from tools.common.net import fetch

SEARCH = "https://www.federalregister.gov/api/v1/documents.json?" + urllib.parse.urlencode({
    "conditions[term]": '"carbon border adjustment"', "conditions[publication_date][gte]": SINCE, "per_page": "100", "order": "newest"})
FIELDS = ["title", "type", "abstract", "document_number", "publication_date", "comments_close_on", "dates", "docket_ids", "citation", "action"]


def crawl():
    status, _, body, error = fetch(SEARCH, headers={"Accept": "application/json"}, retries=1)
    time.sleep(1)
    if status != 200 or not body:
        save_index("us-fedreg", [], {"error": f"{status} {error[:80]}"})
        return {"error": status}
    rows = json.loads(body.decode("utf-8", "replace")).get("results") or []
    entries = []
    for row in rows:
        agencies = [agency.get("name", "") for agency in row.get("agencies") or []]
        title = row.get("title") or ""
        # 제목이 CBAM을 말하는 공고만 남긴다(본문에서 스치듯 말하는 다른 부처 공고는 뺀다)
        if "carbon border adjustment" not in title.lower() and "cbam" not in title.lower():
            continue
        detail_status, _, detail_body, _ = fetch(f"https://www.federalregister.gov/api/v1/documents/{row.get('document_number')}.json",
                                                 headers={"Accept": "application/json"}, retries=1)
        time.sleep(1)
        detail = json.loads(detail_body.decode("utf-8", "replace")) if detail_status == 200 and detail_body else row
        lines = [f"[주소] {detail.get('html_url', '')}", f"기관: {', '.join(agencies)}"]
        lines += [f"{field}: {detail.get(field)}" for field in FIELDS if detail.get(field)]
        entries.append({"date": detail.get("publication_date", ""), "number": detail.get("document_number", ""), "title": title,
                        "agencies": agencies, "commentsClose": detail.get("comments_close_on") or "", "url": detail.get("html_url", ""),
                        "textPath": save_text(f"us-fedreg/{detail.get('document_number')}.txt", lines)})
    save_index("us-fedreg", entries, {"results": len(rows), "kept": len(entries)})
    return {"results": len(rows), "kept": len(entries)}
