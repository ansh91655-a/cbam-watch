"""EU 기관의 역할과 법이 만들어지는 절차를 풀이한 자료(data/procedures.json)를 검사하고, 사이트에 실을 모양으로 바꾼다.

사이트의 '입법 절차' 화면과 규제 화면의 '세부 절차'가 이 자료를 쓴다. 규제마다 어느 절차를 따르고 지금 어느 단계인지는 규제 자료에 적는다(tools/publish/rule_steps.py).
검사: python -m tools.publish.procedures            (문제가 있으면 0이 아닌 값으로 끝난다)

자료의 짜임
{"asOf": "2026-11-18", "lead": "화면 머리에 적는 한두 문장",
 "sources": {"tfeu-294": {"text": "EU 기능조약 제294조", "url": "https://…", "path": "collected/archive/pages/eu-primary/tfeu-294.txt", "read"?: "#law-…"},
             "council-olp": {"text": "EU 이사회의 일반입법절차 안내", "url": "https://…", "checkedOn": "2026-11-18"}},
 "institutions": [{"key", "name", "en", "aka"?, "role", "points": [{"text", "basis"}]}],
 "acts": [{"key", "name", "en", "text", "basis"}],
 "codes": [{"code", "text", "basis"}],
 "kinds": [{"key", "name", "en", "lead": {"text", "basis"}, "lanes": [기관의 key],
            "steps": [{"key", "name", "part", "who": [기관의 key], "by"?: "EEA 공동위원회", "text", "basis", "optional"?: true, "track"?: "parliament", "reach"?: 2}],
            "notes": [{"title", "text", "basis"}]}],
 "terms": [{"ko", "en", "abbr"?, "also"?: [다른 국문 표기], "text", "at"}]}

- 자료(sources)는 둘 가운데 하나다. path가 있으면 받아 둔 공식 글이고(조약의 조문, 법령, 유럽의회 입법 관측소의 기록), 근거마다 그 글에 있어야 하는 말(contains)을
  적어 프로그램이 맞춰 본다. checkedOn이 있으면 공식 화면을 읽고 확인한 것이다(자동으로 받아 둘 수 없는 기관의 안내 화면). 화면은 이 둘을 가려서 보여 준다.
- 근거(basis)는 [{"source": "<sources의 이름>", "contains": ["받아 둔 글에 있는 말", …]}]이다. 글 하나하나가 근거를 가져야 한다. 화면을 읽고 확인한 자료에는 contains를 적지 않는다.
- 절차(kinds)의 단계(steps)는 일이 일어나는 차례대로 적는다. part는 단계들을 묶는 이름, who는 그 일을 하는 기관이다.
  기관 목록에 없는 곳이 하는 일(EEA 공동위원회, 영국 의회, WTO의 패널)은 by에 그 이름을 적는다. lanes는 기관별 줄 그림에 세울 기관들이다(없으면 그리지 않는다).
  optional은 절차마다 꼭 있지는 않은 단계(사전 준비, 자문기구의 의견)이고, 진행도를 셀 때 빼고 센다.
  track은 같은 때에 따로 나아가는 갈래의 이름이다(유럽의회의 심의와 EU 이사회의 심의). 갈래가 다른 단계는 서로의 앞뒤를 정하지 않는다.
  reach는 그 단계의 기록이 있으면 규제의 큰 단계(path의 차례 번호 at)가 적어도 여기까지는 와 있어야 한다는 뜻이다(규제 자료의 검사가 쓴다).
- 용어(terms)는 글 속 용어 풀이에 더할 말이다. at은 이 화면 안의 자리다: "who.<기관>", "acts.<법령의 종류>", "<절차>", "<절차>.<단계>".
- 글은 높임말로 쓰고, 조약과 법령이 정한 것과 기관이 스스로 밝힌 것만 적는다.
"""
import pathlib
import re
import sys

from tools.check import style_check, term_check
from tools.common.jsonio import read_json

SOURCE = "data/procedures.json"
# 근거로 댈 수 있는 글이 있는 곳: 모아 둔 공식 기록(조약, 법령, 기관의 기록)
STORED = (pathlib.Path("collected/archive"),)
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
KEY = re.compile(r"^[a-z][a-z0-9-]*$")
DRIFT = "근거 어긋남"   # 받아 둔 글이 달라져 근거가 맞지 않게 된 것. 사이트 만들기를 멈추지 않고 알리기만 한다
WHO_SECTION, ACT_SECTION = "who", "acts"   # 화면 안의 자리 이름(절차의 이름으로는 쓰지 않는다)


def blocking(found):
    """사이트 만들기를 멈출 문제만 고른다(받아 둔 글과 근거가 어긋난 것은 알리기만 한다)."""
    return [row for row in found if not row[1].startswith(DRIFT)]


