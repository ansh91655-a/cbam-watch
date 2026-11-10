"""EC 화면에서 내려받을 수 있는 문서 링크를 찾는다."""
import re
from urllib.parse import unquote

from tools.common.htmltext import decode, parse
from tools.common.net import fetch, header

# 주소 꼴: /document/download/<문서 번호>[_<언어>][?filename=<파일 이름>]
DOWNLOAD = re.compile(
    r"/document/download/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})(?:_([a-z]{2,3}))?(?:\?filename=([^&#]+))?", re.I)
LANGUAGE_RANK = {"en": 0, "": 1}  # 같은 문서가 여러 언어로 걸려 있으면 영어판을 고른다
MIN_PAGE = 800


def documents(html, page_url):
    """문서 목록을 돌려준다. 항목은 {id, lang, filename, url, label}이다. 파일 이름이 주소에 없으면 빈 글이다."""
    links, _, _ = parse(html, page_url)
    best = {}
    for url, text in links:
        match = DOWNLOAD.search(url)
        if not match:
            continue
        doc_id, lang, raw_name = match.group(1).lower(), (match.group(2) or "").lower(), match.group(3) or ""
        rank = LANGUAGE_RANK.get(lang, 2)
        if doc_id in best and best[doc_id][0] <= rank:
            continue
        filename = unquote(raw_name.replace("+", " ")).strip()
        best[doc_id] = (rank, {"id": doc_id, "lang": lang, "filename": filename, "url": url, "label": text[:200]})
    return [doc for _, doc in best.values()]


def scan(sources):
    """화면들을 읽어 (찾은 문서, 특이사항, 읽는 데 성공한 화면 코드)를 돌려준다. 같은 문서는 먼저 본 화면의 것으로 둔다.

    출처 설정의 skipDocuments(정규식 목록)에 파일 이름이 맞는 문서는 추적하지 않는다(예: 다른 언어로 옮긴 판).
    """
    found, notes, read_codes = {}, [], set()
    for source in sources:
        code, url = source["code"], source["url"]
        skip = [re.compile(pattern, re.I) for pattern in source.get("skipDocuments", [])]
        status, headers, body, error = fetch(url)
        if status != 200 or len(body) < MIN_PAGE:
            notes.append(f"{code}: 화면을 읽지 못함({status} {error[:80]})")
            continue
        read_codes.add(code)
        for doc in documents(decode(body, header(headers, "Content-Type")), url):
            if any(pattern.search(doc["filename"]) for pattern in skip):
                continue
            doc["page"] = code
            found.setdefault(doc["id"], doc)
    return found, notes, read_codes


def family(filename):
    """판이 바뀌어도 같은 문서로 볼 수 있게 이름에서 날짜와 판 표시를 뗀 열쇠."""
    name = filename.lower().rsplit(".", 1)[0]
    name = re.sub(r"\b(v|ver|version)\s*\d+(\.\d+)*\b", " ", name)
    name = re.sub(r"\b\d{1,2}[._-]\d{1,2}([._-]\d{2,4})?\b", " ", name)
    name = re.sub(r"\b(final|update|updated|clean|corrigendum)\b", " ", name)
    name = re.sub(r"[^a-z0-9가-힣]+", " ", name)
    return re.sub(r"\s+", " ", name).strip()
