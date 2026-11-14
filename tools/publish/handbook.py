"""CBAM 해설서의 글(data/handbook.json)을 검사하고 사이트에 실을 모양으로 바꾼다.

해설서는 제도가 어떻게 돌아가는지를 차례로 풀어 쓴 글이다. 손으로 적고, 절마다 근거가 된 조문을 가리킨다.

꼴
  {"asOf": "2026-11-14", "lead": "해설서를 소개하는 한두 문장",
   "sources": {"ets-directive": {"text": "EU 배출권거래제 지침 …", "url": "https://…", "path": "받아 둔 글의 저장소 안 경로"}},   선택
   "chapters": [{"id", "title", "lead", "sections": [{
       "id", "title",
       "body": ["문단", …],                                   꼭. 높임말로 쓴 문단 1~5개
       "list": ["항목", …], "ordered": true,                   선택. 글머리표 목록(ordered가 참이면 차례가 있는 목록)
       "formula": {"text": "식 한 줄", "parts": [["말", "풀이"], …]},   선택
       "table": {"head": ["칸", …], "rows": [["값", …], …]},   선택. 작은 표
       "terms": [{"ko", "en", "abbr"?, "text"}],              선택. 이 절에서 처음 나오는 용어의 풀이
       "basis": [{"act": "32023R0956", "part": "art-31", "contains": ["원문의 영문 대목", …]},   꼭. 근거 조문
                 {"source": "ets-directive", "label": "제10a조(1a)", "contains": […]}],       사이트의 규정 원문에 없는 문서(sources에 적은 것)
       "figure": {"kind": "flow", "title": "그림의 이름", …},    선택. 글을 한눈에 보이게 한 그림(꼴은 tools/publish/handbook_figures.py)
       "see": [{"href": "#calc", "text": "인증서 비용 추정"}],   선택. 사이트 안의 관련 화면
       "caveat": "아직 정해지지 않았거나 바뀔 수 있는 점"          선택
   }]}]}

검사 둘
- 꼴(format): 이름과 글의 꼴, 높임말과 숫자 표기(tools.check.style_check), 용어집이 쓰지 말라는 표기(tools.check.term_check),
  사이트 안 링크(규정 원문의 조각, 규제 화면, 해설서의 장과 절이 실제로 있는지), 같은 용어를 두 번 풀이하지 않았는지,
  목록을 가리키는 문장('아래 …', '다음 …')이 목록 바로 앞(본문의 마지막 문단)에 있는지.
  어긋나면 '문제'이고 사이트 만들기를 멈춘다.
- 근거(evidence): basis의 문서와 조각이 사이트의 규정 원문에 있는지, contains의 영문 대목이 그 조각의 원문에 실제로 있는지.
  source로 적은 근거는 받아 둔 글(sources의 path)에 그 대목이 있는지 본다.
  어긋나면 '근거 어긋남'으로 알리기만 한다(원문이 개정되어 달라진 것일 수 있다. 글은 그대로 실리고 상태 점검이 알린다).

싣는 모양(public): contains를 빼고 basis마다 이름(label)을 붙인다(source로 적은 근거는 이름과 주소). 절마다의 용어 풀이는 terms로도 한데 모아 싣는다.

검사: python -m tools.publish.handbook [--laws <사이트의 data/laws 폴더>] [--file <글 파일>]
      --laws가 없으면 꼴과, 받아 둔 글(sources)에 댄 근거만 본다. 문제가 있으면 0이 아닌 값으로 끝난다(근거 어긋남뿐이면 0).
"""
import argparse
import pathlib
import re
import sys

from tools.check import style_check, term_check
from tools.publish import handbook_figures
from tools.common.jsonio import read_json
from tools.publish import crossrefs

SOURCE = "data/handbook.json"
DRIFT = "근거 어긋남"
VIEWS = ("home", "news", "rules", "price", "calc", "calendar", "sector", "cn", "laws", "law", "changes", "docs", "terms", "about", "handbook", "search")
ID = re.compile(r"^[a-z][a-z0-9-]{1,39}$")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
HANGUL = re.compile(r"[가-힣]")
POINTER = re.compile(r"아래(?!\s*(?:표|절|식|그림))|다음(?:을|과 같)")   # 뒤따르는 목록을 가리키는 말(아래 표, 아래 절처럼 다른 것을 가리키는 말은 뺀다)
LIMITS = {"title": 40, "lead": 220, "body": 420, "list": 220, "term": 280, "caveat": 280, "cell": 120, "formula": 200}
BODY_MAX = 5
BASIS_MAX = 10
PHRASE_MIN = 20   # 근거 대목은 이만큼은 길어야 한다(짧은 낱말은 어디에나 있다)


