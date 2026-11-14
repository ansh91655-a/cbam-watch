"""글 속 용어 풀이의 자료(data/gloss.json)를 만든다: 소식, 규제, 해설서의 글에서 표시할 용어와 그 풀이.

- 표시하는 것: 해설서가 풀이한 용어(국문 표기와 약어)와 용어집의 약어. 용어집의 모든 국문 표기를 표시하지 않는 까닭은,
  일상어와 겹치는 말이 많아 그 뜻이 아닌 곳에도 표시가 붙기 때문이다. 해설서가 풀이한 용어는 처음 읽는 사람에게 필요한 것만 골라 둔 것이다.
- 무엇을 빼는지는 sources/gloss.json이 정한다(글마다 나오는 약어, 다른 말과 헷갈리는 두 글자 약어, 일상어로도 쓰는 국문 표기).
- 풀이는 해설서의 풀이를 앞세우고(높임말로 풀어 쓴 글이고, 그 용어를 다루는 절로 이어진다), 해설서에 없는 약어는 용어집의 풀이를 쓴다.
- 같은 표기가 두 용어에 걸리면 먼저 나온 용어가 그 표기를 가진다. 해설서의 용어가 용어집의 약어보다 앞선다(CN은 해설서의 'CN 코드'의 풀이로 간다).
- sources/gloss.json이 빼라고 한 말이 해설서나 용어집에 없으면 문제로 돌려준다(자료가 낡았다는 뜻이다).
- 범위(scope): 해설서의 장에 scope가 적혀 있으면(영국 CBAM의 장은 "uk") 그 장의 용어는 그 범위의 글에만 쓰고, 그 범위의 글에는 다른 용어를 쓰지 않는다.
  같은 낱말이라도 제도마다 뜻이 달라서다(영국 CBAM의 '회계기간', '인정기구'. 거꾸로 EU의 '과징금', '검증기관'의 풀이는 영국의 글에 맞지 않는다).
  그 범위의 글은 셋이다: 그 장, 이름이 같은 규제 묶음의 규제 화면, 그 묶음의 규제가 출처로 삼는 곳에서 온 소식(다른 묶음의 규제도 출처로 삼는 곳은 뺀다).
  용어집의 약어는 범위가 없는 글에만 쓴다. 표기의 임자는 범위마다 따로 가린다.
- 만드는 것: data/gloss.json
  {"terms": [{"forms": ["부문 간 보정계수", "CSCF"], "ko", "en", "abbr", "text", "read": "#handbook-<장>.<절>" 또는 "", "scope"?: "uk"}],
   "scopes": {"uk": [그 범위의 풀이를 쓰는 소식의 id, …]}}   scopes는 범위가 있는 용어가 있을 때만 싣는다
  forms는 글에서 찾는 표기다. 국문 표기는 띄어쓰기가 달라도 찾고, 영문 약어는 낱말 하나로 나온 곳만 찾는다(site/js/gloss/match.js).
  어느 글에 어느 범위의 용어를 쓰는지는 site/js/gloss/scope.js가 가린다.

쓰는 법: python -m tools.publish.gloss <사이트 폴더의 data>   (사이트 만들기가 부른다. 따로 돌리면 용어 수와 문제를 찍는다)
"""
import pathlib
import re
import sys

from tools.common.jsonio import read_json, write_json

SOURCE = "sources/gloss.json"
LATIN = re.compile(r"[A-Za-z0-9][A-Za-z0-9 /()\-]*$")


def abbreviations(text):
    """약어 칸의 글에서 찾을 표기들: "CCS / CCU(S)" → ["CCS", "CCU", "CCUS"], "PFCs" → ["PFC"], "EU ETS" → ["EU ETS"]."""
    found = []
    for piece in str(text or "").split(" / "):
        piece = piece.strip()
        if not piece or not LATIN.match(piece):
            continue
        optional = re.fullmatch(r"([A-Za-z0-9]+)\(([A-Za-z])\)", piece)   # CCU(S): 괄호 안의 글자가 붙은 꼴과 안 붙은 꼴
        if optional:
            found += [optional.group(1), optional.group(1) + optional.group(2)]
        elif re.fullmatch(r"[A-Z]{2,}s", piece):                          # 복수형으로 적은 약어는 단수형으로(글에서는 s가 붙은 꼴도 찾는다)
            found.append(piece[:-1])
        else:
            found.append(piece)
    return found


def scope_items(scopes, regulations, items):
    """범위마다 그 풀이를 쓸 소식의 id: {범위: [id]}. 그 이름의 규제 묶음에 속한 규제가 출처로 삼는 곳(related.sources)에서 온 소식이다.

    낱말로 이어진 소식(related.words)은 넣지 않는다: 다른 제도를 다루면서 그 이름을 한 번 든 글일 수 있다.
    regulations: 저장소의 규제 자료(data/regulations.json), items: 저장소의 소식(출처 코드 sourceCode가 있는 것).
    """
    groups = {}   # 출처 코드 → 그 출처를 적은 규제의 묶음들
    for rule in (regulations or {}).get("regulations", []):
        for code in (rule.get("related") or {}).get("sources", []):
            groups.setdefault(code, set()).add(rule.get("group"))
    found = {}
    for scope in scopes:
        codes = {code for code, named in groups.items() if named == {scope}}
        found[scope] = sorted(item["id"] for item in items or [] if item.get("sourceCode") in codes and not item.get("withdrawn"))
    return found


