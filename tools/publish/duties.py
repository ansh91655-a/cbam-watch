"""실무 달력: 법령에 날짜가 적힌 의무 일정(EU CBAM, 영국 CBAM). 사이트의 일정 화면이 쓴다.

원본은 data/duties.json이다. 의무마다 날짜, 할 일, 누가 하는지, 근거 조문과 그 조문이 적힌 글(evidence)이 있다.
검사는 다음을 본다.
- 꼴: 값이 다 있는지, 날짜와 종류가 맞는지, 글이 표기 규칙(높임말, 용어집)에 맞는지.
- 근거: evidence의 대목이 받아 둔 법령 글에 있는지, 그리고 의무의 날짜(날과 달, 해)가 그 대목 안에 적혀 있는지.
  법령은 "By 30 September of each year, and for the first time in 2027"처럼 날과 해를 떨어뜨려 적기도 하므로,
  날과 달이 든 대목과 해가 든 대목이 각각 있으면 된다.
검사: python -m tools.publish.duties   (문제가 있으면 0이 아닌 값으로 끝난다)
"""
import re
import sys

from tools.common.jsonio import read_json
from tools.publish import regulations

SOURCE = "data/duties.json"
KINDS = {"시행", "기한"}
DATE = re.compile(r"^(20\d\d)-(\d\d)-(\d\d)$")
SLUG = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
ORDINAL = re.compile(r"(?<=\d)(st|nd|rd|th)\b")


def date_in_phrases(date, phrases):
    """의무의 날짜가 근거 대목에 적혀 있는가. 날과 달이 든 대목, 해가 든 대목이 있어야 한다."""
    match = DATE.match(str(date))
    if not match:
        return False
    year, month, day = match.group(1), int(match.group(2)), int(match.group(3))
    plain = [ORDINAL.sub("", str(phrase)) for phrase in phrases]
    day_month = re.compile(rf"(?<!\d){day} {MONTHS[month - 1]}\b")
    return any(day_month.search(phrase) for phrase in plain) and any(year in phrase for phrase in plain)


def duty_problems(duty, schemes, term_index, kinds):
    where, found = f"의무 {duty.get('id', '?')}", []
    if "format" in kinds:
        if not SLUG.match(str(duty.get("id", ""))):
            found.append((where, "id가 소문자와 붙임표로 된 이름이 아님"))
        if duty.get("scheme") not in schemes:
            found.append((where, f"모르는 제도: {duty.get('scheme')}"))
        if not DATE.match(str(duty.get("date", ""))) or duty.get("kind") not in KINDS:
            found.append((where, f"날짜가 YYYY-MM-DD가 아니거나 종류가 {sorted(KINDS)} 가운데 하나가 아님"))
        for field in ("title", "who", "text", "basis"):
            if not str(duty.get(field, "")).strip():
                found.append((where, f"{field}가 비어 있음"))
        if str(duty.get("title", "")).rstrip().endswith("."):
            found.append((where, "제목이 마침표로 끝남(제목은 명사로 끝나는 구다)"))
        if not str(duty.get("link", "")).startswith("https://"):
            found.append((where, "원문 주소(link)가 https로 시작하지 않음"))
        for field in ("text", "supplier"):
            found += [(f"{where} {field}", problem) for problem in regulations.text_problems(str(duty.get(field, "")), term_index)]
        cover = duty.get("covers")
        if cover is not None and (not isinstance(cover.get("dates"), list) or not cover.get("dates") or not str(cover.get("word", "")).strip()):
            found.append((where, "covers에는 날짜 목록(dates)과 낱말(word)이 있어야 함"))
    if "evidence" in kinds:
        evidence = duty.get("evidence")
        problem = regulations.evidence_problem(evidence, duty.get("date"))
        if problem:
            found.append((where, "근거 어긋남: " + problem))
        elif not date_in_phrases(duty.get("date"), evidence.get("contains", [])):
            found.append((where, f"근거 어긋남: 근거 대목에 날짜 {duty.get('date')}(날과 달, 해)가 적혀 있지 않음"))
    return found


def problems(body, term_index=None, kinds=("format", "evidence")):
    """[(자리, 문제)] 목록. kinds는 regulations.problems와 같다: "format"은 꼴과 표기, "evidence"는 근거."""
    if not isinstance(body, dict) or not isinstance(body.get("duties"), list) or not body["duties"]:
        return [("실무 달력", "자료(data/duties.json)를 읽지 못함")]
    term_index = term_index or regulations.term_check.load()
    schemes = {scheme.get("key") for scheme in body.get("schemes", [])}
    found = []
    ids = [duty.get("id") for duty in body["duties"]]
    if "format" in kinds:
        if len(set(ids)) != len(ids):
            found.append(("실무 달력", "id가 겹침"))
        found += [("실무 달력 note", problem) for problem in regulations.text_problems(str(body.get("note", "")), term_index)]
    for duty in body["duties"]:
        found += duty_problems(duty, schemes, term_index, kinds)
    return found if "format" in kinds else [row for row in found if row[1].startswith("근거 어긋남")]


def public(body):
    """사이트에 실을 모양. 근거 대목과 겹침 처리용 값은 뺀다. 날짜순으로 놓는다."""
    names = {scheme["key"]: scheme["name"] for scheme in body.get("schemes", [])}
    rows = [{**{key: value for key, value in duty.items() if key not in ("evidence", "covers")}, "schemeName": names.get(duty.get("scheme"), "")}
            for duty in body.get("duties", [])]
    return {"asOf": body.get("asOf", ""), "note": body.get("note", ""), "schemes": body.get("schemes", []),
            "duties": sorted(rows, key=lambda row: (row["date"], row["id"]))}


def events(body):
    """의무를 일정 화면의 일정 꼴로 바꾼다."""
    names = {scheme["key"]: scheme["name"] for scheme in (body or {}).get("schemes", [])}
    return [{"date": duty["date"], "title": duty["title"], "kind": duty["kind"], "note": duty["text"], "sourceName": duty["basis"], "link": duty["link"],
             "derived": True, "duty": duty["id"], "scheme": names.get(duty.get("scheme"), "")} for duty in (body or {}).get("duties", [])]


def superseded(event, body):
    """게시 데이터의 일정이 의무 일정과 같은 일을 가리키는가(같은 일을 두 번 싣지 않으려고 본다)."""
    for duty in (body or {}).get("duties", []):
        cover = duty.get("covers") or {}
        if event.get("date") in cover.get("dates", []) and event.get("kind") == duty.get("kind") and cover.get("word", "\0") in str(event.get("title", "")):
            return True
    return False


def main():
    found = problems(read_json(SOURCE, None))
    for where, what in found:
        print(f"문제: {where}: {what}")
    print(f"실무 달력: 문제 {len(found)}건")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
