"""번역한 문단을 검사해서 번역 자료(data/laws-ko/)에 넣는다.

쓰는 법: python -m tools.laws.apply <번역 파일> [--dry] [--terms]
번역 파일은 {"blocks": {열쇠: 국문}} 꼴이다. 열쇠는 python -m tools.laws.todo 가 준 것이다.
문단마다 용어집 낱말의 띄어쓰기를 권장 표기로 맞춘 뒤(tools.laws.terms.unify) tools.laws.check로 원문과 견줘, 막는 까닭이 없는 것만 넣는다. 걸린 문단은 까닭과 함께 찍고 넣지 않는다(끝내는 값 1).
알릴 것(원문에 없는 수, 길이)은 찍기만 하고 넣는다. --dry는 검사만 한다. --terms는 용어집의 권고(막지 않는 것)도 찍는다.
"""
import argparse
import json
import sys

from tools.common.jsonio import read_json
from tools.laws import check, corpus, store, terms


def sources():
    """{열쇠: (그 문단이 처음 나오는 법령의 번호, 원문)}"""
    found = {}
    acts, _ = corpus.everything()
    for act, parts in acts:
        for part in parts:
            for text in corpus.texts(part):
                if check.needs(text):
                    found.setdefault(store.key(text), (act["id"], text))
    return found


def sort(blocks, known=None):
    """번역을 받아들일 것과 걸린 것으로 가른다: ({법령: {열쇠: 국문}}, [(열쇠, 까닭들)], [(열쇠, 알릴 것들)])"""
    known = known if known is not None else sources()
    accepted, rejected, noted = {}, [], []
    for block_key, korean in blocks.items():
        if block_key not in known:
            rejected.append((block_key, ["원문에 없는 열쇠(원문이 바뀌었거나 잘못 적음)"]))
            continue
        act_id, source = known[block_key]
        korean = terms.unify(source, korean)  # 용어집 낱말의 띄어쓰기를 권장 표기로 맞춘다
        found = check.problems(source, korean)
        if found["hard"]:
            rejected.append((block_key, found["hard"]))
            continue
        if found["soft"]:
            noted.append((block_key, found["soft"]))
        accepted.setdefault(act_id, {})[block_key] = " ".join(str(korean).split())
    return accepted, rejected, noted


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("file")
    parser.add_argument("--dry", action="store_true")
    parser.add_argument("--terms", action="store_true")
    args = parser.parse_args(argv)
    blocks = (read_json(args.file, {}) or {}).get("blocks", {})
    if not isinstance(blocks, dict) or not blocks:
        print("번역 파일에 blocks가 없습니다.")
        return 1
    accepted, rejected, noted = sort(blocks)
    if not args.dry:
        for act_id, fresh in accepted.items():
            store.save(act_id, {**store.load(act_id), **fresh})
    for block_key, why in noted:  # 용어집의 권고(막지 않는 것)는 --terms를 줄 때만 찍는다. 낱말의 일부가 걸리는 일이 많다
        shown = [text for text in why if args.terms or not text.startswith("용어:")]
        if shown:
            print(f"알림 {block_key}: {'; '.join(shown)}")
    for block_key, why in rejected:
        print(f"걸림 {block_key}: {'; '.join(why)}")
    print(json.dumps({"accepted": sum(len(fresh) for fresh in accepted.values()), "rejected": len(rejected), "noted": len(noted), "saved": not args.dry}, ensure_ascii=False))
    return 1 if rejected else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
