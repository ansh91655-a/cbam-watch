"""EU 집행위원회 CBAM 화면의 '최신 소식(Latest developments)' 목록이 지난날에 어떤 모습이었는지 모은다.

그 목록은 가장 최근의 몇 건만 보여 주고 지난 것은 화면에서 내려간다. 인터넷 아카이브(web.archive.org)가 보관한
같은 화면의 사본에서 목록 부분을 읽어, 내려간 소식을 되찾는다. 사본의 글은 EU 집행위원회가 쓴 것이다.
"""
import hashlib
import json
import time

from tools.archive.store import save_index, save_text
from tools.collect.extract import DATE_LINE
from tools.common.htmltext import decode, parse
from tools.common.net import fetch, header

PAGES = [
    "https://taxation-customs.ec.europa.eu/carbon-border-adjustment-mechanism_en",
    "https://taxation-customs.ec.europa.eu/carbon-border-adjustment-mechanism/cbam-communication-and-news_en",
]
CDX = "https://web.archive.org/cdx/search/cdx?url={url}&from=20250101&output=json&filter=statuscode:200&collapse=timestamp:8&fl=timestamp,original"
SNAPSHOT = "https://web.archive.org/web/{stamp}id_/{url}"
GAP_DAYS = 5        # 사본을 이만큼 건너뛰며 읽는다
SECTION_LINES = 170  # 목록 부분으로 남기는 줄 수
PAUSE = 2.5
LIMIT = 150


def _day_number(stamp):
    year, month, day = int(stamp[:4]), int(stamp[4:6]), int(stamp[6:8])
    return year * 372 + month * 31 + day


def choose(stamps):
    """사본의 시각 목록에서 GAP_DAYS 간격으로 고른다. 마지막 사본은 반드시 넣는다."""
    chosen = []
    for stamp in sorted(stamps):
        if not chosen or _day_number(stamp) - _day_number(chosen[-1]) >= GAP_DAYS:
            chosen.append(stamp)
    if stamps and sorted(stamps)[-1] not in chosen:
        chosen.append(sorted(stamps)[-1])
    return chosen[:LIMIT]


def section(lines):
    """화면의 글에서 '최신 소식' 목록 부분을 잘라 낸다. 제목 줄 바로 뒤에 날짜 줄이 오는 곳을 목록의 시작으로 본다."""
    starts = [index for index, line in enumerate(lines) if line.strip().lower() in ("latest developments", "latest news", "news")]
    for start in starts:
        if any(DATE_LINE.match(line) for line in lines[start + 1:start + 5]):
            return lines[start:start + SECTION_LINES]
    dated = [index for index, line in enumerate(lines) if DATE_LINE.match(line)]
    if dated:
        return lines[max(0, dated[0] - 2):dated[0] + SECTION_LINES]
    return []


def crawl():
    snapshots, report = [], {"pages": {}, "stored": 0, "failures": []}
    last_hash = ""
    for page in PAGES:
        status, _, body, error = fetch(CDX.format(url=page), timeout=120)
        time.sleep(PAUSE)
        try:
            rows = json.loads(body.decode("utf-8", "replace")) if status == 200 and body else []
        except Exception:
            rows = []
        stamps = [row[0] for row in rows[1:] if row and row[0][:8].isdigit()]
        chosen = choose(stamps)
        report["pages"][page] = {"snapshots": len(stamps), "chosen": len(chosen), "cdx": status, "error": error[:80]}
        name = "main" if page.endswith("mechanism_en") else "news"
        for stamp in chosen:
            url = SNAPSHOT.format(stamp=stamp, url=page)
            status, headers, body, error = fetch(url, timeout=120, retries=3, pause=8)
            time.sleep(PAUSE)
            if status != 200 or not body:
                report["failures"].append(f"{stamp} {name} ({status} {error[:50]})")
                continue
            _, lines, _ = parse(decode(body, header(headers, "Content-Type")), page)
            part = section(lines)
            digest = hashlib.sha1("\n".join(part).encode("utf-8")).hexdigest()[:16]
            row = {"page": page, "stamp": stamp, "snapshot": f"https://web.archive.org/web/{stamp}/{page}", "lines": len(part), "hash": digest, "textPath": ""}
            if part and digest != last_hash:
                row["textPath"] = save_text(f"ec-latest/{name}-{stamp[:8]}.txt",
                                            [f"[주소] {page}", f"[보관 시각] {stamp}", f"[보관 주소] {row['snapshot']}", ""] + part)
                report["stored"] += 1
                last_hash = digest
            snapshots.append(row)
    save_index("ec-latest", snapshots, report)
    return report
