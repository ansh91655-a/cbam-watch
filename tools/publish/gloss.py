"""글 속 용어 풀이의 자료(data/gloss.json)를 만든다: 소식, 규제, 해설서의 글에서 표시할 용어와 그 풀이.

- 표시하는 것: 해설서가 풀이한 용어(국문 표기와 약어)와 용어집의 약어. 용어집의 모든 국문 표기를 표시하지 않는 까닭은,
  일상어와 겹치는 말이 많아 그 뜻이 아닌 곳에도 표시가 붙기 때문이다. 해설서가 풀이한 용어는 처음 읽는 사람에게 필요한 것만 골라 둔 것이다.
- 무엇을 빼는지는 sources/gloss.json이 정한다(글마다 나오는 약어, 다른 말과 헷갈리는 두 글자 약어, 일상어로도 쓰는 국문 표기).
- 풀이는 해설서의 풀이를 앞세우고(높임말로 풀어 쓴 글이고, 그 용어를 다루는 절로 이어진다), 해설서에 없는 약어는 용어집의 풀이를 쓴다.
- 같은 표기가 두 용어에 걸리면 먼저 나온 용어가 그 표기를 가진다. 해설서의 용어가 용어집의 약어보다 앞선다(CN은 해설서의 'CN 코드'의 풀이로 간다).
- sources/gloss.json이 빼라고 한 말이 해설서나 용어집에 없으면 문제로 돌려준다(자료가 낡았다는 뜻이다).
- 만드는 것: data/gloss.json
  {"terms": [{"forms": ["부문 간 보정계수", "CSCF"], "ko", "en", "abbr", "text", "read": "#handbook-<장>.<절>" 또는 ""}]}
  forms는 글에서 찾는 표기다. 국문 표기는 띄어쓰기가 달라도 찾고, 영문 약어는 낱말 하나로 나온 곳만 찾는다(site/js/gloss/match.js).

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


def build(rules, glossary, handbook):
    """(gloss.json의 내용, [(자리, 문제)]). rules: sources/gloss.json, glossary: data/terms.json, handbook: 사이트에 싣는 해설서(용어의 자리가 붙은 terms)."""
    skip_abbr = set(rules.get("skipAbbr") or [])
    skip_ko = set(rules.get("skipKo") or [])
    entries = {}   # 영문 표기(소문자) → 용어 하나
    order = []

    def entry(en, ko):
        key = str(en or ko).strip().lower()
        if key not in entries:
            entries[key] = {"forms": [], "ko": ko, "en": en or "", "abbr": "", "text": "", "read": ""}
            order.append(key)
        return entries[key]

    seen_abbr, seen_ko = set(), set()
    for term in (handbook or {}).get("terms", []):   # 해설서가 풀이한 용어: 국문 표기와 약어
        one = entry(term.get("en"), term.get("ko", ""))
        one.update({"ko": term.get("ko", ""), "text": term.get("text", ""), "read": f"#handbook-{term['chapter']}.{term['section']}"})
        seen_ko.add(one["ko"])
        if one["ko"] and one["ko"] not in skip_ko:
            one["forms"].append(one["ko"])
        if term.get("abbr"):
            one["abbr"] = term["abbr"]
    for term in (glossary or {}).get("terms", []):   # 용어집의 약어(해설서의 용어와 같은 말이면 그 용어에 붙인다)
        if not term.get("abbr"):
            continue
        key = str(term.get("en") or term.get("ko")).strip().lower()
        if key not in entries and term["abbr"] in skip_abbr:
            seen_abbr.add(term["abbr"])
            continue
        one = entry(term.get("en"), term.get("ko", ""))
        one["abbr"] = one["abbr"] or term["abbr"]
        if not one["text"]:
            one["text"] = term.get("note", "")
    taken = set()   # 이미 임자가 있는 표기(빈칸을 빼고 견준다). 먼저 나온 용어가 가진다
    for key in order:
        one = entries[key]
        seen_abbr.add(one["abbr"])
        wanted = one["forms"] + (abbreviations(one["abbr"]) if one["abbr"] and one["abbr"] not in skip_abbr else [])
        one["forms"] = []
        for form in wanted:
            mark = re.sub(r"\s+", "", form)
            if mark not in taken:
                taken.add(mark)
                one["forms"].append(form)

    problems = []
    problems += [("빼는 약어", f"용어집과 해설서에 없는 약어: {name}") for name in sorted(skip_abbr - seen_abbr)]
    problems += [("빼는 국문 표기", f"해설서가 풀이하지 않는 말: {name}") for name in sorted(skip_ko - seen_ko)]
    terms = [entries[key] for key in order if entries[key]["forms"] and entries[key]["text"]]
    return {"terms": terms}, problems


def write(data_out, glossary, handbook):
    """data/gloss.json을 쓰고 (용어 수, 문제)를 돌려준다. 문제가 있으면 쓰지 않는다(그때는 글에 표시가 붙지 않을 뿐 사이트는 그대로다)."""
    rules = read_json(SOURCE, None)
    if not isinstance(rules, dict):
        return 0, [("글 속 용어 풀이", f"자료({SOURCE})를 읽지 못함")]
    body, problems = build(rules, glossary, handbook)
    if problems:
        return 0, problems
    write_json(pathlib.Path(data_out) / "gloss.json", body)
    return len(body["terms"]), []


def main(argv):
    if len(argv) != 1:
        print(__doc__.strip().splitlines()[-1].strip())
        return 2
    data_out = pathlib.Path(argv[0])
    count, problems = write(data_out, read_json(data_out / "terms.json", {}), read_json(data_out / "handbook.json", {}))
    print(f"글 속 용어 풀이: 용어 {count}개, 문제 {len(problems)}건")
    for where, problem in problems:
        print(f"- {where}: {problem}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
