"""EU 집행위원회가 보내는 'CBAM Newsletter'의 보관함에서 지난 호를 모은다.

보관함 목록(쪽마다 열 호)에서 호의 날짜, 제목, 주소를 얻고, 호마다 화면을 받아 글로 남긴다.
"""
import re
import time

from tools.archive.store import SINCE, iso_from_numbers, save_index, save_text
from tools.common.htmltext import decode, parse
from tools.common.net import fetch, header

LIST = "https://ec.europa.eu/newsroom/taxud/newsletter-archives/view/service/9510?page={n}"
ISSUE = re.compile(r"^https://ec\.europa\.eu/newsroom/taxud/newsletter-archives/(\d+)$")
DATE = re.compile(r"^\d{2}/\d{2}/\d{4}$")
MAX_PAGES = 8
PAUSE = 1.5
CHROME_STARTS = ("skip to main content", "Newsroom", "Menu", "Close", "Back", "Previous items", "Search")


def issues_of(html, url):
    """보관함 목록의 한 쪽에서 (날짜, 제목, 주소)를 뽑는다. 날짜 줄 다음 줄이 그 호의 제목이다."""
    links, lines, _ = parse(html, url)
    address = {text.strip(): link for link, text in links if ISSUE.match(link)}
    found = []
    for index, line in enumerate(lines[:-1]):
        title = lines[index + 1].strip()
        if DATE.match(line.strip()) and title in address:
            found.append({"date": iso_from_numbers(line.strip()), "title": title, "url": address[title]})
    return found


def body_of(lines, title):
    """호 화면의 글에서 머리 메뉴를 떼고 본문만 남긴다. 제목이 처음 나오는 줄부터를 본문으로 본다."""
    start = next((index for index, line in enumerate(lines) if index > 0 and line.strip() == title), 0)
    return [line for line in lines[start:] if line.strip() and not line.strip().startswith(CHROME_STARTS)]


def crawl():
    seen, report = {}, {"listPages": 0, "issues": 0, "stored": 0, "failures": []}
    for number in range(1, MAX_PAGES + 1):
        status, headers, body, error = fetch(LIST.format(n=number))
        time.sleep(PAUSE)
        if status != 200 or not body:
            report["failures"].append(f"목록 {number}쪽 ({status} {error[:60]})")
            break
        found = issues_of(decode(body, header(headers, "Content-Type")), LIST.format(n=number))
        new = [issue for issue in found if issue["url"] not in seen]
        if not new:
            break
        report["listPages"] += 1
        for issue in new:
            seen[issue["url"]] = issue
    entries = sorted((issue for issue in seen.values() if issue["date"] >= SINCE), key=lambda issue: issue["date"], reverse=True)
    report["issues"] = len(entries)
    for issue in entries:
        status, headers, body, error = fetch(issue["url"])
        time.sleep(PAUSE)
        if status != 200 or not body:
            report["failures"].append(f"{issue['url']} ({status} {error[:60]})")
            issue["textPath"] = ""
            continue
        _, lines, _ = parse(decode(body, header(headers, "Content-Type")), issue["url"])
        number = ISSUE.match(issue["url"]).group(1)
        issue["textPath"] = save_text(f"ec-newsletter/{number}.txt", [f"[주소] {issue['url']}", f"[보낸 날] {issue['date']}", ""] + body_of(lines, issue["title"]))
        report["stored"] += 1
    save_index("ec-newsletter", entries, report)
    return report