def _text_problems(text, term_index):
    found = [f"표기 규칙({hit['rule']}: {hit['sample']})" for hit in style_check.check(text) if hit["hard"]]
    found += [f"쓰지 않는 용어({hit['avoid']} → {hit['use']})" for hit in term_check.check(text, term_index) if hit["hard"]]
    return found


def source_problems(sources):
    found = []
    for name, source in (sources or {}).items():
        where = f"자료 {name}"
        if not KEY.match(str(name)):
            found.append((where, "이름이 소문자·숫자·붙임표가 아님"))
        if not str(source.get("text", "")).strip() or not str(source.get("url", "")).startswith("https://"):
            found.append((where, "이름(text)이나 주소(url, https)가 없음"))
        stored, seen = "path" in source, "checkedOn" in source
        if stored == seen:
            found.append((where, "받아 둔 글(path)과 확인한 날(checkedOn) 가운데 하나만 있어야 함"))
        elif stored:
            path = pathlib.Path(str(source["path"]))
            if not any(folder in path.parents for folder in STORED):
                found.append((where, "근거 파일이 모아 둔 자료가 아님"))
            elif not path.exists():
                found.append((where, f"{DRIFT}: 근거 파일이 없음: {path}"))
        elif not DATE.match(str(source["checkedOn"])):
            found.append((where, "확인한 날(checkedOn)이 날짜가 아님"))
        if source.get("read") and not str(source["read"]).startswith("#"):
            found.append((where, "이 사이트 안의 자리(read)는 #으로 시작해야 함"))
    return found


def basis_problems(where, basis, sources, texts, kinds):
    """글 하나의 근거. texts는 받아 둔 글을 한 번만 읽으려고 쓰는 곳간이다({경로: 글})."""
    if not isinstance(basis, list) or not basis:
        return [(where, "근거(basis)가 없음")]
    found = []
    for one in basis:
        name = (one or {}).get("source")
        source = (sources or {}).get(name)
        if not source:
            found.append((where, f"없는 자료: {name}"))
            continue
        phrases = one.get("contains") or []
        if "path" not in source:
            if phrases:
                found.append((where, f"화면을 읽고 확인한 자료({name})에는 찾을 글(contains)을 적지 않음"))
            continue
        if not phrases:
            found.append((where, f"받아 둔 글({name})에서 찾을 글(contains)이 없음"))
        if "evidence" not in kinds:
            continue
        path = str(source["path"])
        if path not in texts:
            file = pathlib.Path(path)
            texts[path] = file.read_text(encoding="utf-8") if file.exists() else None
        if texts[path] is None:
            continue   # 파일이 없는 것은 자료 쪽에서 한 번만 알린다
        missing = [phrase for phrase in phrases if phrase not in texts[path]]
        if missing:
            found.append((where, f"{DRIFT}: {name}에 없는 글: {missing}"))
    return found


def anchors(body):
    """이 화면 안의 자리 이름들: 용어(terms)의 at과 다른 화면의 링크가 가리킬 수 있는 곳."""
    found = {WHO_SECTION, ACT_SECTION}
    found |= {f"{WHO_SECTION}.{one.get('key')}" for one in body.get("institutions", [])}
    found |= {f"{ACT_SECTION}.{one.get('key')}" for one in body.get("acts", [])}
    for kind in body.get("kinds", []):
        found.add(kind.get("key"))
        found |= {f"{kind.get('key')}.{step.get('key')}" for step in kind.get("steps", [])}
    return found


