"""역할별 준비 목록(#prepare): 역할마다 챙길 일을 해설서의 절과 의무 일정에서 골라 차례로 놓은 것.

원본은 data/prepare.json이다. 새로 적는 사실은 없다. 항목의 글은 해설서의 절(from)과 의무 일정(duty)의 글을 줄인 것이고, 검사가 그것을 본다.
- roles: 역할의 목록(차례대로). 역할의 key는 의무 일정의 역할(data/duties.json의 roles)이어야 하고, 이름과 설명은 그쪽 것을 쓴다.
  역할마다 about(이 화면에 적는 한두 문장의 설명. 없으면 의무 일정의 설명)과 groups(묶음)가 있고, 묶음에는 name과 items가 있다.
- 항목
  id     주소(#prepare-<역할>.<id>)와 '확인함' 표시에 쓰는 이름. 파일 전체에서 겹치지 않는다.
  title  명사로 끝나는 구. 의무 일정에 기대는 항목은 비워 두면 그 일정의 제목을 쓴다.
  text   글. 의무 일정에 기대는 항목은 비워 두면 그 일정의 글을 쓴다(note가 있으면 그 글).
  from   해설서의 절("장.절")의 목록. 의무 일정에만 기대는 항목은 없어도 된다.
  duty   의무 일정의 id. 해마다 돌아오는 의무는 원래 id를 적는다(화면이 다가오는 해의 일정을 고른다).
         그런 의무에 기대는 항목이 제 말로 적은 title과 text는 첫 일정에 관한 것이다. 그 일정이 지나면 화면은 일정의 제목과 글을 쓴다(site/js/prepare/plan.js의 resolve).
  note   의무 일정의 글 가운데 무엇을 쓸지: "supplier"(생산자가 준비할 것), "verifier"(검증기관이 알아 둘 것). 없으면 일정의 글.
  refs   근거 조문 [{act, part}]. from에 적은 절의 근거에 있는 것만 적을 수 있다.
  tool   사이트의 화면으로 가는 링크 {href, text}.
검사는 다음을 본다.
- 꼴: 값이 다 있는지, id가 겹치지 않는지, 글이 표기 규칙(높임말, 용어집)에 맞는지, 권유나 전망의 말이 없는지(분석 글과 같은 기준).
- 잇는 곳: 해설서의 절, 의무 일정, 근거 조문, 화면의 주소가 실제로 있는지. refs가 그 절의 근거에 있는지.
- 사실: 글에 적힌 날짜와 수가 그 항목이 기대는 글(해설서의 절, 의무 일정)에 적혀 있는지. 날짜는 통째로, 수는 뒤의 한 글자까지 같은 것이 있어야 한다
  ("1월 1일"은 "11월 1일"로, "50톤"은 "150톤"으로 채워지지 않는다). '두 달', '네 번째'처럼 우리말로 적은 수도 본다.
  묶음의 이름과 역할의 설명에 적힌 날짜와 수는 그 묶음, 그 역할의 항목들이 기대는 글에 있어야 한다. 소개와 알림에는 날짜와 수를 적지 않는다.
만드는 것: 사이트의 data/prepare.json. 절의 이름과 근거 조문의 이름을 붙인다. 일정의 날짜와 글은 화면이 의무 일정(duties.json)에서 읽는다
  (의무 일정을 읽지 못한 화면을 위해, 일정에만 기대는 항목에는 그 일정의 제목과 글을 fallback으로 함께 싣는다).

검사: python -m tools.publish.prepare   (문제가 있으면 0이 아닌 값으로 끝난다. 규정 원문의 조문 이름까지 보려면 만든 사이트의 data 폴더를 넘긴다)
"""
import pathlib
import re
import sys

from tools.common.jsonio import read_json, write_json
from tools.publish import analysis, crossrefs, duties as duty_book, handbook, regulations