def build(rules, glossary, handbook, regulations=None, items=None):
    """(gloss.json의 내용, [(자리, 문제)]). rules: sources/gloss.json, glossary: data/terms.json, handbook: 사이트에 싣는 해설서(용어의 자리가 붙은 terms).
    regulations와 items(저장소의 규제 자료와 소식)는 범위가 있는 용어를 쓸 소식을 가리는 데 쓴다(scope_items)."""
    skip_abbr = set(rules.get("skipAbbr") or [])
    skip_ko = set(rules.get("skipKo") or [])
    entries = {}   # (범위, 영문 표기(소문자)) → 용어 하나. 범위가 없는 용어의 범위는 ""
    order = []

    def entry(scope, en, ko):
        key = (scope, str(en or ko).strip().lower())
        if key not in entries:
            entries[key] = {"forms": [], "ko": ko, "en": en or "", "abbr": "", "text": "", "read": "", **({"scope": scope} if scope else {})}
            order.append(key)
        return entries[key]

    seen_abbr, seen_ko = set(), set()
    for term in (handbook or {}).get("terms", []):   # 해설서가 풀이한 용어: 국문 표기와 약어
        one = entry(str(term.get("scope") or ""), term.get("en"), term.get("ko", ""))
        one.update({"ko": term.get("ko", ""), "text": term.get("text", ""), "read": f"#handbook-{term['chapter']}.{term['section']}"})
        seen_ko.add(one["ko"])
        if one["ko"] and one["ko"] not in skip_ko:
            one["forms"].append(one["ko"])
        if term.get("abbr"):
            one["abbr"] = term["abbr"]
    for term in (glossary or {}).get("terms", []):   # 용어집의 약어(해설서의 용어와 같은 말이면 그 용어에 붙인다). 범위가 없는 글에만 쓴다
        if not term.get("abbr"):
            continue
        key = ("", str(term.get("en") or term.get("ko")).strip().lower())
        if key not in entries and term["abbr"] in skip_abbr:
            seen_abbr.add(term["abbr"])
            continue
        one = entry("", term.get("en"), term.get("ko", ""))
        one["abbr"] = one["abbr"] or term["abbr"]
        if not one["text"]:
            one["text"] = term.get("note", "")
    taken = {}   # 범위 → 이미 임자가 있는 표기(빈칸을 빼고 견준다). 그 범위에서 먼저 나온 용어가 가진다
    for key in order:
        one = entries[key]
        mine = taken.setdefault(key[0], set())
        seen_abbr.add(one["abbr"])
        wanted = one["forms"] + (abbreviations(one["abbr"]) if one["abbr"] and one["abbr"] not in skip_abbr else [])
        one["forms"] = []
        for form in wanted:
            mark = re.sub(r"\s+", "", form)
            if mark not in mine:
                mine.add(mark)
                one["forms"].append(form)

    problems = []
    problems += [("빼는 약어", f"용어집과 해설서에 없는 약어: {name}") for name in sorted(skip_abbr - seen_abbr)]
    problems += [("빼는 국문 표기", f"해설서가 풀이하지 않는 말: {name}") for name in sorted(skip_ko - seen_ko)]
    terms = [entries[key] for key in order if entries[key]["forms"] and entries[key]["text"]]
    body = {"terms": terms}
    scopes = sorted({term["scope"] for term in terms if term.get("scope")})
    if scopes:
        body["scopes"] = scope_items(scopes, regulations, items)
    return body, problems


def write(data_out, glossary, handbook, regulations=None, items=None):
    """data/gloss.json을 쓰고 (용어 수, 문제)를 돌려준다. 문제가 있으면 쓰지 않는다(그때는 글에 표시가 붙지 않을 뿐 사이트는 그대로다)."""
    rules = read_json(SOURCE, None)
    if not isinstance(rules, dict):
        return 0, [("글 속 용어 풀이", f"자료({SOURCE})를 읽지 못함")]
    body, problems = build(rules, glossary, handbook, regulations, items)
    if problems:
        return 0, problems
    write_json(pathlib.Path(data_out) / "gloss.json", body)
    return len(body["terms"]), []


def main(argv):
    if len(argv) != 1:
        print(__doc__.strip().splitlines()[-1].strip())
        return 2
    data_out = pathlib.Path(argv[0])
    count, problems = write(data_out, read_json(data_out / "terms.json", {}), read_json(data_out / "handbook.json", {}),
                            read_json("data/regulations.json", {}), (read_json("data/items.json", {}) or {}).get("items", []))
    print(f"글 속 용어 풀이: 용어 {count}개, 문제 {len(problems)}건")
    for where, problem in problems:
        print(f"- {where}: {problem}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
