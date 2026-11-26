"""EU 집행위원회의 의견수렴 목록(Have Your Say)에서 CBAM 관련 입법 계획과 의견수렴 기간을 모은다.

의견수렴 목록은 계획마다 지금의 단계만 보여 준다. 계획이 다음 단계로 넘어가면(초안 의견수렴 → 채택) 지난 의견수렴의 기간이 목록에서 사라진다.
규제 연혁의 '의견수렴이 시작되었습니다' 줄은 그 기간을 근거로 삼으므로, 사라지면 근거가 어긋나 그 규제를 고칠 수 없게 된다(2026-11-26의 14132).
그래서 앞의 수집에 있던 단계 가운데 지금의 단계에 없는 것을 계획마다 '앞선 단계'(earlier)로 남기고 원문 대조용 글에도 함께 적는다.
"""
import json

from tools.archive.store import ROOT, save_index, save_text
from tools.collect.jsonwatch import dig, plain
from tools.common.jsonio import read_json
from tools.common.net import fetch

STATUS_LINE = "단계: {stage} | 의견수렴 상태: {feedback} | 시작: {start} | 마감: {end}"
EARLIER_LINE = "앞선 " + STATUS_LINE


def _period(status):
    """같은 단계의 같은 기간인지 가리는 값. 의견수렴 상태(OPEN → CLOSED)만 바뀐 것은 같은 단계로 본다."""
    return (status.get("stage", ""), status.get("start", ""), status.get("end", ""))


def remembered(statuses, before):
    """앞의 기록(before: 그 계획의 앞선 수집 한 줄)에서 지금의 단계(statuses)에 없는 단계를 차례대로 돌려준다.

    앞의 기록이 이미 남겨 둔 앞선 단계(earlier)가 먼저 오고, 그 뒤에 앞의 수집 때의 단계가 온다. 같은 단계는 한 번만 남긴다.
    """
    now = {_period(status) for status in statuses}
    kept, seen = [], set()
    for status in list((before or {}).get("earlier") or []) + list((before or {}).get("statuses") or []):
        key = _period(status)
        if key in now or key in seen or not any(key):
            continue
        seen.add(key)
        kept.append({name: status.get(name, "") for name in ("stage", "feedback", "start", "end")})
    return kept


def with_history(entries, previous):
    """계획마다 앞선 단계를 붙인 목록. previous는 앞의 수집이 남긴 목록이다(없으면 빈 목록)."""
    before = {str(row.get("id")): row for row in previous or []}
    return [{**entry, "earlier": remembered(entry.get("statuses") or [], before.get(str(entry.get("id"))))} for entry in entries]


def text_lines(address, entries):
    """원문 대조에 쓸 글: 계획마다 값들을 한 줄씩 적는다. 지금의 단계 다음에 앞선 단계를 적는다."""
    lines = [f"[주소] {address}", ""]
    for entry in entries:
        lines += [f"번호: {entry['id']}", f"제목: {entry['title']}", f"문서 번호: {entry['reference']}", f"예정 법령 유형: {entry['actType']}"]
        lines += [STATUS_LINE.format(**item) for item in entry.get("statuses") or []]
        lines += [EARLIER_LINE.format(**item) for item in entry.get("earlier") or []]
        lines.append("")
    return lines


def crawl():
    source = next(row for row in read_json("sources/registry.json", {"sources": []})["sources"] if row["code"] == "ec-haveyoursay")
    config = source["json"]
    status, _, body, error = fetch(config["url"], headers={"Accept": "application/json"})
    if status != 200 or not body:
        save_index("ec-hys", [], {"error": f"읽지 못함({status} {error[:80]})"})
        return {"error": status}
    rows = dig(json.loads(body.decode("utf-8", "replace")), config["list"]) or []
    entries = []
    for row in rows:
        statuses = [{"stage": plain(item.get("frontEndStage")), "feedback": plain(item.get("receivingFeedbackStatus")),
                     "start": plain(item.get("feedbackStartDate")), "end": plain(item.get("feedbackEndDate"))}
                    for item in (row.get("currentStatuses") or []) if isinstance(item, dict)]
        entries.append({"id": plain(row.get("id")), "title": plain(row.get("shortTitle")), "reference": plain(row.get("reference")),
                        "actType": plain(row.get("foreseenActType")), "statuses": statuses,
                        "url": f"https://ec.europa.eu/info/law/better-regulation/have-your-say/initiatives/{plain(row.get('id'))}_en"})
    entries = with_history(entries, read_json(ROOT / "ec-hys.json", {}).get("entries", []))
    path = save_text("ec-hys/initiatives.txt", text_lines(source["url"], entries))
    for entry in entries:
        entry["textPath"] = path
    save_index("ec-hys", entries, {"rows": len(rows), "labels": config.get("labels", {}), "remembered": sum(len(entry["earlier"]) for entry in entries)})
    return {"rows": len(rows), "remembered": sum(len(entry["earlier"]) for entry in entries)}
