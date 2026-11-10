"""국내 기관 게시판에서 CBAM 관련 게시물의 제목, 날짜, 주소를 모은다. 본문은 저장하지 않는다.

게시판마다 쪽을 넘기는 방법이 달라서 게시판별 함수를 따로 둔다. 찾지 못한 게시판은 report에 사유를 적는다.
"""
import json
import re
import time
import urllib.parse

from tools.archive.store import SINCE, iso_from_numbers, save_index
from tools.common.htmltext import decode, parse
from tools.common.net import fetch, header

KEY = re.compile(r"CBAM|탄소국경|탄소 국경", re.I)
PAUSE = 1.2
FORM = {"Content-Type": "application/x-www-form-urlencoded"}


def _get(url, data=None):
    status, headers, body, error = fetch(url, headers=FORM if data else None, method="POST" if data else "GET",
                                         data=urllib.parse.urlencode(data).encode("utf-8") if data else None)
    time.sleep(PAUSE)
    if status != 200 or not body:
        return None, f"{status} {error[:60]}"
    return decode(body, header(headers, "Content-Type")), ""


def table_entries(html, url, title_column, date_column, link_pattern=None):
    """게시판 표에서 (제목, 날짜, 주소)를 뽑는다. 주소는 제목과 글자가 맞는 링크에서 찾고, 없으면 게시판 주소를 쓴다."""
    links, _, rows = parse(html, url)
    candidates = [(link, text) for link, text in links if link_pattern is None or link_pattern.search(link)]
    found = []
    for cells in rows:
        if len(cells) <= max(title_column, date_column):
            continue
        date = iso_from_numbers(cells[date_column])
        title = re.sub(r"\s*(새글|새 글|NEW|New)\s*$", "", cells[title_column]).strip()
        if not date or len(title) < 4:
            continue
        link = next((link for link, text in candidates if title[:30] in text), url)
        found.append({"date": date, "title": title, "url": link, "cells": cells[:8]})
    return found


def keco():
    """한국환경공단 CBAM 헬프데스크 게시판. 모든 글이 CBAM에 관한 것이다."""
    base = "https://www.keco.or.kr/web/lay1/bbs/S1T165C1421/A/279/list.do"
    entries, pages = {}, 0
    for number in range(1, 16):
        html, error = _get(f"{base}?cpage={number}&rows=10")
        if html is None:
            return list(entries.values()), {"pages": pages, "error": error}
        found = table_entries(html, base, 1, 4, re.compile(r"view\.do\?article_seq="))
        new = 0
        for entry in found:
            match = re.search(r"article_seq=(\d+)", entry["url"])
            entry["url"] = f"https://www.keco.or.kr/web/lay1/bbs/S1T165C1421/A/279/view.do?article_seq={match.group(1)}" if match else base
            key = entry["url"] if match else f"{entry['date']}|{entry['title']}"
            if key not in entries:
                entries[key] = entry
                new += 1
        pages += 1
        if not new or min(entry["date"] for entry in found) < SINCE:
            break
    return list(entries.values()), {"pages": pages}


def kosmes():
    """중소벤처기업진흥공단 ESG 통합플랫폼 공지사항. CBAM이 제목에 든 글만 고른다."""
    base = "https://kdoctor.kosmes.or.kr/esgplatform/board/board13.do"
    entries, pages = {}, 0
    for number in range(1, 16):
        html, error = _get(base, {"currentPage": number, "srchKey": "", "srchWord": ""})
        if html is None:
            return list(entries.values()), {"pages": pages, "error": error}
        found = table_entries(html, base, 1, 2)
        new = 0
        for entry in found:
            key = f"{entry['date']}|{entry['title']}"
            if key not in entries:
                entries[key] = entry
                new += 1
        pages += 1
        if not new or min(entry["date"] for entry in found) < SINCE:
            break
    return [entry for entry in entries.values() if KEY.search(entry["title"])], {"pages": pages, "all": len(entries)}


