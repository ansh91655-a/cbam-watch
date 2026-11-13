"""정리 실행이 직접 연 출처의 확인 결과를 저장소에 적는다(collected/claude-status.json).

쓰는 법: python -m tools.run.claude_status council-cbam=ok "council-cbam=fail:검색 결과에 주소가 없음"
연속 실패 횟수와 마지막으로 읽은 시각을 이어서 적는다. 실행 확인(tools.run.health)이 이 파일을 읽는다.
출처 대장에서 직접 열람(collector가 claude)이 아닌 출처의 기록은 이때 지운다.
"""
import sys

from tools.common.jsonio import read_json, stamp, write_json

PATH = "collected/claude-status.json"
REGISTRY = "sources/registry.json"


def _active():
    """출처 대장에서 예약 실행이 직접 여는 출처의 code들. 대장을 읽지 못하면 빈 묶음이다."""
    sources = read_json(REGISTRY, {"sources": []}).get("sources", [])
    return {source["code"] for source in sources if source.get("collector") == "claude"}


def main(argv):
    tokens = [token for token in argv if "=" in token]
    if not tokens or any(token in ("-h", "--help") for token in argv):
        print(__doc__.strip())   # 적을 결과가 없으면 파일을 건드리지 않는다(확인 시각이 헛되이 바뀌지 않게)
        return 0 if argv and argv[0] in ("-h", "--help") else 1
    argv = tokens
    moment = stamp()
    book = read_json(PATH, {"sources": {}})
    sources = book.setdefault("sources", {})
    for token in argv:
        code, _, result = token.partition("=")
        code = code.strip()
        if not code or not result:
            continue
        before = sources.get(code, {})
        ok = result.strip().lower() == "ok"
        note = "" if ok else result.partition(":")[2].strip()[:120]
        sources[code] = {
            "code": code, "checkedAt": moment, "ok": ok, "note": note,
            "failCount": 0 if ok else int(before.get("failCount", 0) or 0) + 1,
            "lastOk": moment if ok else before.get("lastOk", ""),
        }
    active = _active()
    if active:  # 대장에서 직접 열람을 그만둔 출처의 옛 기록은 지운다(남아 있으면 상태 점검이 계속 알린다)
        book["sources"] = {code: row for code, row in sources.items() if code in active}
    book["checkedAt"] = moment
    write_json(PATH, book)
    print(f"직접 연 출처 {len(argv)}곳의 결과를 적음")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
