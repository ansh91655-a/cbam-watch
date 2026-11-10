"""EFTA의 EEA 법령 기록(EEA-Lex)에서 CBAM 규정이 EEA 협정에 들어간 상태를 읽는다.

화면 전체를 옮기지 않고, 편입 상태와 공동위원회 결정을 적은 줄만 남긴다.
"""
import re
import time

from tools.archive.store import save_index, save_text
from tools.common.htmltext import decode, parse
from tools.common.net import fetch, header

PAGES = {"32023R0956": "https://www.efta.int/eea-lex/32023r0956", "32025R2083": "https://www.efta.int/eea-lex/32025r2083"}
WANTED = re.compile(r"Joint Committee Decision|JCD|Incorporated|incorporation|Entry into force|Compliance date|under scrutiny|Legal status"
                    r"|Constitutional requirements|\b\d{1,2}[./]\d{1,2}[./]20\d\d\b|\b20\d\d-\d\d-\d\d\b|\d{3}/20\d\d", re.I)


def crawl():
    entries, report = [], {"pages": {}}
    for celex, url in PAGES.items():
        status, headers, body, error = fetch(url, retries=1)
        time.sleep(1.5)
        if status != 200 or not body:
            report["pages"][celex] = f"읽지 못함({status} {error[:60]})"
            continue
        _, lines, _ = parse(decode(body, header(headers, "Content-Type")), url)
        kept = []
        for index, line in enumerate(lines):
            if WANTED.search(line) and len(line) < 400:
                kept += [text for text in lines[max(0, index - 1):index + 2] if len(text) < 400 and text not in kept]
        entries.append({"celex": celex, "title": lines[0][:200] if lines else "", "url": url,
                        "textPath": save_text(f"efta/{celex}.txt", [f"[주소] {url}", ""] + kept[:120])})
        report["pages"][celex] = {"lines": len(lines), "kept": len(kept)}
    save_index("efta-eea-lex", entries, report)
    return report
