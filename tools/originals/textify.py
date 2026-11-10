"""원문 파일에서 본문을 뽑는다. PDF는 pdftotext, 워드와 엑셀은 압축 안의 XML에서, HTML은 보이는 글자만 읽는다."""
import pathlib
import re
import subprocess
import zipfile

from tools.common.htmltext import decode, parse


def _pdf(path):
    done = subprocess.run(["pdftotext", str(path), "-"], capture_output=True, timeout=300)
    if done.returncode != 0:
        return None
    return done.stdout.decode("utf-8", "replace")


def pdf_pages(path):
    try:
        done = subprocess.run(["pdfinfo", str(path)], capture_output=True, timeout=60)
        match = re.search(r"^Pages:\s+(\d+)", done.stdout.decode("utf-8", "replace"), re.M)
        return int(match.group(1)) if match else 0
    except Exception:
        return 0


def _zip_xml(path, pattern, paragraph_tag):
    """docx와 xlsx 안의 XML에서 글자를 뽑는다. 문단 태그가 끝날 때 줄을 바꾼다."""
    chunks = []
    with zipfile.ZipFile(path) as archive:
        for name in sorted(archive.namelist()):
            if not re.search(pattern, name):
                continue
            xml = archive.read(name).decode("utf-8", "replace")
            xml = re.sub(rf"</{paragraph_tag}>", "\n", xml)
            text = re.sub(r"<[^>]+>", "", xml)
            for entity, char in (("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"), ("&quot;", '"'), ("&apos;", "'")):
                text = text.replace(entity, char)
            chunks.append(text)
    return "\n".join(chunks)


def _html(path):
    """보이는 글의 줄을 문단으로 삼는다(줄 사이를 한 줄 띄워 비교 단위가 되게 한다)."""
    _, lines, _ = parse(decode(pathlib.Path(path).read_bytes()), "https://example.invalid/")
    return "\n\n".join(lines)


def extract(path):
    """(본문 글자 또는 None, 쪽수)를 돌려준다. 뽑지 못하는 형식이면 본문은 None이다."""
    suffix = str(path).lower().rsplit(".", 1)[-1]
    try:
        if suffix == "pdf":
            return _pdf(path), pdf_pages(path)
        if suffix == "docx":
            return _zip_xml(path, r"^word/document\.xml$", "w:p"), 0
        if suffix == "xlsx":
            return _zip_xml(path, r"^xl/sharedStrings\.xml$", "si"), 0
        if suffix in ("html", "htm"):
            return _html(path), 0
        if suffix == "txt":
            return decode(pathlib.Path(path).read_bytes()), 0
    except Exception:
        return None, 0
    return None, 0
