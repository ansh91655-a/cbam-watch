"""자동으로 받지 못하는 문서를 사람이 받아 원문 대장에 넣는다.

EU 집행위원회의 문서 링크 가운데 몇은 자동 실행의 요청을 받아 주지 않는다(403). 그런 문서는 대장의 pending에 남아
'받지 못한 문서'로 보고된다. 사람이 브라우저로 받은 파일을 이 도구로 넣으면 다른 문서와 같은 꼴로 대장에 오른다
(사본, 뽑아 낸 본문, 판 정보). pending에서는 빠진다.

쓰는 법(저장소 맨 위에서)
  python3 -m tools.originals.supply --list
        받지 못한 문서의 번호, 실린 화면, 이름
  python3 -m tools.originals.supply <문서 번호> <파일> [--name <파일 이름>] [--url <주소>] [--no-copy <까닭>]
        그 문서의 파일을 넣는다. 이미 대장에 있는 문서면 새 판으로 넣는다(본문이 받아 둔 판과 같으면 넣지 않는다).

- --name: 대장에 적을 파일 이름. 주지 않으면 건넨 파일의 이름이다. 내려받은 파일이 원래 이름을 갖도록 그대로 둔다.
- --url: 문서가 올라온 주소. 주지 않으면 그 화면의 문서 주소 꼴(<사이트>/document/download/<번호>_en)로 적는다.
  다음 수집이 화면을 읽으면 화면에 걸린 주소로 고쳐진다.
- --no-copy <까닭>: 사본을 저장소에 두지 않고 본문만 받아 둔다. 문서 안에 EU의 것이 아닌 그림이 있다고 적혀 있어
  문서를 통째로 다시 싣기 어려울 때 쓴다. 원문 대장은 그 문서를 원래 올라온 곳으로 잇는다(사이트의 '바로 보기'가 없다).
  PDF면 사본을 지우기 전에 뜻 단위(originals/units: 문단의 글과 자리)를 읽어 둔다.
- 넣은 문서에는 supplied(넣은 날)를 적는다. 그런 문서는 자동 실행이 다시 받으려 하지 않는다(tools/originals/queue.py):
  받아 주지 않는 주소를 날마다 두드리지 않고, 이어진 실패를 접속 제한으로 잘못 보지 않게 하려는 것이다.
  그래서 같은 주소의 파일이 새 판으로 바뀌었는지는 스스로 알지 못한다. 화면의 링크가 사라지거나 새 링크가 생기는 것은 전과 같이 알린다.
- 처음 본 날부터 있던 문서(pending의 quiet)는 소식으로 내지 않는다. 그 뒤에 새로 걸린 문서를 넣을 때에만 소식 후보로 낸다.
"""
import argparse
import pathlib
import sys

from tools.collect import feed
from tools.common.jsonio import now_kst, read_json, stamp, today, write_json
from tools.common.net import sha256_hex
from tools.originals import queue, versions
from tools.originals.run import SOURCE_CODE, STATE_PATH

SITE = "https://taxation-customs.ec.europa.eu"


def _address(doc_id):
    return f"{SITE}/document/download/{doc_id}_en"


def _withhold(version, why):
    """사본을 지우고 본문만 남긴다. 판 정보에는 사본이 없다는 것과 그 까닭을 적는다.

    PDF면 지우기 전에 뜻 단위(originals/units)를 읽어 둔다. 사본이 없으면 나중에 다시 읽을 수 없기 때문이다.
    읽지 못해도 넣기는 계속한다(그 문서는 뽑아 낸 글을 줄 단위로 나눠 싣게 되고, 실행 확인이 단위 파일이 없다고 알린다).
    """
    path = pathlib.Path(version["file"])
    if path.suffix.lower() == ".pdf" and version.get("text"):
        try:
            from tools.pdfko import units   # PDF를 읽는 꾸러미는 여기서만 쓴다
            units.write(path, version["text"])
        except Exception as error:          # noqa: BLE001 - 어떤 까닭이든 단위만 없을 뿐이다
            version["unitsError"] = repr(error)[:160]
    path.unlink(missing_ok=True)
    try:
        path.parent.rmdir()          # 해시 폴더
        path.parent.parent.rmdir()   # 문서 폴더(다른 판의 사본이 있으면 남는다)
    except OSError:
        pass
    version.update({"file": "", "kept": False, "withheld": why})


def _counts(state):
    pending = state["pending"]
    state.update({"docCount": len(state["docs"]), "pendingCount": len(pending), "unreachableCount": len(queue.unreachable(pending)),
                  "unreachableNames": queue.names(pending)})


