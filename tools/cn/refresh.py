"""CBAM 규정의 새 통합본이 나오면 본문을 다시 받아 품목 코드 조회 자료(data/cn.json)를 다시 만든다. 날마다의 수집이 돌린다.

쓰는 법: python -m tools.cn.refresh
- 새 통합본이 나왔는지는 EU 법령 데이터베이스의 연관 문서 기록(collected/archive/eur-lex-related.json)에서 안다.
  날마다의 수집이 이 기록을 먼저 갱신한 뒤에 이 프로그램을 돌린다.
- 새 본문을 EU 출판국 자료 창구에서 받아 부속서를 읽고, 확인(tools.cn.build의 problems)에 걸리지 않을 때만 받아 둔 본문과 자료를 바꾼다.
- 본문을 받지 못하거나 확인에 걸리면 아무것도 바꾸지 않고 사유만 적어 둔다. 다음 날 다시 해 본다.
결과는 collected/cn/refresh.json에 적는다(어느 판을 언제 해 봤는지, 됐는지, 목록에서 바뀐 줄). 실행 확인(tools.run.cn_health)이 이 기록을 읽어 알린다.
새 통합본이 없으면 아무것도 받지 않고 기록도 건드리지 않는다.
"""
import json
import sys

from tools.archive import earlier, fulltext
from tools.archive.store import save_text
from tools.cn import build, versions
from tools.common.jsonio import read_json, stamp, write_json

STATE = "collected/cn/refresh.json"
RELATED = "collected/archive/eur-lex-related.json"
TEXT = "eu-fulltext/cbam-consolidated.txt"
MUST = "ANNEX I"  # 받은 글에 꼭 있어야 하는 말


def changes(before, after):
    """목록이 어떻게 바뀌었는지: 더해진 줄과 빠진 줄의 코드(화면에 적는 꼴 그대로)."""
    def keys(entries):
        return {(entry.get("sector", ""), entry.get("shown", "")) for entry in entries}
    old, new = keys(before), keys(after)
    return {"added": sorted(shown for _, shown in new - old), "removed": sorted(shown for _, shown in old - new)}


def _update_index(celex, address, size):
    """받아 둔 문서의 기록에서 통합본의 줄만 새 판으로 바꾼다."""
    index = read_json(build.INDEX, {}) or {}
    entries = [row for row in index.get("entries", []) if row.get("name") != "cbam-consolidated"]
    entries.insert(0, {"name": "cbam-consolidated", "code": celex, "url": address, "lines": size, "textPath": f"collected/archive/pages/{TEXT}"})
    index["entries"] = entries
    write_json(build.INDEX, index)


def _keep_current(used):
    """새 통합본으로 덮어쓰기 전에, 받아 둔 지금의 판을 앞선 판으로 남긴다(규정 원문 화면의 개정 대조가 견줄 글이다)."""
    stored = next((row for row in (read_json(build.INDEX, {}) or {}).get("entries", []) if row.get("name") == "cbam-consolidated"), {})
    earlier.keep(versions.ACT, str(stored.get("code") or used), f"collected/archive/pages/{TEXT}")


def _note(result):
    write_json(STATE, {"triedAt": stamp(), **result})
    return result


def refresh(fetch_parts=None):
    """새 통합본이 있으면 자료를 다시 만든다. 한 일을 사전으로 돌려준다(state: same, rebuilt, failed).

    fetch_parts: 통합본 번호를 받아 ([(꼬리, 주소, 줄 목록)], 사유)를 돌려주는 함수. 시험에서 바꿔 끼운다.
    """
    cn = read_json(build.OUT, {}) or {}
    used = str((cn.get("law") or {}).get("celex", "")) or versions.FIRST
    newer = versions.newer_consolidated(used, read_json(RELATED, {}).get("entries", []))
    if not newer:
        return {"state": "same", "celex": used}
    try:
        parts, why = (fetch_parts or fulltext.celex_parts)(newer)
    except Exception as problem:
        parts, why = [], f"{type(problem).__name__}: {problem}"[:160]
    lines = [line for _, _, part in parts for line in part]
    if not why and not any(MUST in line for line in lines):
        why = f"받은 글에 '{MUST}'가 없음(다른 문서일 수 있음)"
    if why:
        return _note({"state": "failed", "celex": newer, "from": used, "problems": [f"새 통합본의 본문을 받지 못함: {why}"]})
    address = parts[0][1]
    law = [f"[주소] {address}", ""] + lines
    data, found = build.assemble(law, build.read_lines("downstream-commission-DOC_2.txt"), build.read_lines("downstream-council.txt"), newer)
    if found:
        return _note({"state": "failed", "celex": newer, "from": used, "problems": found})
    _keep_current(used)
    save_text(TEXT, law)
    _update_index(newer, address, len(lines))
    write_json(build.OUT, data)
    return _note({"state": "rebuilt", "celex": newer, "from": used, **changes(cn.get("current", []), data["current"]),
                  "enacted": bool(data.get("proposalEnacted")), "summary": build.summary(data)})


def main():
    print(json.dumps(refresh(), ensure_ascii=False))
    return 0  # 실패해도 날마다의 수집은 이어 간다. 사유는 기록에 남아 실행 확인이 알린다.


if __name__ == "__main__":
    sys.exit(main())
