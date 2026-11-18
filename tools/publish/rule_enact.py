"""준비 중이던 하위 법령이 관보에 실렸을 때, 규제 자료의 그 항목을 '나온 법령'의 모습으로 바꾼다.

  python -m tools.publish.rule_edit enact --id <규제> --celex 32026R2498 [--name "…"] [--kind 이행규정] [--after <규제 id>]

바꾸는 것
  - 묶음: 시행 중인 하위 법령(eu-acts)으로 옮긴다. 자리는 그 묶음에서 끝난 법령(tone이 ended)보다 앞, 나머지의 맨 뒤다(--after로 고를 수 있다).
  - 이름과 종류: 끝에 붙은 '(안)', '(계획)'을 뗀다(--name, --kind로 따로 줄 수 있다).
  - 공식 이름(official): "Implementing Regulation (EU) 2026/2498"처럼 법령 번호로 바꾼다. 법령 전문 화면은 이 번호로 규제와 이어진다.
  - 링크: 법령 원문(EUR-Lex)을 맨 앞에 놓는다. 의견수렴 같은 옛 링크는 뒤에 남는다.
  - 관련 낱말: 법령 번호(2026/2498)를 더한다. 모은 글에서 이 규제의 소식을 찾을 때 쓴다.
바꾸지 않는 것: 단계, 설명, 연혁, 다음 일정. 이것들은 set, add-event, drop-event로 고친다.
"""
import re

from tools.common.jsonio import today

GROUP = "eu-acts"
CELEX = re.compile(r"^3(\d{4})R(\d{4})$")
DRAFT = re.compile(r"\s*\((?:안|계획)\)\s*$")
KINDS = {"이행규정": ("Implementing Regulation (EU)", "이행규정 원문(EUR-Lex)"),
         "위임규정": ("Delegated Regulation (EU)", "위임규정 원문(EUR-Lex)")}
EURLEX = "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:{celex}"


def number(celex):
    """CELEX 번호를 법령 번호로: 32026R2498 → 2026/2498, 32025R0486 → 2025/486."""
    found = CELEX.match(str(celex or ""))
    if not found:
        raise SystemExit(f"규정의 CELEX 번호가 아님: {celex}(3 + 연도 + R + 네 자리 번호, 예: 32026R2498)")
    return f"{found.group(1)}/{int(found.group(2))}"


def finished(text):
    """이름이나 종류의 끝에 붙은 '(안)', '(계획)'을 뗀다."""
    return DRAFT.sub("", str(text or ""))


def place(rules, rule, after=""):
    """규제를 목록에서 꺼내 새 묶음의 제자리에 놓는다."""
    rest = [old for old in rules if old is not rule]
    if after:
        spots = [index for index, old in enumerate(rest) if old.get("id") == after]
        if not spots:
            raise SystemExit(f"없는 규제: {after}")
        spot = spots[0]
    else:
        same = [index for index, old in enumerate(rest) if old.get("group") == rule["group"]]
        going = [index for index in same if rest[index].get("tone") != "ended"]
        spot = going[-1] if going else (same[0] - 1 if same else len(rest) - 1)
    rest.insert(spot + 1, rule)
    rules[:] = rest


def enact(body, args):
    rule = next((old for old in body.get("regulations", []) if old.get("id") == args.id), None)
    if rule is None:
        raise SystemExit(f"없는 규제: {args.id}")
    if not any(group.get("code") == GROUP for group in body.get("groups", [])):
        raise SystemExit(f"없는 묶음: {GROUP}")
    law = number(args.celex)
    kind = getattr(args, "kind", None) or finished(rule.get("kind"))
    if kind not in KINDS:
        raise SystemExit(f"종류를 알 수 없음: {kind}(--kind 이행규정 또는 --kind 위임규정으로 준다)")
    title, link_text = KINDS[kind]
    official = f"{title} {law}"
    if official in str(rule.get("official", "")):
        raise SystemExit("이미 그 법령으로 적혀 있음")
    url = EURLEX.format(celex=args.celex)
    rule.update({"group": GROUP, "kind": kind, "official": official, "name": getattr(args, "name", None) or finished(rule.get("name"))})
    rule["links"] = [{"text": link_text, "url": url}] + [link for link in rule.get("links", []) if link.get("url") != url]
    related = rule.setdefault("related", {})
    related["words"] = list(related.get("words", [])) + ([] if law in related.get("words", []) else [law])
    rule["changedOn"] = today()
    place(body["regulations"], rule, getattr(args, "after", None) or "")
