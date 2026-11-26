"""규정 원문 화면에 싣는 법령의 목록. 저장소에 본문을 받아 둔 것만 싣는다.

CBAM 규정은 통합본(collected/archive/eu-fulltext.json의 cbam-consolidated)을, 하위 법령은 collected/archive/eu-acts.json에 적힌 차례대로 싣는다.
이 차례가 화면에 보이는 차례이자 번역하는 차례다(ORDER_LAST에 적은 것은 맨 뒤로 보낸다).
관보에 실리기 전의 법령 글(EU 집행위원회가 채택한 위임규정, 의견수렴 중인 초안. collected/archive/eu-pending.json)은 시행 중인 법령 다음에 싣고,
화면이 관보에 실린 글이 아님을 알리도록 remark를 붙인다. 이 문서들에는 CELEX 번호가 없다(celex가 빈 글이다).
법령마다 규제 자료(data/regulations.json)의 어느 규제에 해당하는지를 법령 번호로 찾아 적는다.
"""
import re

from tools.common.jsonio import read_json

ACTS = "collected/archive/eu-acts.json"
FULLTEXT = "collected/archive/eu-fulltext.json"
PENDING = "collected/archive/eu-pending.json"
RULES = "data/regulations.json"
BASE_NAME = "cbam-consolidated"
BASE_CELEX = "32023R0956"
ORDER_LAST = ("32023R1773",)  # 전환기간이 끝나 지금은 적용되지 않는 법령
EURLEX = "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:{code}"
NUMBER = re.compile(r"\((?:EU|EC)\) (\d{4})/(\d+)")
CELEX = re.compile(r"CELEX:0?(3\d{4}[RDL]\d{4})")


def number_of(celex):
    """32025R2548 → "2025/2548"."""
    return f"{celex[1:5]}/{int(celex[6:])}"


def official(celex, front=()):
    """법령의 영문 이름: Commission Implementing Regulation (EU) 2025/2548. 종류는 글의 머리(front)에서 읽는다."""
    kind = {"R": "Regulation", "D": "Decision", "L": "Directive"}.get(celex[5], "Act")
    head = " ".join(front[:12]).upper()
    prefix = "Commission Implementing " if "IMPLEMENTING" in head else ("Commission Delegated " if "DELEGATED" in head else "")
    return f"{prefix}{kind} (EU) {number_of(celex)}"


def rule_ids(rules):
    """{법령의 CELEX 번호: 규제 id}. 규제의 official과 링크에 적힌 법령 번호로 맞춘다."""
    found = {}
    for rule in (rules or {}).get("regulations", []):
        codes = [f"3{year}{letter}{int(number):04d}" for year, number in NUMBER.findall(str(rule.get("official", ""))) for letter in "RDL"]
        codes += [code for link in rule.get("links", []) for code in CELEX.findall(str(link.get("url", "")))]
        for code in codes:
            found.setdefault(code, rule["id"])
    return found


# 관보에 실리기 전의 글에 붙이는 알림(화면의 문서 머리에 보인다)과 영문 이름의 끝. {date}는 문서의 날짜다.
PENDING_STATES = {
    "adopted": ("EU 집행위원회가 {date}에 채택한 글입니다. 아직 유럽연합 관보에 실리지 않아 법령 번호가 없고, 유럽의회와 EU 이사회의 이의 제기 기간이 지나야 발효합니다.", "adopted by the Commission, not yet published in the Official Journal"),
    "draft": ("의견수렴 중인 초안입니다({date} 공개). 채택되는 법령은 이 글과 다를 수 있습니다.", "draft for feedback"),
}


def _long_date(day):
    """2026-11-25 → 2026년 11월 25일."""
    year, month, date = (int(piece) for piece in day.split("-"))
    return f"{year}년 {month}월 {date}일"


def pending():
    """관보에 실리기 전의 법령 글의 목록(tools/archive/pending.py가 받아 둔 것). 받아 둔 글이 없는 것은 뺀다. 꼴은 acts와 같다."""
    found = []
    for entry in (read_json(PENDING, {}) or {}).get("entries", []):
        state = PENDING_STATES.get(entry.get("state"))
        if not state or not entry.get("name") or not entry.get("textPath"):
            continue
        remark, tail = state
        kind = "Delegated" if "위임규정" in entry.get("title", "") else "Implementing"
        found.append({"id": entry["name"], "celex": "", "name": entry.get("title", entry["name"]), "url": entry.get("url", ""), "path": entry["textPath"], "consolidated": "",
                      "rule": entry.get("rule", ""), "official": f"Commission {kind} Regulation (EU) …/… · {entry.get('reference', '')} ({tail})",
                      "remark": remark.format(date=_long_date(entry["date"])) if entry.get("date") else remark.replace("{date}에 ", "").replace("({date} 공개)", "")})
    return found


def acts():
    """싣는 법령의 목록: {"id", "celex", "name", "url", "path", "consolidated", "rule", "group": "act", "format": "act"}. 받아 둔 글이 없는 것은 뺀다."""
    rules = rule_ids(read_json(RULES, {}))
    found = []
    for entry in (read_json(FULLTEXT, {}) or {}).get("entries", []):
        if entry.get("name") == BASE_NAME:
            code = str(entry.get("code", ""))
            dated = code.split("-", 1)[1] if "-" in code else ""
            found.append({"id": BASE_CELEX, "celex": BASE_CELEX, "name": "CBAM 규정", "url": EURLEX.format(code=code), "path": entry["textPath"],
                          "consolidated": f"{dated[:4]}-{dated[4:6]}-{dated[6:8]}" if len(dated) == 8 else "", "rule": rules.get(BASE_CELEX, "")})
    rest = [{"id": entry["celex"], "celex": entry["celex"], "name": entry.get("title", entry["celex"]), "url": entry.get("url") or EURLEX.format(code=entry["celex"]),
             "path": entry.get("textPath", ""), "consolidated": "", "rule": rules.get(entry["celex"], "")}
            for entry in (read_json(ACTS, {}) or {}).get("entries", []) if entry.get("celex") and entry.get("textPath")]
    rest.sort(key=lambda act: act["id"] in ORDER_LAST)  # 차례는 그대로 두고 지난 법령만 뒤로
    going = [act for act in rest if act["id"] not in ORDER_LAST]
    return [{**act, "group": "act", "format": "act"} for act in found + going + pending() + rest[len(going):]]
