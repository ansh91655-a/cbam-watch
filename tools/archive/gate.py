"""소급 항목 하나가 게시 기준을 지키는지 검사한다.

평소의 게시 관문(tools.publish.add_items)이 보는 형식·사실 대조에, 문체(높임말)와 용어 검사, 게시일 대조를 더했다.
소급 항목은 따로 검증 실행을 거치지 않으므로, 여기에서 걸리면 싣지 않는다.
"""
from tools.check import dates, excerpt_check, fact_check, style_check, term_check
from tools.publish import add_items

TEXT_FIELDS = ("title", "summary", "impact")


def _joined(item, fields):
    return "\n".join(str(item.get(field, "")) for field in fields)


def fact_problems(item, source):
    """제목·요약·실무 영향의 수치와 날짜가 원문 글에 있는지 본다. factAllow에 적은 값은 사유(factNote)가 있을 때만 넘어간다."""
    result = fact_check.check(_joined(item, TEXT_FIELDS), source)
    allowed = {str(value) for value in item.get("factAllow", [])} if str(item.get("factNote", "")).strip() else set()
    missing = [value for value in result["missingDates"] + result["missingNumbers"] if value not in allowed]
    return ["사실 대조: 원문에서 찾지 못함 " + ", ".join(missing)[:120]] if missing else []


def date_problems(item, source):
    """게시일이 원문 글에 있는 날짜인지 본다."""
    published = str(item.get("published", ""))
    if not published:
        return ["게시일 없음"]
    found, _ = dates.find(source)
    year, month, day = (int(part) for part in published.split("-"))
    return [] if (year, month, day) in found else [f"게시일 {published}이 원문 글에 없음"]


def link_problems(item, source, known_links):
    """링크가 모아 둔 자료에 적힌 주소인지 본다. 손으로 옮겨 적다 틀린 주소를 막는다."""
    link = str(item.get("link", ""))
    return [] if link in known_links or (source and link in source) else ["링크가 모아 둔 자료에 없는 주소"]


def problems(item, source, term_index, known_topics, known_links=None):
    """걸린 것의 목록을 돌려준다. 비어 있으면 실어도 된다. source는 저장소에 받아 둔 원문 글이다.

    known_links를 주면 링크가 그 안에 있거나 원문 글에 적혀 있어야 한다.
    """
    found = list(add_items.format_problems(item))
    if known_links is not None:
        found += link_problems(item, source, known_links)
    if item.get("topic") not in known_topics:
        found.append("주제")
    if not str(item.get("sourceCode", "")).strip() or not str(item.get("sourceName", "")).strip():
        found.append("출처")
    found += [f"문체: {hit['message']} ({hit['sample']})" for hit in style_check.check(_joined(item, TEXT_FIELDS)) if hit["hard"]]
    found += [f"용어: '{hit['avoid']}' 대신 '{hit['use']}'" for hit in term_check.check(_joined(item, TEXT_FIELDS), term_index) if hit["hard"]]
    if source is None:
        found.append("원문 글 없음")
    elif not found:
        found += date_problems(item, source) + fact_problems(item, source)
    return found


def excerpt_of(item, source):
    """실어도 되는 원문 발췌면 그 글을, 아니면 빈 글을 돌려준다. EU 공식 출처(등급 A)의 글만 싣는다."""
    excerpt = str(item.get("excerpt", "")).strip()
    if not excerpt or item.get("tier") != "A" or source is None:
        return ""
    return excerpt if excerpt_check.check(excerpt, source)["ok"] else ""
