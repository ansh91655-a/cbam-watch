"""법령에서 옮겨 온 참고 자료가 낡지 않았는지 본다. 실행 확인과 보고(tools.run.health)가 불러 쓴다.

참고 자료는 넷이다: CBAM 계수(data/factor.json), 실무 달력(data/duties.json), 인증서 비용 추정(data/calc.json, data/calc-goods.json), CBAM 해설서(data/handbook.json).
- 해설서는 절마다 근거로 적은 영문 대목이 받아 둔 법령과 안내 문서의 글에 그대로 있는지 본다. 원문이 개정되어 대목이 사라지면 그 절을 다시 봐야 한다.
- 의무 일정과 용어집의 근거에 적힌 조나 부속서가 사이트의 규정 원문에 없는 것도 알린다(tools.publish.crossrefs: 근거를 잘못 적었거나 받아 둔 글이 제대로 갈리지 않은 것).
- 받아 둔 법령 글과 어긋난 것('근거 어긋남')을 알린다. 사이트는 앞의 값으로 계속 돌지만, 글이 바뀐 것인지 자료가 틀린 것인지 사람이 봐야 한다.
- 꼴이 깨진 것도 알린다(이때는 사이트 만들기가 멈춘다).
- 인증서 비용 추정의 근거 법령(무상할당 조정 이행규정, 기본값 이행규정, 부문 간 보정계수 결정)을 고치거나 바로잡는 새 문서가
  법령 데이터베이스 목록에 보이면 알린다. CBAM 벤치마크는 2027년 수입분부터 갱신된 값이 적용될 예정이라 이 알림이 그때를 잡는다.
"""
from tools.check import term_check
from tools.common.jsonio import read_json
from tools.publish import calc, crossrefs, duties, factor, handbook

RELATED = "collected/archive/eur-lex-related.json"
LIMIT = 4  # 한 자료에서 알리는 줄 수(같은 까닭의 줄이 길게 이어지지 않게)


def _lines(name, found):
    lines = [f"{name}: {where}: {what}" for where, what in found[:LIMIT]]
    if len(found) > LIMIT:
        lines.append(f"{name}: 이 밖에 {len(found) - LIMIT}건")
    return lines


def handbook_lines(body=None):
    """해설서의 꼴이 깨진 것과, 근거로 적은 대목이 받아 둔 글에서 사라진 것."""
    body = read_json(handbook.SOURCE, None) if body is None else body
    if body is None:
        return [f"해설서: {handbook.SOURCE} 을 읽지 못함"]
    rules = {rule.get("id") for rule in (read_json("data/regulations.json", {}) or {}).get("regulations", [])}
    return _lines("해설서", handbook.problems(body, term_check.load(), rules=rules, texts=handbook.corpus_texts()))


def new_acts(terms, entries):
    """근거 법령을 제목에서 가리키는 문서 가운데 아직 반영하지 않은 것. [(CELEX 번호, 제목)]."""
    watch = (terms or {}).get("watch") or {}
    mentions, known = watch.get("mentions") or [], set(watch.get("known") or [])
    found = []
    for entry in entries:
        celex, title = str(entry.get("celex", "")), str(entry.get("title", ""))
        if celex and celex not in known and any(mention in title for mention in mentions):
            found.append((celex, title))
    return sorted(set(found))


def problems(entries=None):
    entries = read_json(RELATED, {}).get("entries", []) if entries is None else entries
    found = _lines("CBAM 계수", factor.problems(read_json(factor.SOURCE, None)))
    found += _lines("실무 달력", duties.problems(read_json(duties.SOURCE, None)))
    terms = read_json(calc.SOURCE, None)
    found += _lines("인증서 비용 추정", calc.problems(terms, read_json(calc.GOODS, None)))
    found += _lines("조문 잇기", crossrefs.source_problems())
    found += handbook_lines()
    for celex, title in new_acts(terms, entries):
        found.append(f"인증서 비용 추정: 근거 법령을 고치거나 바로잡는 것으로 보이는 새 문서 {celex}({title[:90]}). 표를 다시 받아 자료를 다시 만들어야 하는지 확인이 필요함")
    return found
