"""EU 집행위원회의 의견수렴 목록(Have Your Say)에서 CBAM 관련 입법 계획과 의견수렴 기간을 모은다."""
import json

from tools.archive.store import save_index, save_text
from tools.collect.jsonwatch import dig, plain
from tools.common.jsonio import read_json
from tools.common.net import fetch


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
    # 원문 대조에 쓸 글: 항목마다 값들을 한 줄씩 적는다
    lines = [f"[주소] {source['url']}", ""]
    for entry in entries:
        lines += [f"번호: {entry['id']}", f"제목: {entry['title']}", f"문서 번호: {entry['reference']}", f"예정 법령 유형: {entry['actType']}"]
        lines += [f"단계: {item['stage']} | 의견수렴 상태: {item['feedback']} | 시작: {item['start']} | 마감: {item['end']}" for item in entry["statuses"]]
        lines.append("")
    path = save_text("ec-hys/initiatives.txt", lines)
    for entry in entries:
        entry["textPath"] = path
    save_index("ec-hys", entries, {"rows": len(rows), "labels": config.get("labels", {})})
    return {"rows": len(rows)}
