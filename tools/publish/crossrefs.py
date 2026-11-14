"""소식, 의무 일정, 용어집에 적힌 법령과 조문을 사이트의 규정 원문(#law-<문서>.<조각>)으로 잇는다.

- 잇는 것은 글에 법령과 조문이 또렷이 적힌 곳뿐이다. 어림하지 않는다.
  법령은 번호((EU) 2025/2547)나 이름(CBAM 규정, 사이트가 싣는 법령의 이름)으로 알아보고, 조와 부속서는 그 법령 바로 뒤에 이어 적힌 것만 그 법령의 것으로 본다
  ("CBAM 규정 제6조(1), 제22조(1)", "(EU) 2025/2621의 부속서 I과 부속서 IV", "CBAM 규정 제32조~제35조").
  법령 없이 적힌 "제1조"나 다른 법의 조문("EU 기능조약 제192조", "EEA 협정의 부속서 XX")은 잇지 않는다.
- 소식의 글에서는 이름만 적힌 법령("CBAM 규정은 …")을 잇지 않는다(거의 모든 소식에 나오는 말이다). 번호가 적힌 법령은 문서로 잇는다.
  손으로 적는 근거 칸(의무 일정의 basis, 용어집의 article)에서는 이름만 적혀 있어도 그 문서로 잇는다.
- 적힌 조각이 사이트의 글에 없으면 잇지 않는다. 근거 칸에서 그런 것은 알린다(근거를 잘못 적었거나 받아 둔 글이 제대로 갈리지 않은 것이다).
- 만드는 것: data/refs.json
  {"items": {소식 id: [{"act", "part", "label"}]}, "duties": {의무 id: […]}, "terms": {용어의 영문: […]},
   "laws": {문서 id: {조각 id(문서 전체는 ""): {"items": [{"id", "title", "date"}], "duties": [{"id", "title", "date"}], "terms": [{"en", "ko"}], "more": 다 싣지 못한 소식의 수}}}}
  제목만 실은 소식(brief)에는 "link"(원문 주소)가 함께 실린다. 해마다 돌아오는 의무는 조각마다 다가오는 것 하나만 싣는다.
- 해설서로 돌아가는 길도 함께 만든다(해설서의 글이 스스로 적어 둔 것을 뒤집은 것이다. 새로 어림하는 것은 없다):
  해설서의 절이 근거로 든 조각에는 그 절을 싣고("laws"의 조각마다 "handbook": [{"href", "title", "chapter"}]),
  "read": {"terms": {용어의 영문(소문자): {"href", "title", "chapter"}}, "rules": {규제 id: [{"href", "title", "chapter"}]}}에는
  해설서가 풀이한 용어의 절과, 관련 화면으로 그 규제를 가리킨 절을 싣는다.

쓰는 법: python -m tools.publish.crossrefs <사이트 폴더의 data>   (사이트 만들기가 부른다. 따로 돌리면 이어진 수와 문제를 찍는다)
"""
import pathlib
import re
import sys

from tools.common.jsonio import read_json, today, write_json

BASE = "32023R0956"
# 번호 없이 이름으로 가리키는 법령. 사이트가 싣는 법령의 이름(목록의 name)은 저절로 더해진다. 아래는 용어집이 쓰는 줄인 이름이다.
ALIASES = {"CBAM 규정": BASE, "배출량 산정방법 이행규정": "32025R2547", "검증 원칙 이행규정": "32025R2546", "인정·검증 요건 위임규정": "32025R2551"}
OTHERS = ("영국", "UK")    # 이 말이 앞에 붙은 "CBAM 규정"은 EU의 규정이 아니다

NUMBER = re.compile(r"\(E[UC]\)\s*(?:No\s*)?(\d{4})/(\d+)")
GAP = re.compile(r"\s*(?:의\s*)?")
PART = re.compile(r"제\s?(\d+)([a-z]{0,2})조|부속서\s?([IVX]+)(?![A-Za-z])|전문")
MORE_ANNEX = re.compile(r"([IVX]+)(?![A-Za-z])")       # "부속서 I·II"의 뒤쪽
SUB = re.compile(r"(?:\([0-9A-Za-z]+\))*")              # 항과 호: (1), (7a), (c)
JOIN = re.compile(r"\s*(,|·|ㆍ|과|와|및|~)\s*")
FOLDED = {"front": "제목과 근거", "recitals": "전문", "closing": "맺음", "notes": "각주"}
ITEM_FIELDS = ("title", "summary", "impact")
ITEMS_PER_PART = 12


