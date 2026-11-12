"""재이용 조건을 밝힌 공공기관 게시글의 본문을 받아 저장소에 둔다.

출처 목록 화면에서 새로 보인 글(kind가 link인 수집 기록)은 제목과 주소뿐이다. 예약 실행은 그 주소를 웹 읽기로 열 수 없어
(검색 결과에 나온 주소만 열린다) 제목만으로 소식을 쓰게 된다. 그래서 이 프로그램이 본문을 받아 두고, 수집 기록의 그 줄에
받은 글의 경로(textPath)를 적어 준다. 예약 실행은 그 글을 읽고 요약을 쓰고, 검증 실행은 그 글과 대조한다.

받는 글
- 출처 대장에서 articles를 가진 출처의 글만 받는다. articles.license는 화면에 적혀 있어야 하는 이용 조건의 글귀다
  (예: "공공누리 1유형"). 그 글귀는 받은 글의 화면에서 먼저 찾고, 없으면 그 출처의 게시판 화면(출처의 url)에서 찾는다
  (게시판 화면에 "이 게시판의 글은 … 조건에 따라 누구나 이용할 수 있습니다"라고 한 번만 적어 두는 사이트가 있다).
  어느 쪽에도 없으면 글을 저장하지 않는다. 저장소는 공개이므로, 출처를 밝히면 누구나 쓸 수 있다고 화면이 스스로 밝힌 글만 둔다.
- 그 출처와 같은 사이트의 주소만 연다. 첨부 파일은 받지 않는다. robots.txt가 막은 주소는 열지 않는다(tools.common.net).
- 한 번 실행에 LIMIT건까지, 한 글은 MAX_TRIES번까지 해 본다. 지난 DAYS일의 수집 기록을 본다(그날 못 받은 글을 다음 날 다시 해 본다).

쓰는 법: python -m tools.collect.articles [--days 7] [--limit 8]
받은 글은 collected/pages/items/<기록 id>.txt, 해 본 기록은 collected/articles.json 에 남는다.
"""
import argparse
import datetime
import pathlib
import sys
import time
from urllib.parse import urlsplit

from tools.collect import article_text, registry
from tools.collect.feed import FEED_DIR
from tools.collect.pages import PAGE_DIR
from tools.common.htmltext import decode, parse
from tools.common.jsonio import now_kst, read_json, stamp, write_json
from tools.common.net import fetch, header

STATE = "collected/articles.json"
DAYS = 7
LIMIT = 8
MAX_TRIES = 3
PAUSE_SECONDS = 2
KEEP_DAYS = 45       # 해 본 기록을 이만큼만 남긴다
MIN_BYTES = 800
FILE_ENDINGS = (".pdf", ".hwp", ".hwpx", ".zip", ".xlsx", ".xls", ".docx", ".doc", ".pptx", ".jpg", ".jpeg", ".png")

SAVED = "받음"
NO_LICENSE = "이용 조건 표시를 찾지 못함"
TOO_SHORT = "본문이 너무 짧음"


def targets(sources):
    """본문을 받기로 한 출처: {code: 출처}. 이용 조건의 글귀가 적혀 있지 않은 출처는 받지 않는다."""
    return {source["code"]: source for source in sources
            if source.get("collector") == "github" and (source.get("articles") or {}).get("license")}


def text_path(item_id):
    return f"{PAGE_DIR}/items/{item_id}.txt"


def same_site(url, source):
    return bool(url) and urlsplit(url).netloc == urlsplit(source.get("url", "")).netloc


def is_file(url):
    path = urlsplit(url).path.lower()
    return path.endswith(FILE_ENDINGS) or "/attach/" in path or "/download" in path


def wanted(row, sources, tried):
    """이 수집 기록의 글을 받아야 하는가."""
    source = sources.get(row.get("source"))
    if not source or row.get("kind") != "link":
        return False
    if row.get("textPath") and pathlib.Path(row["textPath"]).exists():
        return False
    if not same_site(row.get("url", ""), source) or is_file(row["url"]):
        return False
    return int((tried.get(row["id"]) or {}).get("tries", 0)) < MAX_TRIES


def _page_lines(url, fetcher):
    """화면을 받아 보이는 글의 줄들을 돌려준다. (줄들 또는 None, 받지 못한 까닭)"""
    status, headers, body, error = fetcher(url)
    content_type = header(headers, "Content-Type")
    if status != 200:
        return None, (error or f"열리지 않음(상태 {status})")[:120]
    if "html" not in content_type.lower():
        return None, f"HTML이 아님({content_type[:40]})"
    if len(body) < MIN_BYTES:
        return None, f"본문 {len(body)}바이트"
    return parse(decode(body, content_type), url)[1], ""


def board_terms(source, fetcher, seen):
    """그 출처의 게시판 화면에 적힌 이용 조건의 줄. 한 번 실행에 출처마다 한 번만 받는다(seen에 기억한다)."""
    code = source["code"]
    if code not in seen:
        lines, _ = _page_lines(source["url"], fetcher)
        seen[code] = article_text.license_line(lines or [], (source.get("articles") or {}).get("license", []))
    return seen[code]