def _squeeze(text):
    return " ".join(str(text or "").split())


def known_laws(index):
    """규정 원문의 목록(laws/index.json)에서 문서와 조각을 찾는 표. 법령뿐 아니라 가이던스와 안내서도 든다(crossrefs.label이 쓰는 꼴)."""
    acts = (index or {}).get("acts", [])
    return {"acts": {act["id"]: act for act in acts}, "parts": {act["id"]: {part["id"]: part for part in act.get("toc", [])} for act in acts}}


def _part_text(laws_dir, act_id, part_id, cache):
    """그 조각(조각이 ""이면 문서 전체)의 영문 원문을 빈칸을 하나로 줄여 돌려준다. 없으면 None."""
    if act_id not in cache:
        body = read_json(pathlib.Path(laws_dir) / f"{act_id}.json", None)
        cache[act_id] = {part["id"]: _squeeze(" ".join(str(block[0]) for block in part.get("blocks", []) if block)) for part in (body or {}).get("parts", [])} if body else None
    parts = cache[act_id]
    if parts is None:
        return None
    return parts.get(part_id) if part_id else " ".join(parts.values())


def corpus_texts():
    """받아 둔 법령과 안내 문서의 글에서 만든 { 문서: { 조각: 영문 } }. 사이트를 만들지 않고 근거를 대조할 때 쓴다(상태 점검)."""
    from tools.laws import corpus

    return {doc["id"]: {part["id"]: _squeeze(" ".join(str(block) for block in part.get("blocks", []))) for part in corpus.read(doc)} for doc in corpus.documents()}


def _stored_text(path, cache):
    """받아 둔 글(저장소 안의 파일)을 빈칸을 하나로 줄여 돌려준다. 없으면 None."""
    key = ("file", str(path))
    if key not in cache:
        file = pathlib.Path(str(path))
        cache[key] = _squeeze(file.read_text(encoding="utf-8")) if path and file.is_file() else None
    return cache[key]


def _points_down(text):
    """문단이 '아래'나 '다음'으로 뒤따르는 목록을 가리키는지 본다."""
    return bool(POINTER.search(str(text)))


def _texts(section):
    """절에서 사람이 읽는 글을 모두: [(어디, 글, 길이 한도)]"""
    rows = [("제목", section.get("title", ""), LIMITS["title"])]
    rows += [(f"문단 {at + 1}", text, LIMITS["body"]) for at, text in enumerate(section.get("body") or [])]
    rows += [(f"목록 {at + 1}", text, LIMITS["list"]) for at, text in enumerate(section.get("list") or [])]
    rows += [(f"용어 {term.get('ko', at + 1)}", term.get("text", ""), LIMITS["term"]) for at, term in enumerate(section.get("terms") or []) if isinstance(term, dict)]
    if section.get("caveat"):
        rows.append(("단서", section["caveat"], LIMITS["caveat"]))
    formula = section.get("formula")
    if isinstance(formula, dict):
        rows.append(("식", formula.get("text", ""), LIMITS["formula"]))
        rows += [(f"식 풀이 {at + 1}", " ".join(str(cell) for cell in pair), LIMITS["list"]) for at, pair in enumerate(formula.get("parts") or []) if isinstance(pair, list)]
    table = section.get("table")
    if isinstance(table, dict):
        rows += [("표", str(cell), LIMITS["cell"]) for row in [table.get("head") or []] + list(table.get("rows") or []) for cell in (row if isinstance(row, list) else [])]
    return rows


def _wording(where, text, limit, term_index, sentence):
    """글 한 덩이의 꼴: 비어 있지 않고, 한도 안이고, 표기 규칙과 용어집을 지킨다. sentence이면 문장으로 끝나야 한다."""
    found = []
    text = str(text or "")
    if not text.strip():
        return [(where, "글이 비어 있음")]
    if len(text) > limit:
        found.append((where, f"글이 김({len(text)}자, 한도 {limit}자)"))
    if text != text.strip() or "\n" in text:
        found.append((where, "앞뒤 빈칸이나 줄바꿈이 있음"))
    found += [(where, f"표기: {hit['message']}('{hit['sample']}')") for hit in style_check.check(text) if hit["hard"]]
    if term_index:
        found += [(where, f"용어: '{hit['avoid']}' 대신 '{hit['use']}'") for hit in term_check.check(text, term_index) if hit["hard"]]
    if sentence and not re.search(r"[.?!]\)?$", text):
        found.append((where, "문장이 마침표로 끝나지 않음"))
    return found


