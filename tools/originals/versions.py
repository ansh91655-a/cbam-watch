"""문서의 판을 파일로 남기고, 두 판을 비교한다.

보관 기준
- 본문을 뽑을 수 있거나 흔한 문서 형식이고 크기가 KEEP_LIMIT 이하면 사본을 저장소에 둔다.
  사본의 자리는 originals/files/<문서 id>/<해시 앞 12자>/<원래 파일 이름>이다. 사이트의 원문 대장이 이 파일을 바로 내려받게 하므로
  내려받은 파일이 원래 이름을 갖도록 파일 이름을 그대로 둔다.
- 그 밖의 것(압축 파일, 아주 큰 파일)은 사본을 두지 않고 해시와 크기만 적는다. 바뀌었는지는 알 수 있다.
"""
import pathlib
import re

from tools.common.jsonio import today, write_json
from tools.common.net import sha256_hex
from tools.originals import diff, textify

KEEP_TYPES = {"pdf", "docx", "xlsx", "html", "htm", "txt", "doc", "xls", "xlsm", "ppt", "pptx", "csv", "json", "xml", "odt", "ods", "rtf"}
KEEP_LIMIT = 30 * 1024 * 1024
MAX_SAME_TEXT = 8


UNSAFE = re.compile(r'[\\/:*?"<>|#%\x00-\x1f]')
NAME_LIMIT = 140


def safe_name(filename):
    """파일 이름에서 경로나 주소에 쓸 수 없는 글자를 밑줄로 바꾼다. 너무 길면 확장자를 남기고 줄인다."""
    name = " ".join(UNSAFE.sub("_", str(filename)).split()).strip(". ") or "document"
    if len(name) > NAME_LIMIT and "." in name:
        stem, ext = name.rsplit(".", 1)
        name = stem[: NAME_LIMIT - len(ext) - 1].rstrip() + "." + ext
    return name[:NAME_LIMIT]


def file_path(doc, digest):
    return pathlib.Path(f"originals/files/{doc['id']}/{digest[:12]}/{safe_name(doc['filename'])}")


def suffix(filename):
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"


def keeps(filename, size):
    return suffix(filename) in KEEP_TYPES and size <= KEEP_LIMIT


def store(doc, body, moment):
    """새 판을 남기고 판 정보를 돌려준다. 보관하지 않는 형식이면 해시와 크기만 담는다."""
    digest = sha256_hex(body)
    version = {"sha256": digest, "date": today(moment), "bytes": len(body), "pages": 0, "file": "", "text": "", "chars": 0}
    if not keeps(doc["filename"], len(body)):
        version["kept"] = False
        return version
    short = digest[:12]
    path = file_path(doc, digest)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)
    text, pages = textify.extract(path)
    version.update({"file": str(path), "pages": pages})
    if text is not None:
        text_path = pathlib.Path(f"originals/text/{doc['id']}/{short}.txt")
        text_path.parent.mkdir(parents=True, exist_ok=True)
        text_path.write_text(text, encoding="utf-8")
        version.update({"text": str(text_path), "chars": len(text)})
    return version


def discard(version):
    """방금 남긴 판의 파일을 지운다(본문이 이전 판과 같아 새 판으로 치지 않을 때)."""
    for key in ("file", "text"):
        if version.get(key):
            pathlib.Path(version[key]).unlink(missing_ok=True)
    if version.get("file"):
        try:
            pathlib.Path(version["file"]).parent.rmdir()  # 해시 폴더가 비었으면 지운다
        except OSError:
            pass


def read_text(version):
    if not version or not version.get("text"):
        return None
    path = pathlib.Path(version["text"])
    return path.read_text(encoding="utf-8") if path.exists() else None


def compare(old_version, new_version):
    """두 판의 본문이 다 있으면 비교 결과를, 아니면 None을 돌려준다."""
    old_text, new_text = read_text(old_version), read_text(new_version)
    if old_text is None or new_text is None:
        return None
    return diff.compare(old_text, new_text)


def unchanged(result):
    stats = (result or {}).get("stats")
    return bool(stats) and stats["added"] + stats["removed"] + stats["changed"] == 0


def remember_same_text(version, digest):
    """본문은 같고 파일만 다른 판의 해시를 적어 둔다. 다음에 같은 파일을 받으면 바뀐 것으로 보지 않는다."""
    hashes = version.setdefault("sameTextHashes", [])
    if digest not in hashes:
        hashes.append(digest)
    del hashes[:-MAX_SAME_TEXT]


def known_hash(version, digest):
    return digest == version["sha256"] or digest in version.get("sameTextHashes", [])


def write_diff(doc_id, old_version, new_version, result):
    """비교 결과를 파일로 남기고 (경로, 건수)를 돌려준다."""
    result.update({"doc": doc_id, "from": old_version["sha256"][:12], "to": new_version["sha256"][:12], "fromDate": old_version["date"], "toDate": new_version["date"]})
    path = f"originals/diffs/{doc_id}/{old_version['sha256'][:12]}-{new_version['sha256'][:12]}.json"
    write_json(path, result)
    return path, result["stats"]
