"""EU 집행위원회 조세·관세총국의 소식 목록에서 CBAM 소식을 모은다.

목록 화면을 최신부터 거슬러 읽어 2025-01-01 이전이 나오면 멈춘다. 제목, 한 줄 소개, 주소에 CBAM이 든 소식과
사이트의 CBAM 낱말 찾기에 걸리는 소식을 고르고, 고른 소식의 본문 화면을 받아 글로 남긴다.
"""
import re
import time

from tools.archive.store import SINCE, iso_from_long, save_index, save_text
from tools.common.htmltext import decode, parse
from tools.common.net import fetch, header

LIST = "https://taxation-customs.ec.europa.eu/news_en?page={n}"
FOUND = "https://taxation-customs.ec.europa.eu/news_en?f%5B0%5D=oe_news_title%3Acbam&page={n}"
NEWS_URL = re.compile(r"^https://taxation-customs\.ec\.europa\.eu/news/[^?#]+_en$")
KEY = re.compile(r"cbam|carbon border", re.I)
SHOWING = re.compile(r"^Showing results (\d+) to (\d+)$")
TOTAL = re.compile(r"^News \((\d+)\)$")
MAX_PAGES = 80
PAUSE = 1.2


def entries_of(html, url):
    """목록 화면 하나에서 (소식 목록, 화면에 적힌 전체 건수, '몇 번째부터' 값)을 뽑는다."""
    links, lines, _ = parse(html, url)
    # 제목 줄과 글자가 같은 링크가 그 소식의 주소다. 소식 화면이 아니라 문서나 다른 사이트로 바로 가는 소식도 있다.
    by_title = {text: link for link, text in links}
    total = next((int(TOTAL.match(line).group(1)) for line in lines if TOTAL.match(line)), -1)
    first = next((int(SHOWING.match(line).group(1)) for line in lines if SHOWING.match(line)), -1)
    found = []
    for index, line in enumerate(lines):
        if line not in by_title or index < 1:
            continue
        date = iso_from_long(lines[index - 1])
        if not date:
            continue
        teaser = lines[index + 1] if index + 1 < len(lines) and "min read" not in lines[index + 1] else ""
        found.append({"date": date, "title": line, "teaser": teaser, "url": by_title[line], "type": lines[index - 2] if index >= 2 else ""})
    return found, total, first


def _page(template, number, expect_total_below=None):
    """목록의 한 쪽을 받는다. 서버가 다른 쪽을 돌려주는 일이 있어, 쪽 번호와 건수가 맞을 때까지 몇 번 다시 받는다."""
    for attempt in range(4):
        url = template.format(n=number) + (f"&r={attempt}" if attempt else "")
        status, headers, body, _ = fetch(url)
        time.sleep(PAUSE)
        if status != 200 or not body:
            continue
        found, total, first = entries_of(decode(body, header(headers, "Content-Type")), url)
        right_page = first in (number * 10, number * 10 + 1)
        right_list = expect_total_below is None or (0 <= total < expect_total_below)
        if found and right_page and right_list:
            return found, total
    return [], -1


def crawl():
    seen, report = {}, {"listPages": 0, "foundPages": 0, "listTotal": -1, "foundTotal": -1, "stoppedAt": "", "articles": 0, "articleFailures": []}
    # 1) 전체 목록을 거슬러 읽는다
    for number in range(MAX_PAGES):
        found, total = _page(LIST, number)
        if not found:
            report["stoppedAt"] = f"전체 목록 {number}쪽을 읽지 못함"
            break
        report["listPages"] += 1
        report["listTotal"] = total
        for entry in found:
            if entry["date"] >= SINCE and KEY.search(f"{entry['title']} {entry['teaser']} {entry['url']}"):
                seen.setdefault(entry["url"], {**entry, "via": "목록"})
        if min(entry["date"] for entry in found) < SINCE:
            report["stoppedAt"] = f"전체 목록 {number}쪽에서 {SINCE} 이전에 닿음"
            break
    # 2) 사이트의 낱말 찾기(cbam)에 걸리는 소식을 더한다
    for number in range(12):
        found, total = _page(FOUND, number, expect_total_below=300)
        if not found:
            break
        report["foundPages"] += 1
        report["foundTotal"] = total
        for entry in found:
            if entry["date"] >= SINCE:
                seen.setdefault(entry["url"], {**entry, "via": "낱말 찾기"})
        if min(entry["date"] for entry in found) < SINCE:
            break
    # 3) 고른 소식의 본문을 받아 둔다
    entries = sorted(seen.values(), key=lambda entry: (entry["date"], entry["url"]), reverse=True)
    for entry in entries:
        if not NEWS_URL.match(entry["url"]):
            entry["textPath"] = ""  # 문서나 다른 사이트로 가는 소식: 목록의 한 줄 소개가 원문이다
            continue
        status, headers, body, error = fetch(entry["url"])
        time.sleep(PAUSE)
        content_type = header(headers, "Content-Type")
        if status != 200 or "html" not in content_type.lower() or len(body) < 800:
            report["articleFailures"].append(f"{entry['url']} ({status} {error[:60]})")
            entry["textPath"] = ""
            continue
        _, lines, rows = parse(decode(body, content_type), entry["url"])
        name = entry["url"].rsplit("/", 1)[-1]
        entry["textPath"] = save_text(f"ec-news/{name}.txt", [f"[주소] {entry['url']}", ""] + lines + (["", "[표의 행]"] + [" | ".join(cells) for cells in rows] if rows else []))
        entry["mentions"] = len(KEY.findall("\n".join(lines)))
        report["articles"] += 1
    save_index("ec-news", entries, report)
    return report
