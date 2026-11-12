"""사이트에 싣는 규정 원문 자료를 만든다. 사이트 폴더를 만들 때(tools.publish.build_site) 불린다.

- laws/index.json: 법령의 목록과 차례(조와 부속서의 이름), 번역 진행 상황
- laws/<법령 번호>.json: 조각마다의 원문 문단과 국문 번역(아직 옮기지 않은 문단은 빈 글). 번역문의 전문용어에는 영문을 병기한다(tools.laws.gloss)
- laws/search.json: 전체 규정 검색에 쓰는 글(조각마다 원문과 번역을 이은 것)
원문은 저장소에 받아 둔 EU 법령의 글(collected/archive/pages/)이고, 번역은 data/laws-ko/에 있다.
"""
import json
import pathlib

from tools.laws import catalog, corpus, gloss, segment

SEARCHED = ("recitals", "article", "annex")           # 검색에 넣는 조각
LISTED = ("recitals", "division", "article", "annex")  # 차례에 보이는 조각
NOTICE = "This text is meant purely as a documentation tool"  # 통합본이 스스로 적어 둔 알림의 첫머리


def _dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def body(act, found, memory):
    """법령 하나의 공개용 자료. 번역문의 전문용어에는 영문을 병기한다."""
    front = next((part["blocks"] for part in found if part["kind"] == "front"), [])
    return {
        "id": act["id"], "name": act["name"], "official": catalog.official(act["celex"], front), "url": act["url"],
        "consolidated": act["consolidated"], "rule": act["rule"], "notice": next((line for line in front if line.startswith(NOTICE)), ""),
        "progress": corpus.progress(found, memory),
        "parts": [{"id": part["id"], "kind": part["kind"], "label": part["label"], "ko": segment.label_ko(part), "title": part["title"],
                   "titleKo": corpus.korean(part["title"], memory) if part["title"] else "",
                   "blocks": gloss.annotate([[text, corpus.korean(text, memory)] for text in part["blocks"]])} for part in found],
    }


def listing(act_body):
    """목록에 싣는 한 줄: 본문을 뺀 값과 차례."""
    parts = act_body["parts"]
    return {**{name: act_body[name] for name in ("id", "name", "official", "url", "consolidated", "rule", "progress")},
            "articles": sum(part["kind"] == "article" for part in parts), "annexes": sum(part["kind"] == "annex" for part in parts),
            "toc": [{"id": part["id"], "kind": part["kind"], "ko": part["ko"], "title": part["title"], "titleKo": part["titleKo"]}
                    for part in parts if part["kind"] in LISTED]}


def search_rows(act_id, found, memory):
    """검색에 쓰는 줄들: 조각마다 {a: 법령, p: 조각, n: 국문 이름, t: 영문 제목, k: 국문 제목, x: 원문, y: 번역}. 번역은 병기를 붙이기 전의 글이다."""
    rows = []
    for part in found:
        if part["kind"] not in SEARCHED:
            continue
        korean = [corpus.korean(text, memory) for text in part["blocks"]]
        rows.append({"a": act_id, "p": part["id"], "n": segment.label_ko(part), "t": part["title"], "k": corpus.korean(part["title"], memory) if part["title"] else "",
                     "x": "\n".join(part["blocks"]), "y": "\n".join(ko for text, ko in zip(part["blocks"], korean) if ko and ko != text)})
    return rows


def write(data_out):
    """data_out(사이트의 data 폴더) 아래 laws/에 자료를 쓰고, 법령의 수를 돌려준다."""
    folder = pathlib.Path(data_out) / "laws"
    acts, memory = corpus.everything()
    acts = [(act, found) for act, found in acts if found]
    bodies = [body(act, found, memory) for act, found in acts]
    for act_body in bodies:
        _dump(folder / f"{act_body['id']}.json", act_body)
    _dump(folder / "index.json", {"acts": [listing(act_body) for act_body in bodies]})
    _dump(folder / "search.json", {"rows": [row for act, found in acts for row in search_rows(act["id"], found, memory)]})
    return len(bodies)