SOURCE = "data/prepare.json"
ID = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")
ID_MAX = 40   # 화면이 '확인함' 표시를 남길 때 받아들이는 길이(site/js/prepare/done.js)와 같다
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
NOTES = ("supplier", "verifier")
LIMITS = {"title": 40, "text": 330, "lead": 220, "note": 260, "group": 30, "tool": 24}
FULL_DATE = re.compile(r"\d{4}년\d{1,2}월\d{1,2}일")
MONTH_DAY = re.compile(r"(?<!\d)\d{1,2}월\d{1,2}일")
NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?(?:%|[가-힣])?")
DOTTED_DATE = re.compile(r"\d{4}\.\s?\d{1,2}\.\s?\d{1,2}")   # 이 꼴의 날짜는 쓰지 않는다(수로 읽혀 대조를 비켜 간다)
# 우리말로 적은 수: '두 달', '한 해', '네 번째', '열흘'. 낱말의 첫머리에서만 읽는다('제출한 해'의 '한 해'는 수가 아니다)
WORD_NUMBER = re.compile(r"(?<![가-힣])(?:(?:한|두|세|네|다섯|여섯|일곱|여덟|아홉|열)\s?(?:달|해|주|번째|번|차례|가지|배|곳|쪽)|첫\s?(?:번째|해|달)|이틀|사흘|나흘|열흘|보름)")


def _plain(text):
    """빈칸을 모두 뺀 글(날짜와 수를 띄어쓰기와 상관없이 견주려고)."""
    return "".join(str(text or "").split())


def facts(text):
    """글에 적힌 날짜와 수. 날짜는 통째로("2027년9월30일", "9월30일"), 그 밖의 수는 뒤의 한 글자까지("50톤", "50%", "3배"), 우리말로 적은 수는 빈칸을 빼고("두달")."""
    plain = _plain(text)
    found = FULL_DATE.findall(plain)
    rest = FULL_DATE.sub(" ", plain)
    found += MONTH_DAY.findall(rest)
    rest = MONTH_DAY.sub(" ", rest)
    found += [token.rstrip(",.") for token in NUMBER.findall(rest)]
    return found + [_plain(word) for word in WORD_NUMBER.findall(str(text or ""))]


def source_facts(text):
    """기대는 글에 적힌 날짜와 수의 묶음. 날짜는 그 일부로도 쓸 수 있게 풀어 둔다: "2027년 9월 30일"이 있으면 "9월 30일", "2027년", "9월"도 있는 것으로 본다.
    날만 따로("30일")는 풀지 않는다('30일 안에'의 30일과 다른 것이다)."""
    found = set(facts(text))
    for date in [fact for fact in found if FULL_DATE.fullmatch(fact)]:
        year, rest = date.split("년", 1)
        found.update({f"{year}년", rest})
    for date in [fact for fact in found if MONTH_DAY.fullmatch(fact)]:
        found.add(date.split("월", 1)[0] + "월")
    return found


def _strings(node):
    """자료 안의 모든 글(그림과 표, 식의 글까지)."""
    if isinstance(node, str):
        yield node
    elif isinstance(node, (int, float)) and not isinstance(node, bool):
        yield str(node)   # 그림에 수로 적힌 값
    elif isinstance(node, dict):
        for key, value in node.items():
            if key not in ("basis", "see", "id", "href", "kind", "icon"):
                yield from _strings(value)
    elif isinstance(node, (list, tuple)):
        for value in node:
            yield from _strings(value)


def sections_of(book):
    """해설서의 절: {"장.절": {"chapter": 장의 제목, "title": 절의 제목, "text": 절의 모든 글, "basis": {(act, part)}}}"""
    found = {}
    for chapter in (book or {}).get("chapters", []):
        for section in chapter.get("sections", []):
            found[f"{chapter.get('id')}.{section.get('id')}"] = {
                "chapter": chapter.get("title", ""), "title": section.get("title", ""), "text": " ".join(_strings(section)),
                "basis": {(one.get("act"), one.get("part", "")) for one in section.get("basis", []) if one.get("act")}}
    return found


def _korean_date(iso):
    year, month, day = (int(part) for part in iso.split("-"))
    return f"{year}년 {month}월 {day}일"


def duty_texts(body):
    """의무 일정마다 그 일정이 적은 모든 글(해마다 돌아오는 일정의 글과 날짜까지): {id: 글}. 날짜는 '2027년 1월 1일'의 꼴로 넣는다."""
    found = {}
    for duty in (body or {}).get("duties", []):
        texts = list(_strings({key: value for key, value in duty.items() if key not in ("evidence", "covers", "link", "roles", "scheme")}))
        if DATE.match(str(duty.get("date", ""))):
            texts.append(_korean_date(duty["date"]))
        found[duty.get("id")] = " ".join(texts)
    return found


