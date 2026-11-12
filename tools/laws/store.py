"""법령 문단의 국문 번역을 두는 곳(data/laws-ko/<법령 번호>.json)을 읽고 쓴다.

번역은 원문 문단의 글자에서 만든 열쇠(key)에 붙는다. 문단의 자리가 아니라 글자에 붙으므로
- 법령이 고쳐져 통합본이 새로 나와도 글자가 그대로인 문단의 번역은 남고, 바뀐 문단만 번역이 없는 상태가 된다.
- 여러 법령에 똑같이 나오는 문단(맺음말, 표의 머리 글자)은 한 번만 옮기면 모든 곳에 실린다.
"""
import hashlib
import pathlib
import re

from tools.common.jsonio import read_json, today, write_json

FOLDER = "data/laws-ko"


def key(text):
    """문단의 열쇠. 띄어쓰기의 차이는 같은 문단으로 본다."""
    return hashlib.sha1(re.sub(r"\s+", " ", str(text)).strip().encode("utf-8")).hexdigest()[:12]


def path_of(act_id):
    return f"{FOLDER}/{act_id}.json"


def load(act_id):
    """한 법령의 번역: {열쇠: 국문}."""
    return dict((read_json(path_of(act_id), {}) or {}).get("blocks", {}))


def load_all():
    """모든 법령의 번역을 합친 것: {열쇠: 국문}. 같은 글자의 문단은 어느 법령에서 옮겼든 같은 번역을 쓴다."""
    found = {}
    for path in sorted(pathlib.Path(FOLDER).glob("*.json")):
        for block_key, text in ((read_json(path, {}) or {}).get("blocks", {})).items():
            found.setdefault(block_key, text)
    return found


def save(act_id, blocks, day=None):
    """한 법령의 번역을 쓴다. 열쇠 차례로 적어 바뀐 줄만 달라지게 한다."""
    write_json(path_of(act_id), {"act": act_id, "updated": day or today(), "blocks": dict(sorted(blocks.items()))})