def motir():
    """산업통상부 보도·참고자료. 게시판의 낱말 찾기로 CBAM 관련 글을 찾는다."""
    base = "https://www.motir.go.kr/kor/article/ATCL3f49a5a8c"
    entries, report = {}, {}
    for word in ("탄소국경", "CBAM"):
        pages = 0
        for number in range(1, 13):
            query = urllib.parse.urlencode({"mno": "", "pageIndex": number, "rowPageC": 0, "displayAuthor": "", "schClear": "", "startDtD": "", "endDtD": "",
                                            "searchCondition": "1", "searchKeyword": word})
            html, error = _get(f"{base}?{query}")
            if html is None:
                report[word] = {"pages": pages, "error": error}
                break
            found = table_entries(html, base, 2, 4, re.compile(r"/view"))
            new = 0
            for entry in found:
                match = re.search(r"/ATCL3f49a5a8c/(\d+)/view", entry["url"])
                entry["url"] = f"{base}/{match.group(1)}/view" if match else base
                if entry["url"] not in entries:
                    entries[entry["url"]] = entry
                    new += 1
            pages += 1
            report[word] = {"pages": pages, "lastPageRows": len(found)}
            if not new or min(entry["date"] for entry in found) < SINCE:
                break
    # 낱말 찾기가 듣지 않으면 관계없는 글이 섞이므로 제목에 낱말이 든 것만 남긴다
    kept = [entry for entry in entries.values() if KEY.search(entry["title"])]
    report["all"] = len(entries)
    return kept, report


def moj():
    """법무부 해외규제 모니터링. CBAM이 제목에 든 글만 고른다."""
    base = "https://www.moj.go.kr/bbs/moj/177/artclList.do"
    entries, pages = {}, 0
    for number in range(1, 6):
        html, error = _get(base, {"layout": "", "page": number, "srchColumn": "", "srchWrd": "", "bbsClSeq": "", "bbsOpenWrdSeq": "",
                                  "rgsBgndeStr": "", "rgsEnddeStr": "", "isViewMine": "false"})
        if html is None:
            return list(entries.values()), {"pages": pages, "error": error}
        found = table_entries(html, base, 1, 4, re.compile(r"artclView\.do"))
        new = 0
        for entry in found:
            key = f"{entry['date']}|{entry['title']}"
            if key not in entries:
                entries[key] = entry
                new += 1
        pages += 1
        if not new:
            break
    return [entry for entry in entries.values() if KEY.search(entry["title"])], {"pages": pages, "all": len(entries)}


def compass():
    """국제환경규제 기업지원센터(COMPASS)의 EU CBAM 헬프데스크 자료실. 목록을 자료(JSON)로 준다."""
    base = "https://www.compass.or.kr/eucbam/data/list"
    query = urllib.parse.urlencode({"receiveCnt": 0, "requestCnt": 300, "orderName": "", "orderDir": "", "searchKey": "", "searchKeywd": ""})
    status, _, body, error = fetch(f"https://www.compass.or.kr/eucbam/data/euDataList?{query}", headers={"Accept": "application/json", "X-Requested-With": "XMLHttpRequest"})
    if status != 200 or not body:
        return [], {"error": f"{status} {error[:60]}"}
    try:
        rows = json.loads(body.decode("utf-8", "replace")).get("list") or []
    except Exception:
        return [], {"error": "자료를 풀지 못함"}
    found = []
    for row in rows:
        date = _compass_date(row.get("rdate"))
        if date and row.get("title"):
            found.append({"date": date, "title": str(row["title"]).strip(), "url": base, "cells": [str(row.get("originNm") or "")]})
    return found, {"rows": len(rows)}


def _compass_date(value):
    """날짜 값이 글이면 앞의 열 글자를, 수이면 1970년부터의 밀리초로 보고 날짜로 바꾼다(한국 시각)."""
    if isinstance(value, (int, float)):
        import datetime
        return (datetime.datetime.fromtimestamp(value / 1000, datetime.timezone.utc) + datetime.timedelta(hours=9)).date().isoformat()
    return iso_from_numbers(str(value or "")[:10])


BOARDS = [("keco-cbam", keco), ("kosmes-esg", kosmes), ("motir", motir), ("moj", moj), ("compass", compass)]


def crawl():
    summary = {}
    for code, reader in BOARDS:
        try:
            found, report = reader()
        except Exception as error:  # 한 게시판이 실패해도 나머지는 계속한다
            found, report = [], {"error": f"{type(error).__name__}: {error}"[:160]}
        kept = sorted((entry for entry in found if entry["date"] >= SINCE), key=lambda entry: entry["date"], reverse=True)
        report.update({"found": len(found), "kept": len(kept)})
        save_index(f"kr-{code}", kept, report)
        summary[code] = report
    return summary
