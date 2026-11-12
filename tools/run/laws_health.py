"""규정 원문과 안내 문서의 번역이 제대로 굴러가는지 본다. 실행 확인과 보고(tools.run.health)가 불러 쓴다.

- 싣기로 한 안내 문서(sources/guides.json)를 원문 대장에서 찾지 못하면 알린다(파일 이름이 바뀐 것이다).
- 안내 문서의 절 나누기가 그 문서의 차례와 크게 어긋나면 알린다(새 판의 꼴이 달라진 것이다).
- 번역이 남아 있는데 여러 날 늘지 않으면 알린다. 번역을 맡은 실행(sources/translation.json)이 돌지 않는 것이다.
  한 번도 옮기지 않은 갈래는 알리지 않는다(아직 시작하지 않은 것).
"""
import datetime
import pathlib

from tools.common.jsonio import read_json, today as today_kst
from tools.laws import corpus, guide_segment, guides, pdf_pages, plan, store

STALLED = 5      # 번역이 이만큼의 날 동안 늘지 않으면 알린다(주말과 하루 이틀의 쉼은 넘긴다)
COVERAGE = 0.8   # 차례에 적힌 절 번호 가운데 찾아낸 비율이 이보다 낮으면 알린다
NAMES = {"act": "규정", "guide": "가이던스"}


def _outline_problems():
    found = [f"가이던스 문서를 원문 대장에서 찾지 못함: {name}" for name in guides.missing()]
    for document in guides.documents():
        text = pathlib.Path(document["path"]).read_text(encoding="utf-8")
        listed = {number for number in pdf_pages.read(text)["toc"]["numbers"] if "." in number}
        cut = {part["label"] for part in guide_segment.parts(text) if part["kind"] == "section"}
        if listed and len(listed & cut) < COVERAGE * len(listed):
            found.append(f"가이던스 문서의 절 나누기가 차례와 맞지 않음: {document['short']}(차례의 {len(listed)}개 가운데 {len(listed & cut)}개)")
    return found


def _last_update(act_ids):
    days = [str((read_json(store.path_of(act_id), {}) or {}).get("updated", "")) for act_id in act_ids]
    return max((day for day in days if day), default="")


def _stalled_problems(day):
    documents, memory = corpus.everything()
    groups = {group for settings in plan.runners().values() for group in settings.get("groups", [])}
    found = []
    for group in sorted(groups):
        mine = [(act, parts) for act, parts in documents if act.get("group", "act") == group]
        left = sum(progress["blocks"] - progress["done"] for progress in (corpus.progress(parts, memory) for _, parts in mine))
        last = _last_update([act["id"] for act, _ in mine])
        if left and last and (datetime.date.fromisoformat(day) - datetime.date.fromisoformat(last)).days > STALLED:
            found.append(f"{NAMES.get(group, group)} 번역이 {last} 뒤로 늘지 않음(남은 문단 {left:,}개)")
    return found


def problems(today=None):
    return _outline_problems() + _stalled_problems(today or today_kst())
