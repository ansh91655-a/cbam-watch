"""인증서 비용 추정의 자료를 검사하고 사이트에 실을 모양으로 바꾼다.

자료는 둘이다.
- data/calc.json: 손으로 적는 규칙과 설명. 마크업, 부문 간 보정계수, 벤치마크의 연도 구간, 생산경로의 이름, 계산식, 화면에 싣는 설명 글.
  항목마다 그 내용이 적힌 법령 글(evidence)을 가리키고, 검사는 그 대목이 받아 둔 글에 실제로 있는지와 값이 대목에 들어 있는지를 본다.
- data/calc-goods.json: 받아 둔 법령의 표에서 프로그램이 만든 품목 자료(tools/calc/build.py). 검사는 표에서 다시 만들어 같은지를 본다.
꼴이 깨진 것은 '문제'이고 사이트 만들기를 멈춘다. 받아 둔 글과 달라진 것은 '근거 어긋남'으로 알리기만 한다(사이트는 앞의 값으로 계속 돈다).
검사: python -m tools.publish.calc   (문제가 있으면 0이 아닌 값으로 끝난다)
"""
import json
import pathlib
import re
import sys

from tools.calc import build
from tools.calc.source import Unreadable
from tools.common.jsonio import read_json

SOURCE = "data/calc.json"
GOODS = build.TARGET
STORED = (pathlib.Path("collected/archive"), pathlib.Path("originals/text"))  # 근거로 삼을 수 있는 받아 둔 글: 모아 둔 공식 기록, EU 집행위원회 문서에서 뽑은 본문
SECTORS = ("cement", "fertilisers", "steel", "aluminium", "hydrogen")
DRIFT = "근거 어긋남"
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_texts = {}


def _text(path):
    """받아 둔 글을 빈칸을 하나로 줄여 돌려준다. 저장소의 받아 둔 자료 폴더 밖이거나 없으면 None."""
    file = pathlib.Path(str(path))
    if not any(folder in file.parents for folder in STORED) or ".." in file.parts or not file.exists():
        return None
    if str(file) not in _texts:
        _texts[str(file)] = " ".join(file.read_text(encoding="utf-8").split())
    return _texts[str(file)]


def _phrases(evidence):
    contains = (evidence or {}).get("contains")
    return [contains] if isinstance(contains, str) else list(contains or [])


def evidence_problems(where, evidence, values=()):
    """근거 대목이 받아 둔 글에 있는지, 값들이 그 대목 안에 '10 %' 꼴로 들어 있는지 본다. 근거가 여럿이면(목록) 하나씩 본다."""
    if isinstance(evidence, list):
        return [row for one in evidence for row in evidence_problems(where, one, values)] if evidence else [(where, "근거 글의 경로나 대목이 없음")]
    phrases = _phrases(evidence)
    if not isinstance(evidence, dict) or not evidence.get("path") or not phrases:
        return [(where, "근거 글의 경로나 대목이 없음")]
    text = _text(evidence["path"])
    if text is None:
        return [(where, f"{DRIFT}: 근거 글이 없음: {evidence['path']}")]
    found = [(where, f"{DRIFT}: 글에 없는 대목 '{phrase[:60]}'") for phrase in phrases if " ".join(phrase.split()) not in text]
    joined = " ".join(phrases)
    found += [(where, f"{DRIFT}: 대목에 값 {value:g} %가 없음") for value in values if not re.search(rf"(?<![\d.,]){value:g}\s?%", joined)]
    return found


def _keys(entry):
    """항목이 가리키는 근거 자료의 열쇠들: source(하나)나 sources(여럿)로 적는다."""
    if isinstance(entry.get("sources"), list):
        return [key for key in entry["sources"] if isinstance(key, str)]
    return [entry["source"]] if isinstance(entry.get("source"), str) else []


def _years(values, low=0, high=100):
    return isinstance(values, dict) and values and all(re.match(r"^20\d\d$", str(year)) and isinstance(value, (int, float)) and low <= value <= high for year, value in values.items())


