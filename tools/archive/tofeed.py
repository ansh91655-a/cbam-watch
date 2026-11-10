"""소급 수집 도구가 모으는 공식 기록에 새로 생긴 자료를 그날의 새 후보(collected/feed/)로 넘긴다.

대상: EU 집행위원회 보도자료, EU 법령 데이터베이스의 연관 문서, 미국 연방관보 공고, 영국 정부 자료의 갱신 기록.
처음 돌 때는, 그리고 대상에 새로 든 기록은 처음 볼 때, 지금 있는 자료를 모두 '본 것'으로 적기만 한다(지난 자료가 한꺼번에 후보로 쏟아지지 않게).
후보의 원문 글은 저장소에 받아 둔 파일(textPath)이다.
"""
from tools.archive.store import ROOT
from tools.collect import feed
from tools.common.jsonio import read_json, stamp, today, write_json

STATE = ROOT / "feed-state.json"
# (목록 파일, 후보에 적을 출처 코드(sources/registry.json의 것), 자료를 가르는 값의 이름)
RECORDS = [("ec-press", "ec-press", "reference"), ("eur-lex-docs", "eur-lex-related", "celex"), ("us-fedreg", "us-fedreg", "number"), ("uk-govuk", "uk-govuk", "key")]


def fresh(seen):
    """아직 넘기지 않은 자료를 후보 꼴로 돌려준다. seen은 {목록 이름: [이미 넘긴 값]}이다."""
    found, now = [], {}
    for name, code, key in RECORDS:
        rows = read_json(ROOT / f"{name}.json", {}).get("entries", [])
        now[name] = sorted({str(row.get(key, "")) for row in rows if row.get(key)} | set(seen.get(name, [])))
        if name not in seen:  # 대상에 새로 든 기록: 이번에는 적기만 한다
            continue
        for row in rows:
            value = str(row.get(key, ""))
            if value and value not in set(seen.get(name, [])):
                found.append({"id": feed.item_id(code, value), "source": code, "kind": "link", "url": row.get("url", ""),
                              "text": " | ".join(part for part in (row.get("date", ""), row.get("title", ""), row.get("note", "")) if part)[:400], "textPath": row.get("textPath", "")})
    return found, now


def run():
    state = read_json(STATE, None)
    found, now = fresh((state or {}).get("seen", {}))
    moment = stamp()
    added = 0
    if state is not None and found:
        added = feed.append(today(), [{**item, "seenAt": moment} for item in found], moment)
    write_json(STATE, {"updatedAt": moment, "seen": now})
    return {"baseline": state is None, "new": 0 if state is None else len(found), "added": added}
