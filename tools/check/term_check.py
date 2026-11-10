"""국문 글에서 용어집이 '쓰지 않는 표기'로 정한 낱말을 찾는다.

쓰는 법: python -m tools.check.term_check --text-file 글.txt  (또는 --text "글")
결과는 JSON 한 줄이다. hard가 참인 것이 하나라도 있으면 ok는 거짓이다.
"""
import argparse
import json
import re
import sys

GLOSSARY = "language/glossary.json"


def _pattern(form):
    """띄어쓰기가 달라도 같은 표기로 보도록 낱말 사이의 공백을 느슨하게 맞춘다."""
    parts = [re.escape(part) for part in form.split()]
    return re.compile(r"\s*".join(parts)) if parts else None


def load(path=GLOSSARY):
    with open(path, encoding="utf-8") as handle:
        terms = json.load(handle)["terms"]
    accepted = set()
    for term in terms:
        for form in re.split(r"\s*/\s*", term["preferred"]) + list(term.get("allowed", [])):
            if form.strip():
                accepted.add(form.strip())
    rules = []
    for term in terms:
        use = re.split(r"\s*/\s*", term["preferred"])[0].strip()
        for avoid in term.get("avoid", []):
            form = avoid.get("form", "").strip()
            if not form or avoid.get("descriptive"):
                continue
            # 다른 용어의 권장 표기와 같거나 그 일부인 표기는 문맥을 봐야 하므로 참고로만 알린다.
            shields = sorted((item for item in accepted if form in item and item != form), key=len, reverse=True)
            soft = bool(avoid.get("conditional")) or form in accepted or bool(shields) or len(form.replace(" ", "")) < 3
            rules.append({"avoid": form, "use": use, "en": (term.get("en") or [""])[0], "hard": not soft, "note": avoid.get("note", ""),
                          "pattern": _pattern(form), "shields": shields})
    return {"rules": rules}


def check(text, index):
    """쓰지 않는 표기가 나온 곳을 찾는다. 그 표기를 품은 권장 표기 안의 글자는 세지 않는다."""
    hits = []
    for rule in index["rules"]:
        if rule["pattern"] is None:
            continue
        masked = text
        for shield in rule["shields"]:
            if shield in masked:
                masked = masked.replace(shield, "#" * len(shield))
        found = rule["pattern"].findall(masked)
        if found:
            hits.append({"avoid": rule["avoid"], "use": rule["use"], "en": rule["en"], "hard": rule["hard"], "count": len(found), "note": rule["note"]})
    return hits


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("--glossary", default=GLOSSARY)
    parser.add_argument("--text", default="")
    parser.add_argument("--text-file", default="")
    args = parser.parse_args(argv)
    text = args.text
    if args.text_file:
        with open(args.text_file, encoding="utf-8") as handle:
            text += "\n" + handle.read()
    hits = check(text, load(args.glossary))
    print(json.dumps({"ok": not any(hit["hard"] for hit in hits), "hits": hits}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