def problems(body, term_index=None, kinds=("format", "evidence")):
    """자료 전체의 문제를 (어디, 무엇) 목록으로 돌려준다. kinds로 볼 것을 고른다("format": 꼴과 표기, "evidence": 근거가 받아 둔 글과 맞는지)."""
    if not isinstance(body, dict):
        return [("머리", "자료를 읽지 못함")]
    term_index = term_index or term_check.load()
    sources, texts, found = body.get("sources") or {}, {}, []

    def text(where, value):
        if not str(value or "").strip():
            found.append((where, "글이 비어 있음"))
        found.extend((where, problem) for problem in _text_problems(str(value or ""), term_index))

    def unique(where, keys):
        if any(not KEY.match(str(key or "")) for key in keys) or len(set(keys)) != len(keys):
            found.append((where, "이름(key)이 없거나 겹치거나 소문자·숫자·붙임표가 아님"))

    if not DATE.match(str(body.get("asOf", ""))):
        found.append(("머리", "기준일(asOf)이 날짜가 아님"))
    text("머리", body.get("lead"))
    found += source_problems(sources)

    institutions = body.get("institutions", [])
    who = [one.get("key") for one in institutions]
    unique("기관", who)
    for one in institutions:
        where = f"기관 {one.get('key')}"
        for field in ("name", "en", "role"):
            if not str(one.get(field, "")).strip():
                found.append((where, f"{field}이(가) 비어 있음"))
        text(where, one.get("role"))
        if not one.get("points"):
            found.append((where, "풀이(points)가 없음"))
        for index, point in enumerate(one.get("points", []), start=1):
            text(f"{where} {index}", point.get("text"))
            found += basis_problems(f"{where} {index}", point.get("basis"), sources, texts, kinds)

    unique("법령의 종류", [one.get("key") for one in body.get("acts", [])])
    for one in body.get("acts", []):
        where = f"법령의 종류 {one.get('key')}"
        if not str(one.get("name", "")).strip() or not str(one.get("en", "")).strip():
            found.append((where, "이름(name, en)이 비어 있음"))
        text(where, one.get("text"))
        found += basis_problems(where, one.get("basis"), sources, texts, kinds)
    for one in body.get("codes", []):
        where = f"문서 번호 {one.get('code')}"
        if not str(one.get("code", "")).strip():
            found.append((where, "번호(code)가 비어 있음"))
        text(where, one.get("text"))
        found += basis_problems(where, one.get("basis"), sources, texts, kinds)

    kind_keys = [kind.get("key") for kind in body.get("kinds", [])]
    unique("절차", kind_keys)
    if {WHO_SECTION, ACT_SECTION} & set(kind_keys):
        found.append(("절차", f"절차의 이름으로 쓸 수 없는 말: {WHO_SECTION}, {ACT_SECTION}"))
    for kind in body.get("kinds", []):
        where = f"절차 {kind.get('key')}"
        if not str(kind.get("name", "")).strip() or not str(kind.get("en", "")).strip():
            found.append((where, "이름(name, en)이 비어 있음"))
        lead = kind.get("lead") or {}
        text(f"{where} 머리", lead.get("text"))
        found += basis_problems(f"{where} 머리", lead.get("basis"), sources, texts, kinds)
        lanes = kind.get("lanes") or []   # 없으면 화면이 기관별 줄 그림을 그리지 않는다(EU 기관이 하는 절차가 아닐 때)
        if lanes and (len(lanes) < 2 or not set(lanes) <= set(who) or len(set(lanes)) != len(lanes)):
            found.append((where, "줄(lanes)은 기관의 이름 둘 이상이어야 하고 겹치지 않아야 함"))
        steps = kind.get("steps") or []
        unique(f"{where} 단계", [step.get("key") for step in steps])
        if len([step for step in steps if not step.get("optional")]) < 2:
            found.append((where, "단계가 둘보다 적음"))
        reached = -1
        for step in steps:
            spot = f"{where} {step.get('key')}"
            if not str(step.get("name", "")).strip() or not str(step.get("part", "")).strip():
                found.append((spot, "이름(name)이나 묶음(part)이 비어 있음"))
            if not isinstance(step.get("who"), list) or not set(step.get("who") or []) <= set(who):
                found.append((spot, "하는 기관(who)이 기관의 이름이 아님"))
            text(spot, step.get("text"))
            found += basis_problems(spot, step.get("basis"), sources, texts, kinds)
            if "by" in step:
                text(f"{spot} by", step.get("by"))
            if "track" in step and not KEY.match(str(step["track"])):
                found.append((spot, "갈래(track)의 이름이 소문자·숫자·붙임표가 아님"))
            if "reach" in step:
                if not isinstance(step["reach"], int) or step["reach"] < reached:
                    found.append((spot, "큰 단계의 번호(reach)가 수가 아니거나 앞 단계보다 작음"))
                else:
                    reached = step["reach"]
        parts = [step.get("part") for step in steps]
        if any(part in parts[:index] and parts[index - 1] != part for index, part in enumerate(parts)):
            found.append((where, "같은 묶음(part)의 단계가 떨어져 있음"))
        for index, note in enumerate(kind.get("notes", []), start=1):
            spot = f"{where} 덧붙임 {index}"
            if not str(note.get("title", "")).strip():
                found.append((spot, "제목(title)이 비어 있음"))
            text(spot, note.get("text"))
            found += basis_problems(spot, note.get("basis"), sources, texts, kinds)

    places = anchors(body)
    seen = set()
    for term in body.get("terms", []):
        where = f"용어 {term.get('ko')}"
        if not str(term.get("ko", "")).strip() or not str(term.get("en", "")).strip() or term.get("ko") in seen:
            found.append((where, "국문 표기(ko)나 영문 표기(en)가 없거나 겹침"))
        seen.add(term.get("ko"))
        text(where, term.get("text"))
        if not isinstance(term.get("also", []), list) or any(not str(form).strip() for form in term.get("also", [])):
            found.append((where, "다른 표기(also)는 글의 목록이어야 함"))
        if term.get("at") not in places:
            found.append((where, f"없는 자리(at): {term.get('at')}"))
    cited = {one.get("source") for one in _all_basis(body) if isinstance(one, dict)}
    found += [(f"자료 {name}", "어느 글도 근거로 삼지 않는 자료") for name in sources if name not in cited]
    return found if "format" in kinds else [row for row in found if row[1].startswith(DRIFT)]