def book(index):
    """규정 원문의 목록(laws/index.json)에서 잇는 데 쓰는 것을 뽑는다: 번호와 이름으로 법령을 찾는 표, 법령마다의 조각."""
    acts = [act for act in (index or {}).get("acts", []) if act.get("group", "act") == "act"]
    numbers, names = {}, {}
    for act in acts:
        found = NUMBER.search(str(act.get("official", "")))
        if found:
            numbers[(found.group(1), str(int(found.group(2))))] = act["id"]
        if act.get("name"):
            names[act["name"]] = act["id"]
    names.update({name: act_id for name, act_id in ALIASES.items() if any(act["id"] == act_id for act in acts)})
    return {"acts": {act["id"]: act for act in acts}, "numbers": numbers,
            "names": sorted(names.items(), key=lambda pair: -len(pair[0])),   # 긴 이름부터 본다("기본값 이행규정의 정정 규정"이 "기본값 이행규정"보다 먼저)
            "parts": {act["id"]: {part["id"]: part for part in act.get("toc", [])} for act in acts}}


def _mentions(text, known):
    """글에 나온 법령: [(시작, 끝, 문서 id, 번호로 적혔는가)]를 자리의 차례로. 겹치는 이름은 긴 것 하나만 남긴다."""
    found = []
    for hit in NUMBER.finditer(text):
        act_id = known["numbers"].get((hit.group(1), str(int(hit.group(2)))))
        if act_id:
            found.append((hit.start(), hit.end(), act_id, True))
    taken = []
    for name, act_id in known["names"]:
        for hit in re.finditer(re.escape(name), text):
            if any(start < hit.end() and hit.start() < end for start, end in taken):
                continue
            taken.append((hit.start(), hit.end()))
            if name == "CBAM 규정" and text[:hit.start()].rstrip().endswith(OTHERS):
                continue
            found.append((hit.start(), hit.end(), act_id, False))
    return sorted(found)


def _part_name(part_id):
    """조각 id를 읽기 좋게: art-2a → 제2a조, annex-iv → 부속서 IV."""
    kind, _, number = part_id.partition("-")
    return f"제{number}조" if kind == "art" else f"부속서 {number.upper()}" if kind == "annex" else FOLDED.get(part_id, part_id)


def _part_id(hit):
    if hit.re is MORE_ANNEX:
        return f"annex-{hit.group(1).lower()}"
    if hit.group(1):
        return f"art-{hit.group(1)}{hit.group(2)}"
    return f"annex-{hit.group(3).lower()}" if hit.group(3) else "recitals"


def _tail(text, cursor):
    """법령 바로 뒤에 이어 적힌 조와 부속서의 조각 id들, 그리고 읽고 난 자리. "제32조~제35조"는 사이의 조도 넣는다."""
    found, joined, annex = [], "", False
    cursor = GAP.match(text, cursor).end()
    while True:
        hit = PART.match(text, cursor) or (MORE_ANNEX.match(text, cursor) if annex else None)
        if not hit:
            break
        part = _part_id(hit)
        if joined == "~" and found and re.fullmatch(r"art-\d+", found[-1]) and re.fullmatch(r"art-\d+", part):
            found += [f"art-{number}" for number in range(int(found[-1][4:]) + 1, int(part[4:]))]
        found.append(part)
        annex = part.startswith("annex-")
        cursor = SUB.match(text, hit.end()).end()
        more = JOIN.match(text, cursor)
        if not more:
            break
        joined, cursor = more.group(1), more.end()
    return found, cursor