def terms_problems(terms):
    found = []
    if not DATE.match(str(terms.get("asOf", ""))):
        found.append(("기준일", "asOf가 날짜가 아님"))
    span = terms.get("years") or {}
    if not (isinstance(span.get("from"), int) and isinstance(span.get("to"), int) and 2026 <= span["from"] <= span["to"]):
        found.append(("연도", "years의 from과 to가 없거나 차례가 틀림"))
    # 마크업: 부문마다 꼭 한 번
    covered = [sector for group in terms.get("markups") or [] for sector in group.get("sectors") or []]
    if sorted(covered) != sorted(SECTORS):
        found.append(("마크업", f"부문이 빠지거나 겹침: {sorted(covered)}"))
    for index, group in enumerate(terms.get("markups") or []):
        where = f"마크업 {index + 1}"
        if not _years(group.get("values")) or "2026" not in group["values"]:
            found.append((where, "해마다의 값이 없거나 2026년 값이 없음"))
            continue
        found += evidence_problems(where, group.get("evidence"), group["values"].values())
    # 부문 간 보정계수
    cscf = terms.get("cscf") or {}
    if not _years(cscf.get("values")):
        found.append(("부문 간 보정계수", "해마다의 값이 없음"))
    else:
        found += evidence_problems("부문 간 보정계수", cscf.get("evidence"), set(cscf["values"].values()))
        phrase = " ".join(_phrases(cscf.get("evidence")))
        years = sorted(int(year) for year in cscf["values"])
        if f"{years[0]} to {years[-1]}" not in phrase:
            found.append(("부문 간 보정계수", f"{DRIFT}: 대목에 기간 '{years[0]} to {years[-1]}'이 없음"))
    # 벤치마크의 연도 구간: (1), (2)가 이어져 있어야 한다
    periods = terms.get("periods") or []
    if [period.get("key") for period in periods] != list(build.PERIODS) or any(not isinstance(period.get("from"), int) or not isinstance(period.get("to"), int) for period in periods):
        found.append(("연도 구간", f"구간이 {list(build.PERIODS)}의 차례로 있지 않음"))
    else:
        if any(later["from"] != earlier["to"] + 1 for earlier, later in zip(periods, periods[1:])) or periods[0]["from"] != 2026:
            found.append(("연도 구간", "구간이 2026년부터 이어져 있지 않음"))
        for period in periods:
            where = f"연도 구간 ({period['key']})"
            found += evidence_problems(where, period.get("evidence"))
            short = f"{period['from']}-{str(period['to'])[2:]}"
            if short not in " ".join(_phrases(period.get("evidence"))) or f"({period['key']})" not in " ".join(_phrases(period.get("evidence"))):
                found.append((where, f"{DRIFT}: 대목에 표시 ({period['key']})나 기간 '{short}'이 없음"))
    # 생산경로의 이름: '(C) Carbon Steel based on BF/BOF'가 표의 주석에 있어야 한다
    routes = terms.get("routes") or []
    keys = [route.get("key") for route in routes]
    if len(set(keys)) != len(keys) or any(not route.get("key") or not route.get("name") or not route.get("en") for route in routes):
        found.append(("생산경로", "열쇠가 겹치거나 이름이 빠짐"))
    else:
        text = _text((terms.get("routesEvidence") or {}).get("path", ""))
        if text is None:
            found.append(("생산경로", f"{DRIFT}: 근거 글이 없음"))
        else:
            found += [(f"생산경로 {route['key']}", f"{DRIFT}: 글에 '({route['key']}) {route['en']}'가 없음") for route in routes if f"({route['key']}) {route['en']}" not in text]
    # 계산식과 설명 글
    sources = {source.get("key") for source in terms.get("sources") or []}
    if any(not source.get("key") or not source.get("text") or not str(source.get("url", "")).startswith("https://") for source in terms.get("sources") or []) or not sources:
        found.append(("근거 자료", "열쇠, 이름, 주소 가운데 빠진 것이 있음"))
    formula = terms.get("formula") or {}
    if not formula.get("text") or not _keys(formula) or not set(_keys(formula)) <= sources:
        found.append(("계산식", "글이 없거나 근거 자료를 가리키지 않음"))
    else:
        found += evidence_problems("계산식", formula.get("evidence"))
    watch = terms.get("watch") or {}
    if not all(isinstance(watch.get(key), list) and watch[key] and all(isinstance(one, str) and one for one in watch[key]) for key in ("mentions", "known")):
        found.append(("지켜볼 법령", "watch의 mentions와 known이 글의 목록이 아님"))
    notes = terms.get("notes") or []
    if not notes or len({note.get("key") for note in notes}) != len(notes):
        found.append(("설명 글", "글이 없거나 열쇠가 겹침"))
    for note in notes:
        where = f"설명 글 {note.get('key', '?')}"
        if not note.get("text") or not _keys(note) or not set(_keys(note)) <= sources:
            found.append((where, "글이 없거나 근거 자료를 가리키지 않음"))
        else:
            found += evidence_problems(where, note.get("evidence"))
    return found


