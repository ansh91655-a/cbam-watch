"""사이트에 싣는 규정 원문 자료를 만든다. 사이트 폴더를 만들 때(tools.publish.build_site) 불린다.

- laws/index.json: 문서(법령과 안내 문서)의 목록과 차례(조와 부속서, 절의 이름), 번역 진행 상황
- laws/<문서 id>.json: 조각마다의 원문 문단과 국문 번역(아직 옮기지 않은 문단은 빈 글). 번역문의 전문용어에는 영문을 병기한다(tools.laws.gloss)
- laws/search.json: 법령 검색에 쓰는 글(조각마다 원문과 번역을 이은 것). 안내 문서의 것은 laws/search-guides.json에 따로 둔다(화면이 필요할 때만 받게)
원문은 저장소에 받아 둔 EU 법령의 글(collected/archive/pages/)과 집행위원회 안내 문서의 글(originals/text/)이고, 번역은 data/laws-ko/에 있다.
"""
import json
import pathlib

from tools.laws import catalog, corpus, gloss

SEARCHED = ("recitals", "article", "annex", "section", "appendix")           # 검색에 넣는 조각
LISTED = ("recitals", "division", "article", "annex", "section", "appendix")  # 차례에 보이는 조각
HEADS = ("front", "cover")                                                   # 문서의 머리(제목, 근거, 표지)
NOTICE = "This text is meant purely as a documentation tool"  # 통합본이 스스로 적어 둔 알림의 첫머리
DISCLAIMER = "Disclaimer:"                                    # 안내 문서가 표지에 적어 둔 일러두기의 첫머리
SEARCH_FILES = {"act": "search.json", "guide": "search-guides.json"}


def _dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def body(act, found, memory):
    """문서 하나의 공개용 자료. 번역문의 전문용어에는 영문을 병기한다."""
    front = next((part["blocks"] for part in found if part["kind"] in HEADS), [])
    return {
        "id": act["id"], "group": act.get("group", "act"), "name": act["name"], "short": act.get("short", act["name"]),
        "official": act.get("official") or catalog.official(act["celex"], front), "url": act["url"],
        "consolidated": act["consolidated"], "received": act.get("received", ""), "pages": act.get("pages", 0), "rule": act["rule"],
        "notice": next((line for line in front if line.startswith((NOTICE, DISCLAIMER))), ""),
        "progress": corpus.progress(found, memory),
        "parts": [{"id": part["id"], "kind": part["kind"], "level": part.get("level", 0), "label": part["label"], "ko": corpus.label_ko(part), "title": part["title"],
                   "titleKo": corpus.korean(part["title"], memory) if part["title"] else "",
                   "blocks": gloss.annotate([[text, corpus.korean(text, memory)] for text in part["blocks"]])} for part in found],
    }


def listing(act_body):
    """목록에 싣는 한 줄: 본문을 뺀 값과 차례."""
    parts = act_body["parts"]
    return {**{name: act_body[name] for name in ("id", "group", "name", "short", "official", "url", "consolidated", "received", "pages", "rule", "progress")},
            "articles": sum(part["kind"] == "article" for part in parts), "annexes": sum(part["kind"] in ("annex", "appendix") for part in parts),
            "sections": sum(part["kind"] == "section" for part in parts),
            "toc": [{"id": part["id"], "kind": part["kind"], "level": part["level"], "ko": part["ko"], "title": part["title"], "titleKo": part["titleKo"]}
                    for part in parts if part["kind"] in LISTED]}


def search_rows(act_id, found, memory):
    """검색에 쓰는 줄들: 조각마다 {a: 문서, p: 조각, n: 국문 이름, t: 영문 제목, k: 국문 제목, x: 원문, y: 번역}. 번역은 병기를 붙이기 전의 글이다."""
    rows = []
    for part in found:
        if part["kind"] not in SEARCHED:
            continue
        korean = [corpus.korean(text, memory) for text in part["blocks"]]
        rows.append({"a": act_id, "p": part["id"], "n": corpus.label_ko(part), "t": part["title"], "k": corpus.korean(part["title"], memory) if part["title"] else "",
                     "x": "\n".join(part["blocks"]), "y": "\n".join(ko for text, ko in zip(part["blocks"], korean) if ko and ko != text)})
    return rows


def write(data_out):
    """data_out(사이트의 data 폴더) 아래 laws/에 자료를 쓰고, 문서의 수를 돌려준다."""
    folder = pathlib.Path(data_out) / "laws"
    documents, memory = corpus.everything()
    documents = [(act, found) for act, found in documents if found]
    bodies = [body(act, found, memory) for act, found in documents]
    for act_body in bodies:
        _dump(folder / f"{act_body['id']}.json", act_body)
    _dump(folder / "index.json", {"acts": [listing(act_body) for act_body in bodies]})
    for group, name in SEARCH_FILES.items():
        _dump(folder / name, {"rows": [row for act, found in documents if act.get("group", "act") == group for row in search_rows(act["id"], found, memory)]})
    return len(bodies)
