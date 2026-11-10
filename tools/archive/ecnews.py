"""EU 집행위원회 조세·관세총국의 소식에서 CBAM 소식을 모은다.

소식 목록 화면은 쪽을 넘기는 주소를 자주 무시하고 첫 쪽을 돌려주므로 쓰지 않는다. 대신 사이트 지도(sitemap.xml)에서
소식 화면의 주소를 모두 얻는다. 소식 주소는 '-2026-09-30_en'처럼 게시일로 끝나므로, 2025-01-01부터의 소식 화면을
하나씩 받아 본문(제목, 한 줄 소개, 글)에 CBAM이 나오는 것만 남긴다. 메뉴에 있는 'CBAM'은 세지 않는다.
"""
import re
import time

from tools.archive.store import SINCE, iso_from_long, save_index, save_text
from tools.common.htmltext import decode, parse
from tools.common.net import fetch, header

SITEMAP = "https://taxation-customs.ec.europa.eu/sitemap.xml"
NEWS_LOC = re.compile(r"<loc>(https://taxation-customs\.ec\.europa\.eu/news/[^<]+?-(\d{4}-\d{2}-\d{2})_en)</loc>")
KEY = re.compile(r"cbam|carbon border", re.I)
SLUG_KEY = re.compile(r"cbam|carbon-border", re.I)
SITE_SUFFIX = " - Taxation and Customs Union"
END_MARKS = ("Publication date", "Share this page")
PAUSE = 1.0


def article(lines):
    """소식 화면의 글에서 본문만 잘라 (제목, 본문 줄)을 돌려준다. 본문은 제목 줄부터 'Publication date' 앞까지다."""
    if not lines:
        return "", []
    title = lines[0].split(SITE_SUFFIX)[0].strip()
    end = next((index for index, line in enumerate(lines) if line.strip() in END_MARKS and index > 5), len(lines))
    starts = [index for index, line in enumerate(lines[:end]) if line.strip() == title and index > 0]
    if starts:
        return title, lines[starts[-1]:end]
    # 제목 줄을 찾지 못하면 날짜 줄 앞의 세 줄부터 본문으로 본다
    dated = next((index for index, line in enumerate(lines[:end]) if iso_from_long(line)), -1)
    return title, (lines[max(0, dated - 3):end] if dated >= 0 else [])


def crawl(deadline=None):
    report = {"sitemap": 0, "newsSince": 0, "fetched": 0, "kept": 0, "failures": [], "stoppedEarly": False}
    status, _, body, error = fetch(SITEMAP, timeout=120)
    if status != 200 or not body:
        report["error"] = f"사이트 지도를 받지 못함({status} {error[:60]})"
        return report
    found = NEWS_LOC.findall(body.decode("utf-8", "replace"))
    report["sitemap"] = len(found)
    wanted = sorted({(date, url) for url, date in found if date >= SINCE}, reverse=True)
    report["newsSince"] = len(wanted)
    entries = []
    for date, url in wanted:
        if deadline is not None and time.monotonic() > deadline:
            report["stoppedEarly"] = True
            break
        status, headers, body, error = fetch(url)
        time.sleep(PAUSE)
        content_type = header(headers, "Content-Type")
        if status != 200 or "html" not in content_type.lower() or len(body) < 800:
            report["failures"].append(f"{url} ({status} {error[:60]})")
            continue
        report["fetched"] += 1
        _, lines, _ = parse(decode(body, content_type), url)
        title, text = article(lines)
        mentions = len(KEY.findall("\n".join(text)))
        if not text or (not mentions and not SLUG_KEY.search(url)):
            continue
        name = url.rsplit("/", 1)[-1]
        entries.append({"date": date, "title": title, "teaser": text[1] if len(text) > 1 else "", "url": url, "mentions": mentions, "lines": len(text),
                        "textPath": save_text(f"ec-news/{name}.txt", [f"[주소] {url}", ""] + text)})
    report["kept"] = len(entries)
    save_index("ec-news", entries, report)
    return report