def _wording(where, text, limit, term_index, sentence):
    found = []
    text = str(text or "")
    if not text.strip():
        return [(where, "글이 비어 있음")]
    if text != text.strip() or "\n" in text:
        found.append((where, "앞뒤에 빈칸이나 줄바꿈이 있음"))
    if len(text) > limit:
        found.append((where, f"글이 김({len(text)}자, 한도 {limit}자)"))
    if sentence:
        found += [(where, problem) for problem in regulations.text_problems(text, term_index)]
        if analysis.ADVICE.search(text):
            found.append((where, "권유나 전망의 말이 있음(원문이 정한 사실만 적는다)"))
    elif text.rstrip().endswith("."):
        found.append((where, "마침표로 끝남(명사로 끝나는 구로 적는다)"))
    return found


def item_problems(where, item, sections, duties, texts, known, term_index, places):
    found = []
    if not isinstance(item, dict) or not ID.match(str(item.get("id", ""))) or len(item["id"]) > ID_MAX:
        return [(where, f"항목에 id(소문자와 붙임표, {ID_MAX}자까지)가 없음")]
    duty = item.get("duty")
    if duty is not None and duty not in duties:
        found.append((where, f"없는 의무 일정: {duty}"))
        duty = None
    if item.get("title") or not duty:
        found += _wording(f"{where} 제목", item.get("title"), LIMITS["title"], term_index, False)
    if item.get("text") or not duty:
        found += _wording(f"{where} 글", item.get("text"), LIMITS["text"], term_index, True)
    note = item.get("note")
    if note is not None and (note not in NOTES or not duty or not str(duties.get(duty, {}).get(note, "")).strip()):
        found.append((where, f"note는 {list(NOTES)} 가운데 그 의무 일정에 글이 있는 것이어야 함: {note}"))
    if note and item.get("text"):
        found.append((where, "text와 note를 함께 적을 수 없음(글을 직접 적었으면 note는 쓰이지 않는다)"))
    pointed = item.get("from", [])
    if not isinstance(pointed, list) or any(key not in sections for key in pointed):
        found.append((where, f"해설서에 없는 절: {[key for key in pointed if key not in sections] if isinstance(pointed, list) else pointed}"))
        pointed = [key for key in pointed if key in sections] if isinstance(pointed, list) else []
    if not pointed and not duty:
        found.append((where, "기대는 글이 없음(from이나 duty가 있어야 한다)"))
    if len(pointed) != len(set(pointed)) or len(pointed) > 3:
        found.append((where, "from은 겹치지 않는 절 셋까지"))
    allowed = set().union(*(sections[key]["basis"] for key in pointed)) if pointed else set()
    for ref in item.get("refs", []) if isinstance(item.get("refs", []), list) else [None]:
        if not isinstance(ref, dict) or not ref.get("act"):
            found.append((where, "refs는 [{act, part}]의 꼴이어야 함"))
        elif (ref["act"], ref.get("part", "")) not in allowed:
            found.append((where, f"근거 조문이 그 절의 근거에 없음: {ref['act']}.{ref.get('part', '')}"))
        elif known and (ref["act"] not in known["acts"] or (ref.get("part") and ref["part"] not in known["parts"][ref["act"]])):
            found.append((where, f"규정 원문에 없는 조각: {ref['act']}.{ref.get('part', '')}"))
    tool = item.get("tool")
    if tool is not None:
        if not isinstance(tool, dict):
            found.append((where, "tool은 {href, text}의 꼴이어야 함"))
        else:
            found += _wording(f"{where} 링크", tool.get("text"), LIMITS["tool"], term_index, False)
            problem = handbook._href_problem(tool.get("href"), known, places)
            if problem:
                found.append((where, problem))
    # 글에 적힌 날짜와 수는 기대는 글에 있어야 한다
    written = " ".join(str(item.get(name) or "") for name in ("title", "text"))
    found += fact_problems(where, written, leaned_facts(item, sections, texts))
    return found


