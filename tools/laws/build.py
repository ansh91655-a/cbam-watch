"""사이트에 싣는 규정 원문 자료를 만든다. 사이트 폴더를 만들 때(tools.publish.build_site) 불린다.

- laws/index.json: 문서(법령과 안내 문서)의 목록과 차례(조와 부속서, 절의 이름), 번역 진행 상황
- laws/<문서 id>.json: 조각마다의 원문 문단과 국문 번역(아직 옮기지 않은 문단은 빈 글). 번역문의 전문용어에는 영문을 병기한다(tools.laws.gloss)
- laws/search.json: 법령 검색에 쓰는 글(조각마다 원문과 번역을 이은 것). 안내 문서(가이던스, 등록부 안내서, 보고서)의 것은 laws/search-guides.json에 따로 둔다(화면이 필요할 때만 받게)
- laws/changes/<문서 id>.json: 앞선 판과 견줘 달라진 문단(tools.laws.revisions). 앞선 판이 있는 문서만 만든다. 목록과 문서의 자료에는 한 줄(changes)을 싣는다
원문은 저장소에 받아 둔 EU 법령의 글(collected/archive/pages/)과 집행위원회 문서의 글(originals/text/)이고, 번역은 data/laws-ko/에 있다.
번역 자료의 검수 표시(checked)와 일부러 바꾼 번역(tools.laws.spoil)은 사이트에 싣지 않는다.
"""
import json
import pathlib
import re

from tools.laws import catalog, corpus, gloss, revisions

SEARCHED = ("recitals", "article", "annex", "section", "appendix")           # 검색에 넣는 조각
LISTED = ("recitals", "division", "article", "annex", "section", "appendix")  # 차례에 보이는 조각
HEADS = ("front", "cover")                                                   # 문서의 머리(제목, 근거, 표지)
NOTICE = "This text is meant purely as a documentation tool"  # 통합본이 스스로 적어 둔 알림의 첫머리
FORMULA = re.compile(r"^\(Equation \d+[a-z]?\)[;,.]?$")        # 법령의 수식 자리에 남은 번호(식은 원문에 그림으로 실려 있다)
DISCLAIMER = "Disclaimer:"                                    # 안내 문서가 표지에 적어 둔 일러두기의 첫머리
SEARCH_FILES = {"search.json": ("act",), "search-guides.json": ("guide", "manual", "paper")}  # 검색에 쓰는 글의 파일과 거기에 싣는 갈래


def _dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def body(act, found, memory):
    """문서 하나의 공개용 자료. 번역문의 전문용어에는 영문을 병기한다."""
    front = next((part["blocks"] for part in found if part["kind"] in HEADS), [])
    units = corpus.units(act)  # PDF의 꼬리표에서 읽은 단위(문단마다의 쪽을 싣는 데 쓴다). 없으면 빈 목록
    return {
        "id": act["id"], "group": act.get("group", "act"), "name": act["name"], "short": act.get("short", act["name"]),
        "official": act.get("official") or catalog.official(act["celex"], front), "url": act["url"],
        "consolidated": act["consolidated"], "received": act.get("received", ""), "pages": act.get("pages", 0), "rule": act["rule"], "remark": act.get("remark", ""),
        "notice": next((line for line in front if line.startswith((NOTICE, DISCLAIMER))), ""),
        "progress": corpus.progress(found, memory),
        "parts": [_part(part, memory, units) for part in found],
    }


def _part(part, memory, units=()):
    """조각 하나의 공개용 자료. 문단의 꼴(목록, 표의 칸, 각주 …)을 아는 문서는 shapes에 문단마다 싣는다(화면이 그 꼴로 그린다).

    PDF의 단위(units)를 아는 문서는 문단마다 그 문단이 있는 쪽을 pages에 싣는다(화면이 문단을 인용할 때 쪽을 적는다)."""
    row = {"id": part["id"], "kind": part["kind"], "level": part.get("level", 0), "label": part["label"], "ko": corpus.label_ko(part), "title": part["title"],
           "titleKo": corpus.korean(part["title"], memory) if part["title"] else "",
           "blocks": gloss.annotate([[text, corpus.korean(text, memory)] for text in part["blocks"]])}
    if any(shape != "p" for shape in part.get("shapes", [])):
        row["shapes"] = part["shapes"]
    if part.get("page"):
        row["page"] = part["page"]  # 이 조각이 시작하는 PDF의 쪽
    formulas = sum(1 for text in part["blocks"] if FORMULA.match(text))
    if formulas:
        row["formulas"] = formulas  # 수식의 번호만 남은 줄의 수(법령의 수식은 원문에 그림으로 실려 있다). 화면이 원문에서 보라고 알린다
    if part.get("cut"):
        row["cut"] = part["cut"]    # 받아 둘 때 뺀 줄 수(값의 표가 아주 긴 부속서). 화면이 싣지 않은 부분이 있다고 알린다
    if units and len(part.get("units", [])) == len(part["blocks"]) and part["blocks"]:
        row["pages"] = [units[index]["page"] for index in part["units"]]
    return row


def listing(act_body):
    """목록에 싣는 한 줄: 본문을 뺀 값과 차례."""
    parts = act_body["parts"]
    return {**{name: act_body[name] for name in ("id", "group", "name", "short", "official", "url", "consolidated", "received", "pages", "rule", "remark", "progress", "changes") if name in act_body},
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
    documents, memory = corpus.published()   # 검수를 거친 번역만 싣는다
    documents = [(act, found) for act, found in documents if found]
    bodies = [body(act, found, memory) for act, found in documents]
    changed = revisions.write(folder, documents, memory)   # 앞선 판과 달라진 곳(문서마다의 파일)과, 목록에 실을 한 줄
    for act_body in bodies:
        if act_body["id"] in changed:
            act_body["changes"] = changed[act_body["id"]]
        _dump(folder / f"{act_body['id']}.json", act_body)
    _dump(folder / "index.json", {"acts": [listing(act_body) for act_body in bodies]})
    for name, groups in SEARCH_FILES.items():
        _dump(folder / name, {"rows": [row for act, found in documents if act.get("group", "act") in groups for row in search_rows(act["id"], found, memory)]})
    return len(bodies)
