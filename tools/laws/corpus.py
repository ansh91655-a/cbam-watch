"""싣는 문서(법령과 안내 문서)의 목록과 조각, 번역을 한데 묶어 읽는다. 사이트에 싣는 자료(build), 번역할 것 고르기(todo), 진행 상황(status)이 함께 쓴다.

문서의 갈래(group)는 넷이다. act는 EU 법령(조와 부속서로 나눈다)이고, 나머지 셋은 EU 집행위원회가 낸 문서(PDF의 글을 절로 나눈다)다:
guide(가이던스와 질의응답), manual(CBAM 등록부 이용 안내서), paper(보고서와 그 밖의 안내 자료). 어느 문서가 어느 갈래인지는 sources/guides.json이 정한다.
"""
import functools
import json
import pathlib

from tools.laws import catalog, check, guide_segment, guides, segment, store, unit_segment

GUIDE_KINDS = ("cover", "section", "appendix")
UNITS = "originals/units"   # PDF의 꼬리표에서 읽어 둔 뜻 단위(tools.pdfko.units가 만든다)
LAYOUT = "layout"           # sources/guides.json의 units에 적는 값: 꼬리표가 없는 PDF를 쪽에 놓인 글 상자대로 읽는다


def units_path(text_path):
    """받아 둔 글(originals/text/<문서>/<판>.txt)에 짝이 되는 단위 파일의 자리."""
    text = pathlib.Path(text_path)
    return pathlib.Path(UNITS) / text.parent.name / f"{text.stem}.json"


def units(act):
    """문서의 단위들. 단위 파일이 없거나 쓰지 않기로 한 문서(sources/guides.json의 units: false)면 빈 목록.

    꼬리표가 없는 PDF의 단위(쪽에 놓인 글 상자대로 읽은 것: tools.pdfko.boxes)는 그렇게 읽기로 한 문서("units": "layout")에서만 쓴다.
    그렇게 적지 않은 문서는 전과 같이 뽑아 낸 글을 줄 단위로 나눈다(나누는 방식이 바뀌면 이미 옮긴 번역이 떨어지므로 문서마다 정한다).
    """
    if act.get("format") != "pdf" or act.get("units") is False:
        return []
    path = units_path(act["path"])
    if not path.is_file():
        return []
    found = json.loads(path.read_text(encoding="utf-8"))
    if found.get("tagged") or (act.get("units") == LAYOUT and found.get("layout")):
        return found["units"]
    return []


def marked(act):
    """국문 PDF를 만들 때 쓰는 단위: 꼬리표로 읽은 것만 돌려준다(낱말마다 내용 조각 번호가 적혀 있어 글자의 자리를 찾을 수 있다).
    글 상자대로 읽은 단위에는 그 번호가 없으므로, 그런 문서는 글에서 자리를 찾는 방식으로 만든다."""
    return [] if act.get("units") == LAYOUT else units(act)


@functools.lru_cache(maxsize=128)
def _parts(path, form, outline, stamp, mode):
    text = pathlib.Path(path).read_text(encoding="utf-8")
    if form != "pdf":
        return segment.parts(text)
    found = units({"format": form, "path": path, "units": mode}) if mode is not False else []
    if found:   # PDF에 적힌 짜임(제목, 문단, 목록, 표, 각주)을 그대로 쓴다. 제목 꼬리표가 없는 문서는 글에서 찾은 제목을 빌린다
        return unit_segment.parts(found, outline, lambda: guide_segment.parts(text, outline))
    return guide_segment.parts(text, outline)


def read(act):
    """문서 하나의 조각들. 받아 둔 글이 없으면 빈 목록. 같은 파일은 한 번만 나눈다(파일이 바뀌면 다시 나눈다)."""
    path = pathlib.Path(act["path"])
    if not path.is_file():
        return []
    side = units_path(path)
    mode = act.get("units", True) if side.is_file() else False     # True(꼬리표로 읽은 단위), "layout"(글 상자대로 읽은 단위), False(쓰지 않음)
    stamp = (path.stat().st_mtime_ns, side.stat().st_mtime_ns if mode is not False else 0)
    return _parts(str(path), act.get("format", "act"), act.get("outline", "auto"), stamp, mode)


def label_ko(part):
    """조각의 국문 이름: 제7조, 부속서 I, 2.3.1 …"""
    return guide_segment.label_ko(part) if part["kind"] in GUIDE_KINDS else segment.label_ko(part)


def texts(part):
    """조각에서 번역이 붙는 글자들을 차례대로: 조각의 이름(title)과 문단들."""
    return ([part["title"]] if part["title"] else []) + list(part["blocks"])


def korean(text, memory):
    """문단의 국문. 옮길 글이 없는 줄(수와 기호)은 그대로, 아직 옮기지 않은 문단은 빈 글."""
    return memory.get(store.key(text), "") if check.needs(text) else text


def progress(found, memory):
    """조각들의 번역 진행: {"blocks": 옮길 문단 수, "done": 옮긴 문단 수, "chars": 옮길 글자 수, "doneChars": 옮긴 원문의 글자 수}"""
    total = {"blocks": 0, "done": 0, "chars": 0, "doneChars": 0}
    for part in found:
        for text in texts(part):
            if not check.needs(text):
                continue
            total["blocks"] += 1
            total["chars"] += len(text)
            if store.key(text) in memory:
                total["done"] += 1
                total["doneChars"] += len(text)
    return total


def documents():
    """싣는 문서의 목록: 법령 다음에 안내 문서. 화면에 보이는 차례다."""
    return catalog.acts() + guides.documents()


def everything(history=False):
    """[(문서, 조각들)] 을 싣는 차례대로, 그리고 모든 번역 {열쇠: 국문}.

    history가 참이면 문서의 앞선 판에만 있는 문단을 담은 숨은 문서(tools.laws.revisions.history)를 뒤에 붙인다.
    번역과 검수가 그 문단까지 다루게 하려는 것이다. 사이트에 싣는 자료를 만들 때에는 붙이지 않는다.
    """
    found = [(act, read(act)) for act in documents()]
    if history:
        from tools.laws import revisions  # revisions가 이 모듈을 들이므로 여기서 들인다
        found += revisions.history(found)
    return found, store.load_all()


def published():
    """사이트에 싣는 것: [(문서, 조각들)]과, 검수를 거친 번역만 남긴 {열쇠: 국문}.

    한 번도 검수하지 않은 번역은 싣지 않는다(화면에는 '번역 준비 중'으로 보인다). 검수를 마친 뒤에 고친 번역은 다시 검수하기 전에도 싣는다(tools.laws.store).
    """
    found, memory = everything()
    ready = store.reviewed_all()
    return found, {block_key: text for block_key, text in memory.items() if block_key in ready}
