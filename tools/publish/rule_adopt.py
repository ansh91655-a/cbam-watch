"""EU 집행위원회가 하위 법령을 채택했으나 아직 관보에 실리지 않은 동안, 규제 자료의 그 항목을 '채택된 법령'의 모습으로 바꾼다.

  python -m tools.publish.rule_edit adopt --id <규제> --reference "C(2026) 8367 final" --link "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=PI_COM:C(2026)8367"

위임규정은 채택된 뒤에도 유럽의회와 EU 이사회의 이의 제기 기간을 거쳐야 관보에 실린다. 그동안 규제는 '준비 중인 하위 법령' 묶음에 남는다.
바꾸는 것
  - 이름: 끝에 붙은 '(안)', '(계획)'을 뗀다(--name으로 따로 줄 수 있다).
  - 종류: '위임규정(안)' → '위임규정(채택)'. 관보에 실리면 enact가 '(채택)'을 뗀다.
  - 공식 이름(official): 채택 문서의 번호를 맨 앞에 놓는다("C(2026) 8367 final · 의견수렴 14132 …").
  - 링크: 채택된 글(EUR-Lex)을 맨 앞에 놓는다. 의견수렴 같은 옛 링크는 뒤에 남는다.
바꾸지 않는 것: 묶음, 단계, 설명, 연혁, 다음 일정. 이것들은 add-event, set으로 고친다(절차서 20의 '집행위원회가 채택한 날').
"""
from tools.common.jsonio import today
from tools.publish.rule_enact import KINDS, finished

MARK = "(채택)"
LINK_TEXT = "채택된 {kind}(EUR-Lex, 관보 게재 전)"


def adopt(body, args):
    rule = next((old for old in body.get("regulations", []) if old.get("id") == args.id), None)
    if rule is None:
        raise SystemExit(f"없는 규제: {args.id}")
    reference, link = str(args.reference or "").strip(), str(args.link or "").strip()
    if not reference:
        raise SystemExit("채택 문서의 번호가 비어 있음(--reference \"C(2026) 8367 final\")")
    if not link.startswith("https://"):
        raise SystemExit("채택된 글의 주소가 https로 시작하지 않음(--link)")
    kind = finished(getattr(args, "kind", None) or rule.get("kind"))
    if kind not in KINDS:
        raise SystemExit(f"종류를 알 수 없음: {kind}(--kind 이행규정 또는 --kind 위임규정으로 준다)")
    if reference in str(rule.get("official", "")):
        raise SystemExit("이미 그 문서로 적혀 있음")
    rule.update({"kind": kind + MARK, "name": getattr(args, "name", None) or finished(rule.get("name")),
                 "official": " · ".join(part for part in (reference, str(rule.get("official", "")).strip()) if part)})
    rule["links"] = [{"text": LINK_TEXT.format(kind=kind), "url": link}] + [old for old in rule.get("links", []) if old.get("url") != link]
    rule["changedOn"] = today()
