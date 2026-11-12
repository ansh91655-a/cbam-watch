"""법령의 목록과 조각, 번역을 한데 묶어 읽는다. 사이트에 싣는 자료(build), 번역할 것 고르기(todo), 진행 상황(status)이 함께 쓴다."""
import pathlib

from tools.laws import catalog, check, segment, store


def read(act):
    """법령 하나의 조각들. 받아 둔 글이 없으면 빈 목록."""
    path = pathlib.Path(act["path"])
    return segment.parts(path.read_text(encoding="utf-8")) if path.exists() else []


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


def everything():
    """[(법령, 조각들)] 을 싣는 차례대로, 그리고 모든 번역 {열쇠: 국문}."""
    return [(act, read(act)) for act in catalog.acts()], store.load_all()
