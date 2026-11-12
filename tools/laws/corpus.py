"""싣는 문서(법령과 안내 문서)의 목록과 조각, 번역을 한데 묶어 읽는다. 사이트에 싣는 자료(build), 번역할 것 고르기(todo), 진행 상황(status)이 함께 쓴다.

문서의 갈래(group)는 넷이다. act는 EU 법령(조와 부속서로 나눈다)이고, 나머지 셋은 EU 집행위원회가 낸 문서(PDF의 글을 절로 나눈다)다:
guide(가이던스와 질의응답), manual(CBAM 등록부 이용 안내서), paper(보고서와 그 밖의 안내 자료). 어느 문서가 어느 갈래인지는 sources/guides.json이 정한다.
"""
import functools
import pathlib

from tools.laws import catalog, check, guide_segment, guides, segment, store

GUIDE_KINDS = ("cover", "section", "appendix")


@functools.lru_cache(maxsize=128)
def _parts(path, form, outline, stamp):
    text = pathlib.Path(path).read_text(encoding="utf-8")
    return guide_segment.parts(text, outline) if form == "pdf" else segment.parts(text)


def read(act):
    """문서 하나의 조각들. 받아 둔 글이 없으면 빈 목록. 같은 파일은 한 번만 나눈다(파일이 바뀌면 다시 나눈다)."""
    path = pathlib.Path(act["path"])
    return _parts(str(path), act.get("format", "act"), act.get("outline", "auto"), path.stat().st_mtime_ns) if path.is_file() else []


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


def everything():
    """[(문서, 조각들)] 을 싣는 차례대로, 그리고 모든 번역 {열쇠: 국문}."""
    return [(act, read(act)) for act in documents()], store.load_all()