def leaned_facts(item, sections, texts):
    """항목이 기대는 글(해설서의 절, 의무 일정)에 적힌 날짜와 수의 묶음. 없는 절과 일정은 건너뛴다."""
    pointed = [key for key in item.get("from", []) if key in sections] if isinstance(item.get("from", []), list) else []
    return source_facts(" ".join([sections[key]["text"] for key in pointed] + ([texts.get(item.get("duty"), "")] if item.get("duty") else [])))


def fact_problems(where, written, have):
    """글에 적힌 날짜와 수 가운데 기대는 글에 없는 것. have는 기대는 글의 날짜와 수(source_facts)."""
    found = []
    if DOTTED_DATE.search(written):
        found.append((where, "날짜는 '2027년 9월 30일'의 꼴로 적음"))
    missing = [fact for fact in facts(written) if fact not in have]
    if missing:
        found.append((where, f"기대는 글에 없는 날짜나 수: {sorted(set(missing))}"))
    return found


def problems(body, book, duty_body, known=None, term_index=None, rules=None):
    """[(자리, 문제)]. book은 해설서(data/handbook.json), duty_body는 의무 일정(data/duties.json), known은 규정 원문의 문서와 조각(주면 근거 조문도 본다)."""
    if not isinstance(body, dict) or not isinstance(body.get("roles"), list) or not body["roles"]:
        return [("준비 목록", f"자료({SOURCE})를 읽지 못함")]
    term_index = term_index or regulations.term_check.load()
    sections = sections_of(book)
    duties = {duty.get("id"): duty for duty in (duty_body or {}).get("duties", [])}
    texts = duty_texts(duty_body)
    role_keys = [role.get("key") for role in (duty_body or {}).get("roles", [])]
    places = {"handbook": {}, "rules": set(rules) if rules is not None else None, "prepare": listed(body)}
    for key in sections:
        chapter, _, section = key.partition(".")
        places["handbook"].setdefault(chapter, set()).add(section)
    found = []
    if not DATE.match(str(body.get("asOf", ""))):
        found.append(("기준일", "asOf가 날짜가 아님"))
    found += _wording("소개", body.get("lead"), LIMITS["lead"], term_index, True)
    found += _wording("알림", body.get("note"), LIMITS["note"], term_index, True)
    found += fact_problems("소개와 알림", f"{body.get('lead', '')} {body.get('note', '')}", set())   # 날짜와 수는 항목에만 적는다
    seen_roles, seen_ids = [], set()
    for role in body["roles"]:
        key = role.get("key") if isinstance(role, dict) else None
        where = f"역할 {key}"
        if key not in role_keys or key in seen_roles:
            found.append((where, "의무 일정의 역할(data/duties.json의 roles)에 없거나 겹침"))
            continue
        seen_roles.append(key)
        if role.get("about") is not None:
            found += _wording(f"{where} 설명", role.get("about"), LIMITS["lead"], term_index, True)
        groups = role.get("groups")
        if not isinstance(groups, list) or not groups:
            found.append((where, "묶음(groups)이 없음"))
            continue
        role_facts = set()
        for at, group in enumerate(groups, 1):
            place = f"{where} 묶음 {at}"
            if not isinstance(group, dict) or not isinstance(group.get("items"), list) or not group["items"]:
                found.append((place, "name과 items가 있어야 함"))
                continue
            found += _wording(f"{place} 이름", group.get("name"), LIMITS["group"], term_index, False)
            group_facts = set().union(*(leaned_facts(item, sections, texts) for item in group["items"] if isinstance(item, dict)))
            found += fact_problems(f"{place} 이름", str(group.get("name") or ""), group_facts)
            role_facts |= group_facts
            for item in group["items"]:
                name = f"{where} 항목 {item.get('id', '?') if isinstance(item, dict) else '?'}"
                if isinstance(item, dict) and item.get("id") in seen_ids:
                    found.append((name, "id가 겹침"))
                seen_ids.add(item.get("id") if isinstance(item, dict) else None)
                found += item_problems(name, item, sections, duties, texts, known, term_index, places)
        found += fact_problems(f"{where} 설명", str(role.get("about") or ""), role_facts)
    return found


