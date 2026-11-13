"""규정 원문과 안내 문서의 번역이 제대로 굴러가는지 본다. 실행 확인과 보고(tools.run.health)가 불러 쓴다.

- 싣기로 한 안내 문서(sources/guides.json)를 원문 대장에서 찾지 못하면 알린다(파일 이름이 바뀐 것이다).
- 안내 문서의 절 나누기가 그 문서의 차례와 크게 어긋나면 알린다(새 판의 꼴이 달라진 것이다).
- 번역이 남아 있는데 여러 날 늘지 않으면 알린다. 번역을 맡은 실행(sources/translation.json)이 돌지 않는 것이다.
  한 번도 옮기지 않은 갈래는 알리지 않는다(아직 시작하지 않은 것).
- 검사에 거듭 걸려 끝내 싣지 못한 문단이 있으면 알린다(검사 프로그램이 잘못 막고 있거나 원문이 깨진 것이다. 사람이 봐야 한다).
- 검수(tools.laws.verify)가 여러 날 늘지 않거나, 일부러 바꿔 섞은 번역을 놓치거나, 묶음을 반영하지 못했거나, 번역과 검수가 맞선 문단이 생기면 알린다.
"""
import datetime
import pathlib

from tools.common.jsonio import read_json, today as today_kst
from tools.laws import corpus, guide_segment, guides, pdf_pages, plan, status, store, verify

STALLED = 5      # 번역이 이만큼의 날 동안 늘지 않으면 알린다(주말과 하루 이틀의 쉼은 넘긴다)
COVERAGE = 0.8   # 차례에 적힌 절 번호 가운데 찾아낸 비율이 이보다 낮으면 알린다
NAMES = {"act": "규정", "guide": "가이던스", "manual": "등록부 안내서", "paper": "보고서·안내 자료"}
UNCHECKED = 3    # 검수할 문단이 남아 있는데 이만큼의 날 동안 검수 기록이 없으면 알린다
CAUGHT = 0.6     # 일부러 바꾼 번역을 잡아낸 비율(최근 기록)이 이보다 낮으면 알린다
CANARIES_MIN = 10  # 바꾼 번역이 이만큼은 쌓여야 비율을 본다


def _outline_problems():
    found = [f"안내 문서를 원문 대장에서 찾지 못함: {name}" for name in guides.missing()]
    for document in guides.documents():
        if document.get("outline") == "none":
            continue  # 제목을 찾지 않는 문서
        text = pathlib.Path(document["path"]).read_text(encoding="utf-8")
        listed = {number for number in pdf_pages.read(text)["toc"]["numbers"] if "." in number}
        cut = {part["label"] for part in corpus.read(document) if part["kind"] == "section"}
        if listed and len(listed & cut) < COVERAGE * len(listed):
            found.append(f"안내 문서의 절 나누기가 차례와 맞지 않음: {document['short']}(차례의 {len(listed)}개 가운데 {len(listed & cut)}개)")
    return found


def _units_problems():
    """PDF로 받은 문서인데 꼬리표에서 읽은 단위 파일이 없는 것. 그 문서는 글에서 나눈 조각을 쓰게 되어 문단이 달라지고 번역이 떨어져 나간다."""
    missing = [document["short"] for document in guides.documents()
               if document.get("format") == "pdf" and document.get("units") is not False and not corpus.units_path(document["path"]).is_file()]
    return [f"원문 PDF의 뜻 단위를 읽어 두지 않은 문서 {len(missing)}건({', '.join(missing[:3])}): python -m tools.pdfko.units --missing"] if missing else []


def _last_update(act_ids):
    days = [str((read_json(store.path_of(act_id), {}) or {}).get("updated", "")) for act_id in act_ids]
    return max((day for day in days if day), default="")


def _stalled_problems(day):
    documents, memory = corpus.everything(history=True)   # 앞선 판에만 있는 문단(달라진 곳 보기에 쓰는 것)도 옮길 것으로 센다
    groups = {group for settings in plan.runners().values() for group in settings.get("groups", [])}
    found = []
    for group in sorted(groups):
        mine = [(act, parts) for act, parts in documents if act.get("group", "act") == group]
        left = sum(progress["blocks"] - progress["done"] for progress in (corpus.progress(parts, memory) for _, parts in mine))
        last = _last_update([act["id"] for act, _ in mine])
        if left and last and (datetime.date.fromisoformat(day) - datetime.date.fromisoformat(last)).days > STALLED:
            found.append(f"{NAMES.get(group, group)} 번역이 {last} 뒤로 늘지 않음(남은 문단 {left:,}개)")
    return found


def _check_problems(day):
    """검수(tools.laws.verify)가 도는지, 제대로 읽는지."""
    log = read_json(verify.LOG, {}) or {}
    days = sorted(log.get("days", []), key=lambda row: row.get("day", ""))
    found = []
    state = verify.progress()
    waiting = state["translated"] - state["checked"]
    last = next((row["day"] for row in reversed(days) if row.get("checked") or row.get("dropped")), "")
    if waiting and days and (not last or (datetime.date.fromisoformat(day) - datetime.date.fromisoformat(last)).days > UNCHECKED):
        found.append(f"번역 검수가 {last or '처음'} 뒤로 늘지 않음(검수할 문단 {waiting:,}개)")
    recent = days[-7:]
    seeded, caught = sum(row.get("canaries", 0) for row in recent), sum(row.get("caught", 0) for row in recent)
    if seeded >= CANARIES_MIN and caught < CAUGHT * seeded:
        found.append(f"번역 검수가 일부러 바꾼 번역을 놓침(최근 {seeded}개 가운데 {caught}개만 잡음)")
    held = sum(row.get("held", 0) for row in recent if row.get("day") == day)
    if held:
        found.append(f"번역 검수의 묶음 {held}개를 반영하지 않음(틀렸다고 한 비율이 지나치게 높음)")
    fresh = [row for row in log.get("disputed", []) if row.get("day") == day]
    if fresh:
        found.append(f"번역과 검수가 맞선 문단 {len(fresh)}개(두 번 다시 옮기고도 틀렸다고 함): " + ", ".join(row["key"] for row in fresh[:5]))
    return found


def _held_problems():
    """검사에 거듭 걸려 더 주지 않게 된 문단."""
    given_up = status.held(tries=store.GIVE_UP)
    if not given_up:
        return []
    shown = ", ".join(f"{block_key}({row['why'][:40]})" for block_key, row in sorted(given_up.items())[:3])
    return [f"번역: 검사에 거듭 걸려 싣지 못한 문단 {len(given_up)}개: {shown}"]


def problems(today=None):
    day = today or today_kst()
    return _outline_problems() + _units_problems() + _stalled_problems(day) + _held_problems() + _check_problems(day)