def add(doc_id, body, filename, url="", no_copy="", moment=None, state_path=STATE_PATH):
    """파일 하나를 넣고 (결과, 설명)을 돌려준다. 결과는 "added"(새 문서), "version"(새 판), "same"(받아 둔 판과 같음), "unknown"(모르는 번호),
    "unreadable"(본문을 뽑지 못해 --no-copy로는 넣을 수 없음)."""
    moment = moment or now_kst()
    state = read_json(state_path, {"docs": {}, "pending": {}})
    docs, pending = state.setdefault("docs", {}), state.setdefault("pending", {})
    entry = pending.get(doc_id)
    if doc_id in docs:
        doc, latest = docs[doc_id], docs[doc_id]["versions"][-1]
        if versions.known_hash(latest, sha256_hex(body)):
            return "same", "받아 둔 판과 같은 파일"
        doc["filename"] = filename
        version = versions.store(doc, body, moment)
        result = versions.compare(latest, version)
        if versions.unchanged(result):
            versions.discard(version)
            versions.remember_same_text(latest, version["sha256"])
            write_json(state_path, state)
            return "same", "파일은 다르지만 본문이 받아 둔 판과 같음"
        if no_copy and not version.get("text"):
            versions.discard(version)
            return "unreadable", "본문을 뽑지 못한 파일은 사본 없이 넣을 수 없음"
        diff_path, _ = versions.write_diff(doc_id, latest, version, result) if result else ("", None)
        version["diff"] = diff_path
        if no_copy:
            _withhold(version, no_copy)
        doc["versions"].append(version)
        doc.update({"supplied": today(moment), "lastChecked": stamp(moment)})
        doc.pop("lastError", None)
        _counts(state)
        write_json(state_path, state)
        return "version", f"새 판: {filename}"
    if entry is None:
        return "unknown", "받지 못한 문서의 번호가 아님(python3 -m tools.originals.supply --list)"
    doc = {"id": doc_id, "filename": filename, "label": entry.get("label", ""), "url": url or _address(doc_id), "lang": "en", "page": entry.get("page", ""),
           "firstSeen": entry.get("firstSeen") or today(moment), "lastSeen": today(moment), "lastChecked": stamp(moment), "linked": True,
           "versions": [], "replaces": "", "supplied": today(moment)}
    version = versions.store(doc, body, moment)
    if no_copy and not version.get("text"):
        versions.discard(version)
        return "unreadable", "본문을 뽑지 못한 파일은 사본 없이 넣을 수 없음"
    if no_copy:
        _withhold(version, no_copy)
    doc["versions"].append(version)
    docs[doc_id] = doc
    del pending[doc_id]
    _counts(state)
    write_json(state_path, state)
    if not entry.get("quiet"):   # 처음 본 날부터 있던 문서가 아니면 다른 새 문서처럼 소식 후보로 낸다
        item = {"id": feed.item_id(SOURCE_CODE, f"{doc_id}:new"), "source": SOURCE_CODE, "kind": "document", "change": "new-document", "doc": doc_id,
                "url": doc["url"], "text": f"새 문서: {filename}", "seenAt": stamp(moment), "textPath": version["text"]}
        feed.append(today(moment), [item], stamp(moment))
    kept = "본문만 받아 둠(사본 없음)" if no_copy else f"{version['bytes']:,}바이트"
    return "added", f"{doc['label'] or filename}: {version['pages']}쪽, 본문 {version['chars']:,}자, {kept}"


def listing(state_path=STATE_PATH):
    """받지 못한 문서의 줄들: [(번호, 실린 화면, 이름, 시도한 횟수)]"""
    pending = (read_json(state_path, {}) or {}).get("pending", {})
    return [(doc_id, entry.get("page", ""), str(entry.get("label") or entry.get("name") or "(이름 모름)"), int(entry.get("tries", 0) or 0)) for doc_id, entry in pending.items()]


def main(arguments):
    parser = argparse.ArgumentParser(prog="python3 -m tools.originals.supply")
    parser.add_argument("doc", nargs="?", help="문서 번호")
    parser.add_argument("file", nargs="?", help="받아 둔 파일")
    parser.add_argument("--name", default="", help="대장에 적을 파일 이름")
    parser.add_argument("--url", default="", help="문서가 올라온 주소")
    parser.add_argument("--no-copy", default="", metavar="까닭", help="사본을 두지 않고 본문만 받아 둔다")
    parser.add_argument("--list", action="store_true", help="받지 못한 문서를 보여 준다")
    args = parser.parse_args(arguments)
    if args.list or not args.doc:
        rows = listing()
        for doc_id, page, name, tries in rows:
            print(f"{doc_id}  {page:16s} {name}" + (f"  (시도 {tries}번)" if tries else ""))
        print(f"받지 못한 문서 {len(rows)}건")
        return 0
    if not args.file:
        parser.error("넣을 파일을 적어 주세요")
    path = pathlib.Path(args.file)
    if not path.is_file():
        print(f"파일이 없음: {path}")
        return 2
    outcome, said = add(args.doc.lower(), path.read_bytes(), args.name or path.name, url=args.url, no_copy=args.no_copy)
    print({"added": "넣음", "version": "새 판으로 넣음", "same": "넣지 않음", "unknown": "넣지 않음", "unreadable": "넣지 않음"}[outcome] + f": {said}")
    return 0 if outcome in ("added", "version", "same") else 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
