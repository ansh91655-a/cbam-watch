"""규제마다의 분석 글(배경, 주요 내용, 쟁점과 정세, 실무에서 볼 점)을 검사하고 사이트에 실을 모양으로 바꾼다.

분석 글은 규제 자료(data/regulations.json)의 규제 하나에 analysis로 들어 있다.
 - sections: 절의 목록. 절은 key(아래 SECTIONS 가운데 하나)와 items(문단의 목록)를 가진다.
   문단은 text(글), refs(근거 자료의 key 목록), 그리고 있으면 label(문단 앞에 굵게 적는 짧은 이름)을 가진다.
 - sources: 근거 자료의 목록. 자료는 key, text(이름), url(https), basis(연혁의 근거와 같은 세 종류)를 가진다.
     stored: 저장소에 모아 둔 공식 자료. path(글 파일)나 index와 where(목록의 줄)를 적는다.
     web:    공식 화면을 읽고 확인한 것. checkedOn에 확인한 날을 적는다.
     press:  언론 보도로만 아는 것. checkedOn을 적고, 이 자료에 기댄 문단에는 '보도'라는 말이 있어야 한다.
 - asOf: 쓴 날. basedOn: 쓸 때의 규제 단계와 연혁의 줄 수(그 뒤에 규제가 달라졌는지 알아보는 데 쓴다).

모든 문단은 근거 자료를 하나 이상 가리켜야 한다. 모아 둔 자료만 가리키는 문단은 그 안의 날짜와 수가 자료의 글에 실제로 있는지 대조한다.
"""
import json
import pathlib
import re

from tools.check import fact_check
from tools.common.jsonio import read_json

ARCHIVE = pathlib.Path("collected/archive")
DATA = pathlib.Path("data")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
KEY = re.compile(r"^[a-z0-9][a-z0-9-]*$")
BASES = {"stored", "web", "press"}
# (key, 화면에 보이는 이름, 꼭 있어야 하는가)
SECTIONS = [("background", "배경", True), ("content", "주요 내용", True), ("situation", "쟁점과 정세", True), ("practice", "실무에서 볼 점", False)]
TITLES = {key: title for key, title, _ in SECTIONS}


def based_on(rule):
    """분석을 쓸 때의 규제 모습. 단계가 바뀌거나 연혁에 줄이 더해지면 이 값과 달라진다."""
    return {"stage": rule.get("stage", ""), "events": len(rule.get("timeline", []))}


def stale(rule):
    """분석을 쓴 뒤에 규제의 단계나 연혁이 달라졌는가."""
    analysis = rule.get("analysis")
    return bool(analysis) and analysis.get("basedOn") != based_on(rule)


def _source_text(source):
    """모아 둔 자료의 글. 글 파일이면 그 내용, 목록의 줄이면 그 줄들을 적은 글. 읽지 못하면 None."""
    if source.get("path"):
        path = pathlib.Path(source["path"])
        if ARCHIVE not in path.parents and DATA not in path.parents:
            return None
        return path.read_text(encoding="utf-8") if path.exists() else None
    if source.get("index"):
        entries = read_json(ARCHIVE / f"{source['index']}.json", {}).get("entries", [])
        where = source.get("where") or {}
        rows = [entry for entry in entries if where and all(str(entry.get(key, "")) == str(value) for key, value in where.items())]
        return "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) if rows else None
    return None


def _source_problems(source):
    found = []
    if not KEY.match(str(source.get("key", ""))):
        found.append("근거 자료의 key가 없거나 소문자·숫자·붙임표가 아님")
    if not str(source.get("text", "")).strip() or not str(source.get("url", "")).startswith("https://"):
        found.append(f"근거 자료의 이름이나 주소(https)가 온전하지 않음: {source.get('key')}")
    basis = source.get("basis")
    if basis not in BASES:
        found.append(f"근거 자료의 종류가 {sorted(BASES)} 가운데 하나가 아님: {source.get('key')}")
    elif basis == "stored":
        if not source.get("path") and not (source.get("index") and source.get("where")):
            found.append(f"모아 둔 자료인데 글 파일(path)이나 목록의 줄(index, where)이 없음: {source.get('key')}")
    elif not DATE.match(str(source.get("checkedOn", ""))):
        found.append(f"확인한 날(checkedOn)이 없음: {source.get('key')}")
    return found


