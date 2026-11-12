"""공공기관 게시글의 본문 받기가 막혀 있지 않은지 본다. 실행 확인과 보고(tools.run.health)가 불러 쓴다.

본문을 받지 못한 글은 제목만으로 실리므로 한두 건은 문제가 아니다. 한 출처에서 같은 까닭으로 여러 건이 이어지면
그 사이트의 화면이 바뀌었거나(이용 조건의 글귀가 사라짐, 본문 자리가 달라짐) 읽기가 막힌 것이므로 알린다.
받기로 한 이용 조건이 아니어서 받지 않은 글(예: 공공누리 2유형으로 올라온 글)은 정한 대로 한 일이므로 세지 않는다.
"""
import datetime

from tools.collect.articles import FINAL, SAVED, STATE
from tools.common.jsonio import now_kst, read_json

REPEAT = 3      # 같은 출처, 같은 까닭으로 이만큼 받지 못하면 알린다
RECENT_DAYS = 7


def problems(now=None, path=STATE):
    now = now or now_kst()
    oldest = (now - datetime.timedelta(days=RECENT_DAYS)).isoformat(timespec="seconds")
    missed = {}
    for row in ((read_json(path, {}) or {}).get("items") or {}).values():
        result = str(row.get("result", ""))
        if result != SAVED and result not in FINAL and str(row.get("at", "")) >= oldest:
            missed.setdefault((row.get("source", ""), result[:60]), []).append(row)
    return [f"본문 받기: 출처 {code}의 글 {len(rows)}건을 받지 못함({why}). 이 출처의 소식이 제목만으로 실림"
            for (code, why), rows in sorted(missed.items()) if len(rows) >= REPEAT]