def listed(body):
    """준비 목록의 역할과 항목: {역할: {항목 id}}. 사이트 안의 링크(#prepare-<역할>.<항목>)가 있는 곳을 가리키는지 볼 때 쓴다."""
    return {role.get("key"): {item.get("id") for group in role.get("groups") or [] if isinstance(group, dict) for item in group.get("items") or [] if isinstance(item, dict)}
            for role in (body or {}).get("roles") or [] if isinstance(role, dict)}


def public(body, book, duty_body, known=None):
    """사이트에 싣는 모양. 역할의 이름과 설명은 의무 일정의 것, 절과 조문의 이름은 해설서와 규정 원문의 것을 붙인다."""
    sections = sections_of(book)
    named = {role.get("key"): role for role in (duty_body or {}).get("roles", [])}
    duties = {duty.get("id"): duty for duty in (duty_body or {}).get("duties", [])}
    roles = []
    for role in body.get("roles", []):
        groups = []
        for group in role.get("groups", []):
            items = []
            for item in group.get("items", []):
                row = {key: item[key] for key in ("id", "title", "text", "duty", "note", "tool") if item.get(key)}
                row["sections"] = [{"href": f"#handbook-{key}", "chapter": sections[key]["chapter"], "title": sections[key]["title"]} for key in item.get("from", [])]
                refs = [{"act": ref["act"], "part": ref.get("part", ""),
                         "label": crossrefs.label(known, ref["act"], ref.get("part", "")) if known and ref["act"] in known["acts"] else ref["act"]}
                        for ref in item.get("refs", []) if not known or ref["act"] in known["acts"]]
                if refs:
                    row["refs"] = refs
                duty = duties.get(item.get("duty"))
                if duty and not (item.get("title") and item.get("text")):
                    # 화면이 의무 일정을 읽지 못했을 때 보여 줄 제목과 글(항목이 따로 적지 않은 것만)
                    row["fallback"] = {"title": duty.get("title", ""), "text": duty.get(item.get("note")) or duty.get("text", "")}
                items.append(row)
            groups.append({"name": group["name"], "items": items})
        about = named.get(role["key"], {})
        roles.append({"key": role["key"], "name": about.get("name", role["key"]), "about": role.get("about") or about.get("about", ""), "groups": groups})
    return {"asOf": body.get("asOf", ""), "lead": body.get("lead", ""), "note": body.get("note", ""), "roles": roles}


def write(data_out, rules=None):
    """사이트의 data/prepare.json을 쓰고 (항목 수, 문제)를 돌려준다. 문제가 있으면 쓰지 않는다. 규정 원문의 목록이 먼저 만들어져 있어야 한다."""
    data_out = pathlib.Path(data_out)
    body, book, duty_body = read_json(SOURCE, None), read_json(handbook.SOURCE, None), read_json(duty_book.SOURCE, None)
    known = handbook.known_laws(read_json(data_out / "laws" / "index.json", None))
    found = problems(body, book, duty_body, known if known["acts"] else None, rules=rules)
    if found:
        return 0, found
    made = public(body, book, duty_body, known if known["acts"] else None)
    write_json(data_out / "prepare.json", made)
    return sum(len(group["items"]) for role in made["roles"] for group in role["groups"]), []


def main(argv):
    body, book, duty_body = read_json(SOURCE, None), read_json(handbook.SOURCE, None), read_json(duty_book.SOURCE, None)
    known = handbook.known_laws(read_json(pathlib.Path(argv[0]) / "laws" / "index.json", None)) if argv else None
    rules = {rule.get("id") for rule in (read_json("data/regulations.json", {}) or {}).get("regulations", [])}
    found = problems(body, book, duty_body, known if known and known["acts"] else None, rules=rules)
    count = sum(len(group.get("items", [])) for role in (body or {}).get("roles", []) for group in role.get("groups", [])) if isinstance(body, dict) else 0
    print(f"준비 목록: 역할 {len((body or {}).get('roles', [])) if isinstance(body, dict) else 0}개, 항목 {count}개, 문제 {len(found)}건")
    for where, problem in found:
        print(f"- {where}: {problem}")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