def compose(row, source, lines, moment, board=""):
    """받은 화면의 줄들로 저장할 글을 만든다. (저장할 줄들, 결과 글, 본문 줄 수)를 돌려준다. 저장하지 않을 때 줄들은 None이다.

    board는 그 출처의 게시판 화면에 적힌 이용 조건의 줄이다(글의 화면에 그 글귀가 없을 때 쓴다).
    """
    rules = source.get("articles") or {}
    shown = article_text.license_line(lines, rules.get("license", []))
    terms = shown or (f"{board} (게시판 화면 {source['url']} 에 적힌 글)" if board else "")
    if not terms:
        return None, NO_LICENSE, 0
    kept, found = article_text.body(lines, row.get("text", ""), list(rules.get("stop", [])) + list(rules.get("license", [])))
    if not article_text.long_enough(kept):
        return None, TOO_SHORT, len(kept)
    head = [f"[주소] {row['url']}", f"[출처] {source.get('name', source['code'])}", f"[이용 조건] {terms}", f"[받은 때] {stamp(moment)}"]
    if not found:
        head.append("[알림] 화면에서 제목이 적힌 줄을 찾지 못해 화면의 글을 처음부터 실었다")
    return head + [""] + kept, SAVED, len(kept)


def take(row, source, moment, fetcher=fetch, seen=None):
    """글 하나를 받아 저장한다. {"path": 저장한 경로 또는 빈 글, "result": 결과 글, "lines": 본문 줄 수, "hints": 화면의 저작권 줄}을 돌려준다."""
    lines, why = _page_lines(row["url"], fetcher)
    if lines is None:
        return {"path": "", "result": why, "lines": 0, "hints": []}
    rules = source.get("articles") or {}
    on_page = article_text.license_line(lines, rules.get("license", []))
    board = "" if on_page else board_terms(source, fetcher, seen if seen is not None else {})
    text, result, count = compose(row, source, lines, moment, board)
    if text is None:
        return {"path": "", "result": result, "lines": count, "hints": article_text.terms_hints(lines) if result == NO_LICENSE else []}
    path = pathlib.Path(text_path(row["id"]))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(text) + "\n", encoding="utf-8")
    return {"path": str(path), "result": result, "lines": count, "hints": []}


def _feed_paths(days, moment):
    day = moment.date()
    return [f"{FEED_DIR}/{(day - datetime.timedelta(days=back)).isoformat()}.json" for back in range(days - 1, -1, -1)]


def _prune(tried, moment):
    oldest = (moment - datetime.timedelta(days=KEEP_DAYS)).isoformat(timespec="seconds")
    return {key: row for key, row in tried.items() if str(row.get("at", "")) >= oldest}


def fill(days=DAYS, limit=LIMIT, moment=None, fetcher=fetch, pause=PAUSE_SECONDS):
    """지난 days일의 수집 기록에서 본문이 없는 글을 받아 채운다. 한 일을 요약한 값을 돌려준다."""
    moment = moment or now_kst()
    sources = targets(registry.load()[0])
    book = read_json(STATE, {"items": {}}) or {"items": {}}
    tried = book.get("items", {})
    saved, failed, left = [], [], 0
    boards = {}  # 출처마다 게시판 화면의 이용 조건을 한 번만 본다
    if sources:
        for path in _feed_paths(days, moment):
            feed = read_json(path, None)
            if not feed:
                continue
            changed = False
            for row in feed.get("items", []):
                if not wanted(row, sources, tried):
                    continue
                if len(saved) + len(failed) >= limit:
                    left += 1
                    continue
                if saved or failed:
                    time.sleep(pause)
                got = take(row, sources[row["source"]], moment, fetcher, boards)
                before = tried.get(row["id"]) or {}
                tried[row["id"]] = {"source": row["source"], "url": row["url"], "tries": int(before.get("tries", 0)) + 1,
                                    "result": got["result"], "lines": got["lines"], "at": stamp(moment)}
                if got["hints"]:
                    tried[row["id"]]["hints"] = got["hints"]
                if got["path"]:
                    row["textPath"] = got["path"]
                    changed = True
                    saved.append(row["id"])
                else:
                    failed.append(row["id"])
            if changed:
                write_json(path, feed)
    book = {"checkedAt": stamp(moment), "sources": sorted(sources), "items": _prune(tried, moment)}
    write_json(STATE, book)
    return {"sources": sorted(sources), "saved": saved, "failed": failed, "left": left}


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=DAYS)
    parser.add_argument("--limit", type=int, default=LIMIT)
    args = parser.parse_args(argv)
    done = fill(args.days, args.limit)
    tried = (read_json(STATE, {}) or {}).get("items", {})
    for item_id in done["saved"] + done["failed"]:
        row = tried.get(item_id, {})
        print(f"  {item_id} [{row.get('source', '')}] {row.get('result', '')} {row.get('lines', 0)}줄")
    print(f"본문 받기: 출처 {len(done['sources'])}곳, 받은 글 {len(done['saved'])}건, 받지 못한 글 {len(done['failed'])}건, 다음으로 미룬 글 {done['left']}건")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
