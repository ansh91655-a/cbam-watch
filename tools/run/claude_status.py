"""정리 실행이 직접 연 출처의 확인 결과를 저장소에 적는다(collected/claude-status.json).

쓰는 법: python -m tools.run.claude_status council-cbam=ok ep-train=ok "op-europa=fail:403으로 막힘"
연속 실패 횟수와 마지막으로 읽은 시각을 이어서 적는다. 사이트의 출처 화면과 실행 확인이 이 파일을 읽는다.
"""
import sys

from tools.common.jsonio import read_json, stamp, write_json

PATH = "collected/claude-status.json"


def main(argv):
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
    book["checkedAt"] = moment
    write_json(PATH, book)
    print(f"직접 연 출처 {len(argv)}곳의 결과를 적음")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