def _href_problem(href, known, places=None):
    """사이트 안의 주소가 실제로 있는 곳인지. places: {"handbook": {장: {절}}, "rules": {규제 id}} 가운데 아는 것만 본다."""
    hit = re.match(r"^#([a-z]+)(?:-(.+))?$", str(href or ""))
    if not hit or hit.group(1) not in VIEWS:
        return f"사이트에 없는 주소: {href}"
    view, rest = hit.group(1), hit.group(2) or ""
    places = places or {}
    if view == "law" and known and rest:
        act_id, _, part_id = rest.partition(".")
        if act_id not in known["acts"] or (part_id and part_id not in known["parts"][act_id]):
            return f"규정 원문에 없는 곳: {href}"
    if view == "handbook" and rest and places.get("handbook") is not None:
        chapter, _, section = rest.partition(".")
        if chapter not in places["handbook"] or (section and section not in places["handbook"][chapter]):
            return f"해설서에 없는 곳: {href}"
    if view == "rules" and rest and places.get("rules") is not None and rest not in places["rules"]:
        return f"규제 화면에 없는 곳: {href}"
    return ""


def section_problems(where, section, term_index=None, known=None, laws_dir=None, cache=None, kinds=("format", "evidence"), sources=None, places=None):
    found = []
    sources = sources or {}
    if "format" in kinds:
        if not ID.match(str(section.get("id", ""))):
            found.append((where, "id가 없거나 꼴이 다름(소문자, 숫자, 붙임표)"))
        body = section.get("body")
        if not isinstance(body, list) or not 1 <= len(body) <= BODY_MAX:
            found.append((where, f"문단은 1~{BODY_MAX}개여야 함"))
        if section.get("list") and isinstance(body, list):   # 목록은 본문 뒤에 놓이므로, 목록을 가리키는 문장은 마지막 문단에 둔다
            found += [(f"{where} 문단 {at + 1}", "목록을 가리키는 문장은 본문의 마지막 문단에 둠") for at, text in enumerate(body[:-1]) if _points_down(text)]
        for name, text, limit in _texts(section):
            sentence = name.startswith(("문단", "용어", "단서"))
            found += [(f"{where} {name}", what) for _, what in _wording(name, text, limit, term_index, sentence)]
        title = str(section.get("title", ""))
        if title.endswith((".", "다", "요")):
            found.append((where, "제목은 명사로 끝나는 구로 적음"))
        for term in section.get("terms") or []:
            if not isinstance(term, dict) or not all(str(term.get(key, "")).strip() for key in ("ko", "en", "text")):
                found.append((where, "용어 풀이에 ko, en, text가 있어야 함"))
        formula = section.get("formula")
        if formula is not None and not (isinstance(formula, dict) and str(formula.get("text", "")).strip()
                                        and all(isinstance(pair, list) and len(pair) == 2 for pair in formula.get("parts") or [])):
            found.append((where, "식은 {text, parts: [[말, 풀이]]} 꼴이어야 함"))
        table = section.get("table")
        if table is not None:
            head, rows = (table.get("head"), table.get("rows")) if isinstance(table, dict) else (None, None)
            if not (isinstance(head, list) and head and isinstance(rows, list) and rows and all(isinstance(row, list) and len(row) == len(head) for row in rows)):
                found.append((where, "표는 머리와 같은 칸 수의 줄들이어야 함"))
        figure = section.get("figure")
        if figure is not None:
            found += [(f"{where} 그림", what) for what in handbook_figures.problems(figure)]
            for text in handbook_figures.texts(figure):   # 그림의 글도 표기 규칙과 용어집을 지킨다(짧은 구라서 문장의 꼴은 보지 않는다)
                found += [(f"{where} 그림", what) for _, what in _wording("그림", text, 10 ** 6, term_index, False)]
            for href in handbook_figures.hrefs(figure):
                problem = _href_problem(href, known, places)
                if problem:
                    found.append((f"{where} 그림", problem))
        for link in section.get("see") or []:
            if not isinstance(link, dict) or not str(link.get("text", "")).strip():
                found.append((where, "관련 화면에 text가 있어야 함"))
                continue
            problem = _href_problem(link.get("href"), known, places)
            if problem:
                found.append((where, problem))
        basis = section.get("basis")
        if not isinstance(basis, list) or not 1 <= len(basis) <= BASIS_MAX:
            found.append((where, f"근거 조문은 1~{BASIS_MAX}개여야 함"))
        for one in basis if isinstance(basis, list) else []:
            phrases = one.get("contains") if isinstance(one, dict) else None
            if not isinstance(one, dict) or not (one.get("act") or one.get("source")) or not isinstance(phrases, list) or not phrases:
                found.append((where, "근거에 act(또는 source)와 contains(영문 대목)가 있어야 함"))
            elif one.get("source") and one["source"] not in sources:
                found.append((where, f"sources에 없는 근거 문서: {one['source']}"))
            elif any(not isinstance(phrase, str) or len(_squeeze(phrase)) < PHRASE_MIN or HANGUL.search(phrase) for phrase in phrases):
                found.append((where, f"근거 대목은 원문의 영문 그대로 {PHRASE_MIN}자 이상이어야 함"))
    if "evidence" in kinds:  # 받아 둔 글은 저장소 안에 있으므로 사이트의 규정 원문이 없어도 본다
        for one in section.get("basis") or []:
            if not isinstance(one, dict) or not one.get("source") or one["source"] not in sources:
                continue
            text = _stored_text(sources[one["source"]].get("path", ""), cache if cache is not None else {})
            if text is None:
                found.append((where, f"{DRIFT}: 받아 둔 글을 읽지 못함 {sources[one['source']].get('path', '')}"))
                continue
            found += [(where, f"{DRIFT}: {one['source']}에 없는 대목 '{_squeeze(phrase)[:60]}'")
                      for phrase in one.get("contains") or [] if isinstance(phrase, str) and _squeeze(phrase) not in text]
    if "evidence" in kinds and known is not None:
        for one in section.get("basis") or []:
            if not isinstance(one, dict) or not one.get("act"):
                continue
            act_id, part_id = one["act"], one.get("part", "")
            if act_id not in known["acts"]:
                found.append((where, f"{DRIFT}: 규정 원문에 없는 문서 {act_id}"))
                continue
            if part_id and part_id not in known["parts"][act_id]:
                found.append((where, f"{DRIFT}: {act_id}에 없는 조각 {part_id}"))
                continue
            if laws_dir is None and act_id not in (cache or {}):
                continue
            text = _part_text(laws_dir, act_id, part_id, cache if cache is not None else {})
            if text is None:
                found.append((where, f"{DRIFT}: 원문을 읽지 못함 {act_id}"))
                continue
            found += [(where, f"{DRIFT}: {act_id} {part_id or '문서'}에 없는 대목 '{_squeeze(phrase)[:60]}'")
                      for phrase in one.get("contains") or [] if isinstance(phrase, str) and _squeeze(phrase) not in text]
    return found


