"""검사에 걸려 번역이 들어가지 못한 문단을 보고, 까닭을 고친 뒤 다시 주게 한다.

걸린 문단은 번역 자료의 held에 걸린 횟수와 까닭이 적힌다(tools.laws.store). 세 번 걸리면 줄의 뒤로 돌려지고 여섯 번이면 더 주지 않는다.
까닭이 검사나 용어집 쪽에 있으면(다른 뜻으로 쓰인 낱말, 용어집에 없는 겹낱말, 깨진 원문) 그쪽을 고친 다음 횟수를 지워 다시 주게 한다.

쓰는 법(저장소 맨 위에서)
  python3 -m tools.laws.held                 걸린 문단을 찍는다: 열쇠, 문서, 걸린 횟수, 까닭, 원문의 앞머리
  python3 -m tools.laws.held --reset [열쇠 …]  걸린 횟수를 지운다(열쇠를 주지 않으면 모두). 다음 번역 묶음에 다시 나온다
"""
import argparse
import pathlib
import sys

from tools.common.jsonio import read_json, write_json
from tools.laws import apply, store


def rows():
    """[{"key", "act", "tries", "why", "text"}] 걸린 횟수가 많은 것부터. 번역이 들어갔거나 지금의 문서에 없는 문단은 뺀다."""
    known, memory = apply.sources(), store.load_all()
    found = [{"key": block_key, "act": known[block_key][0], "tries": row["tries"], "why": row["why"], "text": known[block_key][1]}
             for block_key, row in store.held_all().items() if block_key in known and block_key not in memory]
    return sorted(found, key=lambda row: (-row["tries"], row["act"], row["key"]))


def reset(block_keys=()):
    """걸린 횟수를 지운다. block_keys가 비어 있으면 모두. 지운 열쇠의 수를 돌려준다."""
    wanted, cleared = set(block_keys), 0
    for path in sorted(pathlib.Path(store.FOLDER).glob("*.json")):
        body = read_json(path, {}) or {}
        held = body.get("held") or {}
        kept = {block_key: row for block_key, row in held.items() if wanted and block_key not in wanted}
        if len(kept) != len(held):
            cleared += len(held) - len(kept)
            if kept:
                body["held"] = kept
            else:
                body.pop("held", None)
            write_json(path, body)
    return cleared


def main(argv):
    parser = argparse.ArgumentParser(description="검사에 걸린 문단")
    parser.add_argument("--reset", nargs="*", default=None, metavar="열쇠")
    args = parser.parse_args(argv)
    if args.reset is not None:
        print(f"걸린 횟수를 지운 문단 {reset(args.reset)}개")
        return 0
    found = rows()
    for row in found:
        print(f"{row['key']}  {row['act']:<20} {row['tries']}번  {row['why']}\n    {' '.join(row['text'].split())[:160]}")
    print(f"걸린 문단 {len(found)}개(뒤로 돌린 것 {sum(row['tries'] >= store.HOLD_AFTER for row in found)}개, 더 주지 않는 것 {sum(row['tries'] >= store.GIVE_UP for row in found)}개)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
