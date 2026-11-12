"""규정 원문 화면에 싣는 법령의 목록. 저장소에 본문을 받아 둔 것만 싣는다.

CBAM 규정은 통합본(collected/archive/eu-fulltext.json의 cbam-consolidated)을, 하위 법령은 collected/archive/eu-acts.json에 적힌 차례대로 싣는다.
이 차례가 화면에 보이는 차례이자 번역하는 차례다(ORDER_LAST에 적은 것은 맨 뒤로 보낸다).
법령마다 규제 자료(data/regulations.json)의 어느 규제에 해당하는지를 법령 번호로 찾아 적는다.
"""
import re

from tools.common.jsonio import read_json

ACTS = "collected/archive/eu-acts.json"
FULLTEXT = "collected/archive/eu-fulltext.json"
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
    return [{**act, "group": "act", "format": "act"} for act in found + rest]
