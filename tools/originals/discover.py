"""EC 화면에서 내려받을 수 있는 문서 링크를 찾는다."""
import re
from urllib.parse import unquote

from tools.common.htmltext import parse

DOWNLOAD = re.compile(r"/document/download/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})_(\w+)\?filename=([^&#]+)")


def documents(html, page_url):
    """문서 목록을 돌려준다. 항목은 {id, lang, filename, url, label}이다."""
    links, _, _ = parse(html, page_url)
    found = {}
    for url, text in links:
        match = DOWNLOAD.search(url)
        if not match:
            continue
        doc_id, lang, raw_name = match.groups()
        filename = unquote(raw_name.replace("+", " ")).strip()
        found[doc_id] = {"id": doc_id, "lang": lang, "filename": filename, "url": url, "label": text[:200]}
    return list(found.values())


def family(filename):
    """판이 바뀌어도 같은 문서로 볼 수 있게 이름에서 날짜와 판 표시를 뗀 열쇠."""
    name = filename.lower().rsplit(".", 1)[0]
    name = re.sub(r"\b(v|ver|version)\s*\d+(\.\d+)*\b", " ", name)
    name = re.sub(r"\b\d{1,2}[._-]\d{1,2}([._-]\d{2,4})?\b", " ", name)
    name = re.sub(r"\b(final|update|updated|clean|corrigendum)\b", " ", name)
    name = re.sub(r"[^a-z0-9가-힣]+", " ", name)
    return re.sub(r"\s+", " ", name).strip()