def problems(rule, check_text, kinds=("format", "evidence")):
    """분석 글의 문제를 (어디, 무엇) 목록으로 돌려준다. 분석이 없으면 빈 목록.

    check_text는 글 하나의 표기와 용어 문제를 돌려주는 함수다(tools.publish.regulations의 text_problems).
    근거가 모아 둔 자료와 맞지 않는 것은 '근거 어긋남'으로 시작하고, kinds에 "evidence"가 있을 때만 본다.
    """
    analysis = rule.get("analysis")
    if analysis is None:
        return []
    where, found = f"규제 {rule.get('id')} 분석", []
    if not isinstance(analysis, dict):
        return [(where, "분석의 꼴이 아님")]
    if not DATE.match(str(analysis.get("asOf", ""))):
        found.append((where, "쓴 날(asOf)이 날짜가 아님"))
    based = analysis.get("basedOn")
    if not isinstance(based, dict) or not isinstance(based.get("events"), int) or "stage" not in based:
        found.append((where, "쓸 때의 규제 모습(basedOn)이 없음"))
    sources = analysis.get("sources") or []
    keys = [source.get("key") for source in sources]
    if len(set(keys)) != len(keys):
        found.append((where, "근거 자료의 key가 겹침"))
    for source in sources:
        found += [(where, problem) for problem in _source_problems(source)]
    by_key = {source.get("key"): source for source in sources}
    sections = analysis.get("sections") or []
    names = [section.get("key") for section in sections]
    if len(set(names)) != len(names) or any(name not in TITLES for name in names):
        found.append((where, f"절의 key가 겹치거나 {list(TITLES)} 가운데 하나가 아님"))
    for key, title, needed in SECTIONS:
        if needed and key not in names:
            found.append((where, f"'{title}' 절이 없음"))
    if names != [key for key, _, _ in SECTIONS if key in names]:
        found.append((where, "절의 차례가 정해진 차례와 다름"))
    used = set()
    for section in sections:
        title = TITLES.get(section.get("key"), str(section.get("key")))
        items = section.get("items") or []
        if not items:
            found.append((f"{where} {title}", "문단이 없음"))
        for number, item in enumerate(items, start=1):
            spot = f"{where} {title} {number}"
            text = str(item.get("text", "")).strip()
            if not text:
                found.append((spot, "글이 비어 있음"))
                continue
            found += [(spot, problem) for problem in check_text(text)]
            if item.get("label") is not None:
                found += [(spot, problem) for problem in check_text(str(item["label"]))]
                if not str(item["label"]).strip():
                    found.append((spot, "문단의 이름(label)이 비어 있음"))
            refs = item.get("refs") or []
            if not refs:
                found.append((spot, "근거 자료(refs)가 없음"))
                continue
            missing = [ref for ref in refs if ref not in by_key]
            if missing:
                found.append((spot, f"없는 근거 자료를 가리킴: {missing}"))
                continue
            used.update(refs)
            cited = [by_key[ref] for ref in refs]
            if any(source.get("basis") == "press" for source in cited) and "보도" not in text:
                found.append((spot, "언론 보도에 기댄 문단인데 글에 '보도'라는 말이 없음"))
            if "evidence" not in kinds:
                continue
            stored = [source for source in cited if source.get("basis") == "stored"]
            texts = [_source_text(source) for source in stored]
            unread = [source.get("key") for source, body in zip(stored, texts) if body is None]
            if unread:
                found.append((spot, f"근거 어긋남: 모아 둔 자료를 읽지 못함 {unread}"))
                continue
            if stored and len(stored) == len(cited):  # 모아 둔 자료만 가리키는 문단: 날짜와 수를 자료의 글과 대조한다
                result = fact_check.check(f"{item.get('label') or ''} {text}", "\n".join(texts))
                if not result["ok"]:
                    found.append((spot, f"근거 어긋남: 자료에서 찾지 못한 날짜 {result['missingDates']}, 수 {result['missingNumbers']}"))
    unused = [key for key in keys if key not in used]
    if unused:
        found.append((where, f"어느 문단도 가리키지 않는 근거 자료: {unused}"))
    return found


def public(rule):
    """사이트에 실을 모양. 안에서만 쓰는 값(자료의 파일 경로, 확인한 날)은 빼고, 절의 이름과 '쓴 뒤에 달라졌는가'를 더한다."""
    analysis = rule.get("analysis")
    if not analysis:
        return None
    sources = [{"key": source["key"], "text": source["text"], "url": source["url"], **({"press": True} if source.get("basis") == "press" else {})}
               for source in analysis.get("sources", [])]
    sections = [{"key": section["key"], "title": TITLES.get(section["key"], section["key"]),
                 "items": [{key: item[key] for key in ("label", "text", "refs") if item.get(key)} for item in section.get("items", [])]}
                for section in analysis.get("sections", [])]
    return {"asOf": analysis.get("asOf", ""), "stale": stale(rule), "sections": sections, "sources": sources}