def problems(body, term_index=None, laws_dir=None, kinds=("format", "evidence"), rules=None, texts=None):
    """[(어디, 무엇)]. '근거 어긋남'으로 시작하는 것은 알리기만 하고, 나머지는 사이트 만들기를 멈춘다.
    rules: 규제 화면의 id 묶음(주면 #rules-<id> 링크가 실제로 있는 규제인지 본다).
    texts: 사이트의 규정 원문(laws_dir) 대신 근거를 대조할 글({ 문서: { 조각: 영문 } }. corpus_texts가 만든다)."""
    if not isinstance(body, dict) or not isinstance(body.get("chapters"), list) or not body["chapters"]:
        return [("해설서", "chapters가 없음")]
    found = []
    known = known_laws(read_json(pathlib.Path(laws_dir) / "index.json", None)) if laws_dir else None
    if laws_dir and not known["acts"]:
        found.append(("해설서", f"{DRIFT}: 규정 원문의 목록을 읽지 못함"))
        known = None
    cache = {}
    if texts is not None and known is None:
        known = {"acts": {act_id: {} for act_id in texts}, "parts": {act_id: {part_id: {} for part_id in parts} for act_id, parts in texts.items()}}
        cache.update(texts)
    sources = body.get("sources") if isinstance(body.get("sources"), dict) else {}
    places = {"handbook": {chapter.get("id"): {section.get("id") for section in chapter.get("sections") or [] if isinstance(section, dict)}
                           for chapter in body["chapters"] if isinstance(chapter, dict)},
              "rules": set(rules) if rules is not None else None}
    if "format" in kinds:
        if not DATE.match(str(body.get("asOf", ""))):
            found.append(("기준일", "asOf가 날짜가 아님"))
        found += [("소개", what) for _, what in _wording("소개", body.get("lead", ""), LIMITS["lead"], term_index, True)]
        if body.get("sources") is not None and not isinstance(body.get("sources"), dict):
            found.append(("근거 문서", "sources는 {이름: {text, url, path}} 꼴이어야 함"))
        for key, one in sources.items():
            if not ID.match(str(key)) or not isinstance(one, dict) or not all(str(one.get(name, "")).strip() for name in ("text", "url", "path")) \
                    or not str(one.get("url", "")).startswith("https://"):
                found.append(("근거 문서", f"{key}: text, url(https), path가 있어야 함"))
    seen = set()
    explained = {}
    for chapter in body["chapters"]:
        name = f"{chapter.get('id', '?')}"
        if "format" in kinds:
            if not ID.match(str(chapter.get("id", ""))) or chapter.get("id") in seen:
                found.append((name, "장의 id가 없거나 겹침"))
            seen.add(chapter.get("id"))
            found += [(f"{name} {where}", what) for where, what in _wording("제목", chapter.get("title", ""), LIMITS["title"], term_index, False)]
            found += [(f"{name} {where}", what) for where, what in _wording("요약", chapter.get("lead", ""), LIMITS["lead"], term_index, True)]
            if not isinstance(chapter.get("sections"), list) or not chapter["sections"]:
                found.append((name, "절이 없음"))
            ids = [section.get("id") for section in chapter.get("sections") or [] if isinstance(section, dict)]
            if len(ids) != len(set(ids)):
                found.append((name, "절의 id가 겹침"))
        for section in chapter.get("sections") or []:
            if not isinstance(section, dict):
                found.append((name, "절이 꼴에 맞지 않음"))
                continue
            where = f"{name}.{section.get('id', '?')}"
            found += section_problems(where, section, term_index, known, laws_dir, cache, kinds, sources, places)
            for term in section.get("terms") or [] if "format" in kinds else []:
                word = term.get("ko") if isinstance(term, dict) else None
                if word and word in explained:
                    found.append((where, f"용어 '{word}'의 풀이가 겹침({explained[word]}에 이미 있음)"))
                elif word:
                    explained[word] = where
    return found