def goods_problems(terms, goods):
    """품목 자료의 꼴과, 받아 둔 표에서 다시 만든 것과 같은지."""
    rows, items = goods.get("rows"), goods.get("goods")
    if not isinstance(rows, list) or not isinstance(items, list) or not rows or not items:
        return [("품목 자료", f"{GOODS}에 행이나 품목이 없음")]
    found = []
    routes = {route.get("key") for route in terms.get("routes") or []} | {""}
    for index, row in enumerate(rows):
        number = all(isinstance(row.get(key), (int, float)) for key in ("direct", "total")) and (row.get("indirect") is None or isinstance(row["indirect"], (int, float)))
        if not row.get("shown") or row.get("origin") not in ("kr", "other") or not number or row["total"] <= 0 or not set(row.get("routes") or []) <= routes:
            found.append((f"기본값 행 {index}", "코드, 출처 표, 값, 경로 가운데 틀린 것이 있음"))
    codes = set()
    for good in items:
        where = f"품목 {good.get('shown', '?')}"
        variants = (good.get("a") or []) + (good.get("b") or [])
        fine = (re.match(r"^\d{8}$", str(good.get("code", ""))) and good["code"] not in codes and good.get("text") and good.get("sector") in SECTORS
                and good.get("a") and good.get("b")
                and all(len(one) == 3 and isinstance(one[0], (int, float)) and one[0] >= 0 and one[1] in routes and one[2] in (0,) + build.PERIODS for one in variants)
                and good.get("defaults")
                and all(isinstance(choice.get("row"), int) and 0 <= choice["row"] < len(rows) and choice.get("route") in routes
                        and isinstance(choice.get("benchmark"), list) and len(choice["benchmark"]) == len(build.PERIODS)
                        and all(isinstance(value, (int, float)) and value >= 0 for value in choice["benchmark"]) for choice in good["defaults"]))
        if not fine:
            found.append((where, "코드, 부문, 벤치마크 값, 기본값 짝 가운데 틀린 것이 있음"))
        codes.add(good.get("code"))
    if found:
        return found[:20]
    try:
        fresh = build.build()
    except Unreadable as problem:
        return [("품목 자료", f"{DRIFT}: 받아 둔 표를 읽지 못함: {problem}")]
    # 표의 번호나 표 앞의 글 같은 겉모습(builtFrom)은 견주지 않는다. 다시 받으면 번호가 달라질 수 있고, 값이 같으면 자료는 그대로다.
    if fresh["rows"] != goods["rows"] or fresh["goods"] != goods["goods"]:
        changed = sum(1 for old, new in zip(goods["goods"], fresh["goods"]) if old != new) + abs(len(goods["goods"]) - len(fresh["goods"]))
        return [("품목 자료", f"{DRIFT}: 받아 둔 표로 다시 만든 것과 다름(품목 {changed}개가 다름). python -m tools.calc.build 로 다시 만들고 달라진 것을 확인할 것")]
    return []


def problems(terms, goods):
    """[(자리, 문제)] 목록."""
    if not isinstance(terms, dict) or not isinstance(goods, dict):
        return [("비용 추정", f"자료({SOURCE}, {GOODS})를 읽지 못함")]
    return terms_problems(terms) + goods_problems(terms, goods)


def blocking(found):
    return [row for row in found if not row[1].startswith(DRIFT)]


def public(terms, goods):
    """사이트에 실을 모양. 저장소 안의 파일 경로와 대조용 대목은 빼고, 품목은 자리로 읽는 짧은 꼴로 줄인다.

    rows: [코드, 이름, 출처 표(kr 또는 other), 직접, 간접(없으면 null), 합계]
    goods: [코드, 이름, 부문, A열 값들, B열 값들, 기본값 짝들]  값은 [수, 경로, 연도 구간], 짝은 [행 자리, 경로, 2026~27년 벤치마크, 2028~30년 벤치마크]
    """
    sources = {source["key"]: {"text": source["text"], "url": source["url"]} for source in terms["sources"]}
    return {
        "asOf": terms["asOf"],
        "years": terms["years"],
        "markups": [{"sectors": group["sectors"], "values": group["values"]} for group in terms["markups"]],
        "cscf": terms["cscf"]["values"],
        "periods": [{"key": period["key"], "from": period["from"], "to": period["to"]} for period in terms["periods"]],
        "routes": [{"key": route["key"], "name": route["name"]} for route in terms["routes"]],
        "formula": {"text": terms["formula"]["text"], "sources": [sources[key] for key in _keys(terms["formula"])]},
        "notes": [{"key": note["key"], "text": note["text"], "sources": [sources[key] for key in _keys(note)]} for note in terms["notes"]],
        "sources": list(sources.values()),
        "korea": goods["builtFrom"]["defaults"]["korea"]["caption"],
        "rows": [[row["shown"], row["text"], row["origin"], row["direct"], row["indirect"], row["total"]] for row in goods["rows"]],
        "goods": [[good["code"], good["text"], good["sector"], good["a"], good["b"],
                   [[choice["row"], choice["route"]] + choice["benchmark"] for choice in good["defaults"]]] for good in goods["goods"]],
    }


def dump(body):
    """사이트에 싣는 파일의 글. 품목이 많아 빈칸 없이 적는다."""
    return json.dumps(body, ensure_ascii=False, separators=(",", ":")) + "\n"


def main():
    found = problems(read_json(SOURCE, None), read_json(GOODS, None))
    for where, what in found:
        print(f"{where}: {what}")
    if not found:
        print("비용 추정 자료: 문제 없음")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
