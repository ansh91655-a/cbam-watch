"""EU 공식 출처의 화면 글을 저장소에 남긴다. 정리한 글을 원문과 대조할 때 쓴다.

재이용이 허용된 EU 기관 화면만 다룬다. 그 밖의 출처는 여기서 글을 저장하지 않는다.
화면이 이용 조건(공공누리 1유형 등)을 스스로 밝힌 공공기관 게시글의 본문은 tools.collect.articles가 따로 받아 같은 폴더(items/)에 둔다.
"""
import pathlib
from urllib.parse import urlsplit

from tools.common.htmltext import decode, parse
from tools.common.net import fetch, header

PAGE_DIR = "collected/pages"
ITEM_LIMIT = 12
_fetched = 0


def source_path(code):
    return f"{PAGE_DIR}/{code}.txt"


def _write(path, lines):
    target = pathlib.Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")


def save_source_text(code, html, url):
    _, lines, rows = parse(html, url)
    table_lines = [" | ".join(cells) for cells in rows]
    _write(source_path(code), lines + (["", "[표의 행]"] + table_lines if table_lines else []))


def save_lines(item_id, lines):
    """주어진 줄들을 그 항목의 원문 글 파일로 남기고 경로를 돌려준다."""
    path = f"{PAGE_DIR}/items/{item_id}.txt"
    _write(path, lines)
    return path


def save_item_text(item):
    """새 링크가 가리키는 화면의 글을 받아 둔다. EU 기관의 HTML 화면만, 한 번 실행에 정해진 건수까지만."""
    global _fetched
    host = urlsplit(item["url"]).netloc
    if not host.endswith("europa.eu") or "/document/download/" in item["url"] or _fetched >= ITEM_LIMIT:
        return ""
    _fetched += 1
    status, headers, body, _ = fetch(item["url"])
    content_type = header(headers, "Content-Type")
    if status != 200 or "html" not in content_type.lower() or len(body) < 800:
        return ""
    _, lines, rows = parse(decode(body, content_type), item["url"])
    path = f"{PAGE_DIR}/items/{item['id']}.txt"
    _write(path, [f"[주소] {item['url']}", ""] + lines + ["", "[표의 행]"] + [" | ".join(cells) for cells in rows])
    return path