def found(text, known, bare=False):
    """글에 적힌 법령과 조각: ([(문서 id, 조각 id)], [사이트의 글에 없는 조각]). 조각 id가 ""이면 문서 전체다.

    bare가 참이면 이름만 적힌 법령도 문서로 잇는다(손으로 적은 근거 칸).
    """
    text = str(text or "")
    refs, missing = [], []
    mentions = _mentions(text, known)
    for at, (start, end, act_id, numbered) in enumerate(mentions):
        parts, _ = _tail(text, end)
        if not parts:
            # 이름 바로 뒤에 같은 법령의 번호가 이어지면("CBAM 규정 (EU) 2023/956 제6조") 번호 쪽이 읽는다
            follows = at + 1 < len(mentions) and mentions[at + 1][2] == act_id and not text[end:mentions[at + 1][0]].strip(" (")
            if (numbered or bare) and not follows:
                refs.append((act_id, ""))
            continue
        for part in parts:
            if part in known["parts"].get(act_id, {}):
                refs.append((act_id, part))
            elif part != "recitals":   # 통합본에는 전문이 없다. 근거를 잘못 적은 것이 아니므로 알리지 않는다
                missing.append(f"{known['acts'][act_id].get('name', act_id)} {_part_name(part)}")
    seen = set()
    return [ref for ref in refs if not (ref in seen or seen.add(ref))], missing


def label(known, act_id, part_id):
    """이은 곳의 이름: "CBAM 규정 제6조 CBAM 신고", "기본값 이행규정 부속서 I", 문서 전체이면 문서의 이름."""
    act = known["acts"][act_id]
    part = known["parts"][act_id].get(part_id)
    if not part:
        return act.get("name", act_id)
    name = FOLDED.get(part["kind"]) or " ".join(text for text in (part.get("ko") or "", part.get("titleKo") or "") if text)
    return f"{act.get('name', act_id)} {name}"


def _row(known, refs):
    return [{"act": act_id, "part": part_id, "label": label(known, act_id, part_id)} for act_id, part_id in refs]


def _next_of_each(duties, day):
    """해마다 돌아오는 의무는 하나만: 오늘 뒤의 가장 가까운 것, 모두 지났으면 마지막 것."""
    groups = {}
    for duty in sorted(duties, key=lambda row: row["date"]):
        base = re.sub(r"-\d{4}$", "", duty["id"]) if duty.get("repeat") else duty["id"]
        kept = groups.get(base)
        if kept is None or kept["date"] < day:
            groups[base] = duty
    return sorted(groups.values(), key=lambda row: row["date"])


RULE_VIEW = re.compile(r"^#rules-([a-z0-9-]+)$")


def _handbook(body, place, handbook, rule_ids):
    """해설서의 절에서 근거 조각, 풀이한 용어, 가리킨 규제로 돌아가는 길을 body에 싣는다. handbook은 사이트에 싣는 해설서(handbook.public)다."""
    read = body["read"]
    for chapter in (handbook or {}).get("chapters", []):
        for section in chapter.get("sections", []):
            here = {"href": f"#handbook-{chapter['id']}.{section['id']}", "title": section.get("title", ""), "chapter": chapter.get("title", "")}
            for basis in section.get("basis", []):
                if not basis.get("act"):
                    continue
                listed = place(basis["act"], basis.get("part", "")).setdefault("handbook", [])
                if here not in listed:
                    listed.append(here)
            for term in [] if chapter.get("scope") else section.get("terms") or []:   # 다른 제도를 다루는 장(scope)의 풀이는 용어집의 용어와 잇지 않는다
                if term.get("en"):
                    read["terms"].setdefault(term["en"].lower(), here)   # 영문 표기의 대소문자는 가리지 않는다
            for link in section.get("see") or []:
                hit = RULE_VIEW.match(str(link.get("href", "")))
                if hit and (rule_ids is None or hit.group(1) in rule_ids) and here not in read["rules"].setdefault(hit.group(1), []):
                    read["rules"][hit.group(1)].append(here)