def blocking(found):
    return [row for row in found if not row[1].startswith(DRIFT)]


def public(body, known=None):
    """사이트에 싣는 모양: 근거의 영문 대목을 빼고 이름을 붙인다. 용어 풀이는 장과 절의 자리와 함께 한데 모은다."""
    chapters, terms = [], []
    sources = body.get("sources") if isinstance(body.get("sources"), dict) else {}
    for chapter in body.get("chapters", []):
        sections = []
        for section in chapter.get("sections", []):
            row = {key: section[key] for key in ("id", "title", "body", "figure", "list", "ordered", "formula", "table", "terms", "see", "caveat") if section.get(key)}
            row["basis"] = []
            for one in section.get("basis", []):
                if one.get("source"):
                    source = sources.get(one["source"]) or {}
                    if source.get("url"):
                        row["basis"].append({"label": " ".join(part for part in (source.get("text", ""), one.get("label", "")) if part), "url": source["url"]})
                elif not known or one["act"] in known["acts"]:
                    row["basis"].append({"act": one["act"], "part": one.get("part", ""),
                                         "label": crossrefs.label(known, one["act"], one.get("part", "")) if known and one["act"] in known["acts"] else one["act"]})
            sections.append(row)
            terms += [{**term, "chapter": chapter["id"], "section": section["id"]} for term in section.get("terms") or []]
        chapters.append({"id": chapter["id"], "title": chapter["title"], "lead": chapter.get("lead", ""), "sections": sections})
    return {"asOf": body.get("asOf", ""), "lead": body.get("lead", ""), "chapters": chapters, "terms": terms}


def main(argv=None):
    parser = argparse.ArgumentParser(description="CBAM 해설서의 글을 검사한다")
    parser.add_argument("--file", default=SOURCE)
    parser.add_argument("--laws", default="", help="사이트의 data/laws 폴더(근거 대목까지 보려면)")
    args = parser.parse_args(argv)
    body = read_json(args.file, None)
    if body is None:
        print(f"읽지 못함: {args.file}")
        return 1
    rules = read_json("data/regulations.json", None)
    rule_ids = {one.get("id") for one in (rules.get("regulations", []) if isinstance(rules, dict) else rules or [])} if rules else None
    found = problems(body, term_check.load(), args.laws or None, rules=rule_ids)
    for where, what in found:
        print(f"{where}: {what}")
    chapters = body.get("chapters", []) if isinstance(body, dict) else []
    print(f"장 {len(chapters)}개, 절 {sum(len(chapter.get('sections') or []) for chapter in chapters)}개, 문제 {len(blocking(found))}건, 근거 어긋남 {len(found) - len(blocking(found))}건")
    return 1 if blocking(found) else 0


if __name__ == "__main__":
    sys.exit(main())