def _all_basis(body):
    """자료 안의 모든 근거를 차례로 내놓는다."""
    for one in body.get("institutions", []):
        for point in one.get("points", []):
            yield from point.get("basis") or []
    for one in body.get("acts", []) + body.get("codes", []):
        yield from one.get("basis") or []
    for kind in body.get("kinds", []):
        yield from (kind.get("lead") or {}).get("basis") or []
        for row in kind.get("steps", []) + kind.get("notes", []):
            yield from row.get("basis") or []


def _names(basis):
    """근거가 가리키는 자료의 이름들(차례대로, 겹치지 않게)."""
    return list(dict.fromkeys(one.get("source") for one in basis or [] if one.get("source")))


def public(body):
    """사이트에 실을 모양. 받아 둔 글의 경로와 찾는 말은 빼고, 글마다 근거가 된 자료의 이름만 남긴다. 쓰이지 않는 자료는 싣지 않는다."""
    used = []

    def cite(basis):
        names = _names(basis)
        used.extend(names)
        return names

    out = {"asOf": body.get("asOf", ""), "lead": body.get("lead", "")}
    out["institutions"] = [{**{key: one[key] for key in ("key", "name", "en", "aka", "role") if one.get(key)},
                            "points": [{"text": point["text"], "basis": cite(point.get("basis"))} for point in one.get("points", [])]}
                           for one in body.get("institutions", [])]
    out["acts"] = [{"key": one["key"], "name": one["name"], "en": one["en"], "text": one["text"], "basis": cite(one.get("basis"))} for one in body.get("acts", [])]
    out["codes"] = [{"code": one["code"], "text": one["text"], "basis": cite(one.get("basis"))} for one in body.get("codes", [])]
    out["kinds"] = []
    for kind in body.get("kinds", []):
        out["kinds"].append({
            "key": kind["key"], "name": kind["name"], "en": kind["en"], "lanes": kind.get("lanes", []),
            "lead": {"text": kind["lead"]["text"], "basis": cite(kind["lead"].get("basis"))},
            "steps": [{**{key: step[key] for key in ("key", "name", "part", "who", "text")}, **({"by": step["by"]} if step.get("by") else {}),
                       **({"optional": True} if step.get("optional") else {}), **({"track": step["track"]} if step.get("track") else {}),
                       "basis": cite(step.get("basis"))} for step in kind.get("steps", [])],
            "notes": [{"title": note["title"], "text": note["text"], "basis": cite(note.get("basis"))} for note in kind.get("notes", [])],
        })
    sources = body.get("sources") or {}
    out["sources"] = {name: {key: sources[name][key] for key in ("text", "url", "checkedOn", "read") if sources[name].get(key)}
                      for name in dict.fromkeys(used) if name in sources}
    return out


def gloss_terms(body):
    """글 속 용어 풀이에 더할 용어: [{"ko", "en", "abbr", "also", "text", "read"}]. read는 이 화면 안의 그 자리다."""
    return [{"ko": term["ko"], "en": term.get("en", ""), "abbr": term.get("abbr", ""), "also": list(term.get("also", [])), "text": term.get("text", ""),
             "read": f"#procedure-{term['at']}"} for term in (body or {}).get("terms", [])]


def kinds_by_key(body):
    return {kind.get("key"): kind for kind in (body or {}).get("kinds", [])}


def main(argv):
    body = read_json(argv[0] if argv else SOURCE, None)
    if body is None:
        print("자료를 읽지 못함")
        return 1
    found = problems(body)
    for where, what in found:
        print(f"문제: {where}: {what}")
    steps = sum(len(kind.get("steps", [])) for kind in body.get("kinds", []))
    stored = sum(1 for source in (body.get("sources") or {}).values() if "path" in source)
    print(f"기관 {len(body.get('institutions', []))}곳, 법령의 종류 {len(body.get('acts', []))}가지, 절차 {len(body.get('kinds', []))}가지(단계 {steps}개), "
          f"용어 {len(body.get('terms', []))}개, 자료 {len(body.get('sources') or {})}건(받아 둔 글 {stored}건), 문제 {len(found)}건")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
