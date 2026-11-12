"""규정 원문 화면에 함께 싣는 EU 집행위원회 안내 문서(가이던스, 질의응답)의 목록.

무엇을 싣는지는 sources/guides.json이 정한다(문서의 id, 국문 이름, 원문 대장에서 찾을 파일 이름의 앞머리, 번역하는 차례).
글은 원문 대장(originals/state.json)이 받아 둔 최신 판의 것을 쓴다. 문서가 새 판으로 바뀌면 그 판의 글을 쓰게 되고,
글자가 그대로인 문단의 번역은 남는다(tools.laws.store). 파일 이름이 바뀌어 찾지 못한 문서는 목록에서 빠지고 missing()이 알려 준다.
"""
import pathlib

from tools.common.jsonio import read_json

SOURCE = "sources/guides.json"
STATE = "originals/state.json"


def _latest(stored, prefix):
    """파일 이름이 prefix로 시작하고 글을 받아 둔 문서 가운데 가장 최근 것. 지금 화면에 걸려 있는 것을 먼저 친다."""
    found = [doc for doc in stored if str(doc.get("filename", "")).startswith(prefix) and doc.get("versions")
             and doc["versions"][-1].get("text") and pathlib.Path(doc["versions"][-1]["text"]).exists()]
    found.sort(key=lambda doc: (bool(doc.get("linked")), str(doc.get("lastSeen", "")), str(doc.get("firstSeen", ""))))
    return found[-1] if found else None


def entries():
    return (read_json(SOURCE, {}) or {}).get("documents", [])


def documents():
    """싣는 문서의 목록. 법령의 목록(tools.laws.catalog.acts)과 같은 꼴에 group, format, received, pages, turn을 더한 것이다."""
    stored = list(((read_json(STATE, {}) or {}).get("docs") or {}).values())
    found = []
    for entry in entries():
        doc = _latest(stored, entry["file"])
        if doc is None:
            continue
        version = doc["versions"][-1]
        found.append({"id": entry["id"], "celex": "", "name": entry["name"], "short": entry.get("short", entry["name"]), "official": entry.get("en", ""),
                      "url": doc.get("url", ""), "path": version["text"], "consolidated": "", "rule": "", "group": "guide", "format": "pdf",
                      "received": version.get("date", ""), "pages": version.get("pages", 0), "turn": entry.get("turn", 99)})
    return found


def missing():
    """목록에는 있는데 원문 대장에서 찾지 못한 문서의 이름들."""
    have = {doc["id"] for doc in documents()}
    return [entry["name"] for entry in entries() if entry["id"] not in have]
