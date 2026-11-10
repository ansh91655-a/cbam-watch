"""EU 법령 데이터베이스(CELLAR)에 물어, CBAM 규정과 이어진 법령·입법안을 빠짐없이 모은다.

EU 출판국의 SPARQL 창구에 "이 법령을 가리키는 모든 문서"를 묻는다. 근거 법령으로 삼은 것(이행·위임규정),
고치는 것, 바로잡는 것, 고치자고 제안하는 것, 인용하는 것이 관계 이름과 함께 돌아온다. 제목에 낱말이 든 문서도 따로 찾는다.
결과는 목록(collected/archive/eur-lex-related.json)으로만 남기고 본문은 받지 않는다.
"""
import json
import time
import urllib.parse

from tools.archive.store import save_index
from tools.common.net import fetch

ENDPOINT = "https://publications.europa.eu/webapi/rdf/sparql"
BASES = ["32023R0956", "32025R2083"]  # CBAM 규정, 간소화 개정 규정
PREFIX = """PREFIX cdm: <http://publications.europa.eu/ontology/cdm#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
"""
ENG = "<http://publications.europa.eu/resource/authority/language/ENG>"

LINKS = PREFIX + """SELECT DISTINCT ?p ?celex ?date ?title WHERE {{
  {{ ?base cdm:resource_legal_id_celex "{celex}"^^xsd:string }} UNION {{ ?base owl:sameAs <http://publications.europa.eu/resource/celex/{celex}> }}
  ?work ?p ?base .
  ?work cdm:resource_legal_id_celex ?celex .
  OPTIONAL {{ ?work cdm:work_date_document ?date }}
  OPTIONAL {{ ?exp cdm:expression_belongs_to_work ?work ; cdm:expression_uses_language {eng} ; cdm:expression_title ?title }}
}} LIMIT 4000"""

TITLES = PREFIX + """SELECT DISTINCT ?celex ?date ?title WHERE {{
  ?exp cdm:expression_title ?title .
  ?title bif:contains "{words}" .
  ?exp cdm:expression_uses_language {eng} ; cdm:expression_belongs_to_work ?work .
  ?work cdm:resource_legal_id_celex ?celex .
  OPTIONAL {{ ?work cdm:work_date_document ?date }}
  FILTER(!BOUND(?date) || ?date >= "2025-01-01"^^xsd:date)
}} LIMIT 2000"""

WORDS = ["'carbon border adjustment'", "CBAM", "'Temporary Decarbonisation Fund'"]
# CBAM 규정을 다투는 EU 법원 사건의 문서 번호(판결 CJ, 법무관 의견 CC, 명령 CO, 제소 공고 CN). 데이터베이스에 있는지만 묻는다.
CASES = ["62023CJ0512", "62023CC0512", "62023CO0512", "62023CN0512", "62024CJ0519", "62024CC0519", "62024CO0519"]
KNOWN = PREFIX + """SELECT DISTINCT ?celex ?date WHERE {{
  VALUES ?celex {{ {values} }}
  ?work cdm:resource_legal_id_celex ?celex .
  OPTIONAL {{ ?work cdm:work_date_document ?date }}
}}"""


def ask(query):
    """질의를 보내 결과 줄의 목록을 돌려준다. 실패하면 (빈 목록, 사유)."""
    url = ENDPOINT + "?" + urllib.parse.urlencode({"query": query, "format": "application/sparql-results+json", "timeout": "120000"})
    status, _, body, error = fetch(url, timeout=180, retries=1, headers={"Accept": "application/sparql-results+json"})
    time.sleep(2)
    if status != 200 or not body:
        return [], f"{status} {error[:80]} {body[:120].decode('utf-8', 'replace') if body else ''}"
    try:
        rows = json.loads(body.decode("utf-8", "replace"))["results"]["bindings"]
    except Exception as problem:
        return [], f"결과를 풀지 못함: {problem}"
    return [{name: cell.get("value", "") for name, cell in row.items()} for row in rows], ""


def crawl():
    found, report = {}, {"links": {}, "titles": {}, "failures": []}
    for base in BASES:
        rows, error = ask(LINKS.format(celex=base, eng=ENG))
        if error:
            report["failures"].append(f"{base}: {error}")
        report["links"][base] = len(rows)
        for row in rows:
            relation = row.get("p", "").rsplit("#", 1)[-1]
            entry = found.setdefault(row["celex"], {"celex": row["celex"], "date": row.get("date", "")[:10], "title": row.get("title", ""), "relations": []})
            entry["title"] = entry["title"] or row.get("title", "")
            label = f"{relation}:{base}"
            if label not in entry["relations"]:
                entry["relations"].append(label)
    for words in WORDS:
        rows, error = ask(TITLES.format(words=words, eng=ENG))
        if error:
            report["failures"].append(f"제목 '{words}': {error}")
        report["titles"][words] = len(rows)
        for row in rows:
            entry = found.setdefault(row["celex"], {"celex": row["celex"], "date": row.get("date", "")[:10], "title": row.get("title", ""), "relations": []})
            entry["title"] = entry["title"] or row.get("title", "")
            if "title-match" not in entry["relations"]:
                entry["relations"].append("title-match")
    rows, error = ask(KNOWN.format(values=" ".join(f'"{celex}"^^xsd:string' for celex in CASES)))
    if error:
        report["failures"].append(f"법원 사건: {error}")
    report["cases"] = {celex: next((row.get("date", "")[:10] or "날짜 없음" for row in rows if row.get("celex") == celex), "없음") for celex in CASES}
    entries = sorted(found.values(), key=lambda entry: (entry["date"], entry["celex"]), reverse=True)
    for entry in entries:
        entry["url"] = f"https://eur-lex.europa.eu/legal-content/EN/ALL/?uri=CELEX:{entry['celex']}"
    report["works"] = len(entries)
    save_index("eur-lex-related", entries, report)
    return report