def build(index, items, duties, terms, day, handbook=None, rule_ids=None):
    """(refs.json의 내용, [(자리, 문제)]). handbook: 사이트에 싣는 해설서, rule_ids: 규제의 id들(주면 규제 묶음의 주소와 가른다)."""
    known = book(index)
    body = {"items": {}, "duties": {}, "terms": {}, "laws": {}, "read": {"terms": {}, "rules": {}}}
    problems = []

    def place(act_id, part_id):
        return body["laws"].setdefault(act_id, {}).setdefault(part_id, {"items": [], "duties": [], "terms": []})

    for item in sorted(items or [], key=lambda row: str(row.get("published", "")), reverse=True):
        if item.get("withdrawn"):
            continue
        # 칸(제목, 요약, 실무 영향)은 띄어쓰기가 아닌 글자로 갈라 잇는다: 제목 끝의 법령과 요약 첫머리의 조가 한데 이어지지 않게
        refs, _ = found(" | ".join(str(item.get(field, "")) for field in ITEM_FIELDS), known)
        if refs:
            body["items"][item["id"]] = _row(known, refs)
        for act_id, part_id in refs:
            row = {"id": item["id"], "title": item.get("title", ""), "date": item.get("published", "")}
            if item.get("brief"):   # 제목만 실은 소식은 요약 화면이 없다. 원문으로 바로 간다
                row["link"] = item.get("link", "")
            place(act_id, part_id)["items"].append(row)

    linked = {}
    for duty in duties or []:
        refs, missing = found(duty.get("basis", ""), known, bare=True)
        problems += [(f"의무 {duty['id']}", f"근거에 적힌 조각이 사이트의 규정 원문에 없음: {name}") for name in missing]
        if refs:
            body["duties"][duty["id"]] = _row(known, refs)
            linked[duty["id"]] = refs
    for duty in _next_of_each([duty for duty in duties or [] if duty["id"] in linked], day):
        for act_id, part_id in linked[duty["id"]]:
            place(act_id, part_id)["duties"].append({"id": duty["id"], "title": duty.get("title", ""), "date": duty.get("date", "")})

    for term in terms or []:
        refs, missing = found(term.get("article", ""), known, bare=True)
        problems += [(f"용어 {term.get('en', '?')}", f"근거에 적힌 조각이 사이트의 규정 원문에 없음: {name}") for name in missing]
        if refs:
            body["terms"][term["en"]] = _row(known, refs)
        for act_id, part_id in refs:
            place(act_id, part_id)["terms"].append({"en": term["en"], "ko": term.get("ko", "")})

    _handbook(body, place, handbook, rule_ids)

    for parts in body["laws"].values():
        for row in parts.values():
            row["more"] = max(0, len(row["items"]) - ITEMS_PER_PART)   # 다 싣지 못한 소식의 수
            row["items"] = row["items"][:ITEMS_PER_PART]
    return body, problems


def write(data_out, items, duties, terms, day, rule_ids=None):
    """data/refs.json을 쓰고 (이어진 수, 문제)를 돌려준다. 규정 원문의 목록(laws/index.json)과 해설서(handbook.json)가 먼저 만들어져 있어야 한다."""
    data_out = pathlib.Path(data_out)
    body, problems = build(read_json(data_out / "laws" / "index.json", {}), items, duties, terms, day, read_json(data_out / "handbook.json", None), rule_ids)
    write_json(data_out / "refs.json", body)
    counts = {name: len(body[name]) for name in ("items", "duties", "terms")}
    counts["handbook"] = sum(1 for parts in body["laws"].values() for row in parts.values() if row.get("handbook"))   # 해설서의 절로 돌아가는 조각의 수
    return counts, problems


def source_problems(day=None):
    """저장소의 자료로 본 문제(상태 점검이 쓴다): 의무 일정과 용어집의 근거에 적힌 조나 부속서가 사이트의 규정 원문에 없는 것."""
    from tools.laws import corpus
    from tools.publish import duties as duty_book

    acts = [{"id": act["id"], "group": "act", "name": act.get("name", ""), "official": act.get("official", ""),
             "toc": [{"id": part["id"], "kind": part["kind"], "ko": corpus.label_ko(part)} for part in corpus.read(act)]}
            for act in corpus.documents() if act.get("group", "act") == "act"]
    duties = (read_json(duty_book.SOURCE, {}) or {}).get("duties", [])
    terms = (read_json("data/terms.json", {}) or {}).get("terms", [])
    return build({"acts": acts}, [], duties, terms, day or today())[1]


def main(argv):
    if len(argv) != 1:
        print(__doc__.strip().splitlines()[-1].strip())
        return 2
    data_out = pathlib.Path(argv[0])
    counts, problems = write(data_out, read_json(data_out / "items.json", {}).get("items", []), read_json(data_out / "duties.json", {}).get("duties", []),
                             read_json(data_out / "terms.json", {}).get("terms", []), today())
    print(f"규정 원문으로 이은 것: 소식 {counts['items']}건, 의무 {counts['duties']}건, 용어 {counts['terms']}건, 문제 {len(problems)}건")
    for where, problem in problems:
        print(f"- {where}: {problem}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
