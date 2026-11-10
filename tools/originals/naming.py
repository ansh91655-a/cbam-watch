"""내려받은 문서의 파일 이름을 정한다. 주소에 이름이 없으면 응답 머리글에서 찾는다."""
import re
from urllib.parse import unquote

from tools.common.net import header

BY_TYPE = [
    ("pdf", ".pdf"), ("html", ".html"), ("zip", ".zip"), ("spreadsheetml", ".xlsx"), ("wordprocessingml", ".docx"),
    ("presentationml", ".pptx"), ("msword", ".doc"), ("ms-excel", ".xls"), ("csv", ".csv"), ("json", ".json"), ("plain", ".txt"),
]
MAX_NAME = 150


def _clean(name):
    name = re.sub(r"[\\/\x00-\x1f]+", " ", name)
    return re.sub(r"\s+", " ", name).strip()[:MAX_NAME]


def _from_disposition(value):
    extended = re.search(r"filename\*\s*=\s*[\w-]+''([^;]+)", value, re.I)
    if extended:
        return unquote(extended.group(1))
    plain = re.search(r'filename\s*=\s*"?([^";]+)"?', value, re.I)
    if not plain:
        return ""
    name = plain.group(1)
    try:  # 머리글은 latin-1로 읽히므로 UTF-8로 온 이름을 되살린다
        return name.encode("latin-1").decode("utf-8")
    except Exception:
        return name


def choose(url_name, headers, doc_id):
    """주소의 이름, 머리글의 이름, 내용 형식에서 짐작한 이름의 순서로 고른다."""
    name = _clean(url_name) or _clean(_from_disposition(header(headers, "Content-Disposition")))
    if name:
        return name
    content_type = header(headers, "Content-Type").lower()
    suffix = next((ext for mark, ext in BY_TYPE if mark in content_type), ".bin")
    return f"{doc_id[:8]}{suffix}"
