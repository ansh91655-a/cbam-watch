"""CBAM 법령의 원문에서 제목, 채택일, 관보 게재일, 시행과 적용에 관한 조문을 모은다.

EUR-Lex 화면은 자동 접속을 받지 않으므로, 같은 원문을 내어 주는 EU 출판국의 자료 창구(publications.europa.eu의 CELEX 주소)에서 받는다.
법령 전문은 부속서 때문에 매우 길 수 있어서 앞부분과 마지막 조문만 글로 남긴다. 대상 법령은 EU 집행위원회의 'CBAM legislation and guidance' 화면에 실린 것이다.
"""
import re
import time

from tools.archive.store import iso_from_long, save_index, save_text
from tools.common.htmltext import decode, parse
from tools.common.net import fetch, header

CELLAR = "http://publications.europa.eu/resource/celex/{celex}"
EURLEX = "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:{celex}"
ACTS = ["32025R0486", "32025R2083", "32025R2210", "32025R2546", "32025R2547", "32025R2548", "32025R2549", "32025R2550", "32025R2551",
        "32025R2619", "32025R2620", "32025R2621", "32026R1740"]
HEAD_LINES = 60
LINE_LIMIT = 700
ARTICLE = re.compile(r"^Article \d+[a-z]?$")
OJ_DATE = re.compile(r"^(\d{1,2})\.(\d{1,2})\.(\d{4})$")
ADOPTED = re.compile(r"^of (\d{1,2} [A-Za-z]+ \d{4})$")
PAUSE = 2.0


def digest(lines):
    """법령 글에서 (남길 줄, 관보 게재일, 채택일, 법령 이름, 다루는 내용)을 뽑는다."""
    head = [line[:LINE_LIMIT] for line in lines[:HEAD_LINES]]
    done = max((index for index, line in enumerate(lines) if line.startswith("Done at ")), default=-1)
    tail = []
    if done >= 0:
        starts = [index for index, line in enumerate(lines[:done]) if ARTICLE.match(line.strip())]
        first = starts[-1] if starts and done - starts[-1] < 40 else max(0, done - 6)
        tail = [line[:LINE_LIMIT] for line in lines[first:done + 1]]
    eli = [line for line in lines[-12:] if line.startswith("ELI:")]
    published = next((f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}" for line in lines[:12] for m in [OJ_DATE.match(line.strip())] if m), "")
    adopted_at = next((index for index, line in enumerate(lines[:30]) if ADOPTED.match(line.strip())), -1)
    adopted = iso_from_long(ADOPTED.match(lines[adopted_at].strip()).group(1)) if adopted_at >= 0 else ""
    name = lines[adopted_at - 1].strip() if adopted_at >= 1 else ""
    subject = lines[adopted_at + 1].strip()[:LINE_LIMIT] if 0 <= adopted_at < len(lines) - 1 else ""
    return head + (["", "[마지막 조문]"] + tail if tail else []) + eli, published, adopted, name, subject


def crawl():
    entries, report = [], {"acts": len(ACTS), "stored": 0, "failures": []}
    for celex in ACTS:
        status, headers, body, error = fetch(CELLAR.format(celex=celex), timeout=240, retries=1,
                                             headers={"Accept": "application/xhtml+xml, text/html;q=0.9", "Accept-Language": "eng"})
        time.sleep(PAUSE)
        if status != 200 or not body:
            report["failures"].append(f"{celex} ({status} {error[:60]})")
            continue
        _, lines, _ = parse(decode(body, header(headers, "Content-Type")), CELLAR.format(celex=celex))
        kept, published, adopted, name, subject = digest(lines)
        if not published or not name:
            report["failures"].append(f"{celex} (글에서 날짜나 이름을 찾지 못함)")
            continue
        url = EURLEX.format(celex=celex)
        entries.append({"date": published, "celex": celex, "title": name, "subject": subject, "adopted": adopted, "url": url,
                        "textPath": save_text(f"eur-lex/{celex}.txt", [f"[주소] {url}", f"[받은 곳] {CELLAR.format(celex=celex)}", ""] + kept)})
        report["stored"] += 1
    save_index("eur-lex", sorted(entries, key=lambda entry: entry["date"], reverse=True), report)
    return report
