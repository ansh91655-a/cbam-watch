"""같은 일을 두 번 실은 소식을 하나로 묶는다. 남길 소식은 두고, 묶이는 소식은 소식 목록에서 빼서 data/merged.json에 옮겨 적는다.

쓰는 법:
  python -m tools.publish.merge --id <묶이는 소식> --into <남길 소식> --reason "<왜 같은 일인지, 120자 이내>"
      [--summary-file <남길 소식의 새 요약> --source-file <근거가 되는 글>]
- 묶이는 소식을 가리키던 주간 요약의 번호는 남길 소식의 번호로 바꾼다.
- 사이트는 묶인 소식의 옛 주소(#item-<번호>)를 남긴 소식으로 넘긴다(빌드가 data/merged.json에서 옮겨 간 곳의 표를 만든다).
- 새 요약을 주면 다시 쓴 요약과 같은 검사(문체, 용어, 길이, 수치와 날짜가 근거 글에 있는지)를 거친 뒤에만 바꾼다.
검사에 걸리거나 번호가 맞지 않으면 아무것도 바꾸지 않고 1로 끝난다. 묶인 소식은 지우지 않고 merged.json에 그대로 남는다.
"""
import argparse
import json
import pathlib
import sys

from tools.common.jsonio import read_json, stamp, today, write_json
from tools.publish import revise

ITEMS = "data/items.json"
DIGESTS = "data/digests.json"
MERGED = "data/merged.json"


def moved(records, live_ids):
    """묶인 소식의 번호 → 지금 남아 있는 소식의 번호. 여러 번 묶인 것은 끝까지 따라간다. 끝이 남아 있지 않으면 싣지 않는다."""
    step = {row.get("id"): row.get("into") for row in records}
    table = {}
    for start in step:
        target, hops = step[start], 0
        while target in step and hops < len(step):
            target, hops = step[target], hops + 1
        if target in live_ids:
            table[start] = target
    return table


def swap_ids(digests, old, new):
    """주간 요약이 가리키는 번호를 바꾼다. 같은 번호가 겹치면 하나만 둔다. 바뀐 요약의 수를 돌려준다."""
    changed = 0
    for digest in digests:
        ids = digest.get("itemIds", [])
        if old in ids:
            seen = []
            for item_id in (new if item_id == old else item_id for item_id in ids):
                if item_id not in seen:
                    seen.append(item_id)
            digest["itemIds"] = seen
            changed += 1
    return changed


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", required=True)
    parser.add_argument("--into", required=True)
    parser.add_argument("--reason", required=True)
    parser.add_argument("--summary-file", default="")
    parser.add_argument("--source-file", default="")
    args = parser.parse_args(argv)
    body = read_json(ITEMS, None)
    if body is None:
        print("data/items.json 을 읽지 못함")
        return 1
    items = body.get("items", [])
    gone = next((row for row in items if row.get("id") == args.id), None)
    kept = next((row for row in items if row.get("id") == args.into), None)
    if gone is None or kept is None or gone is kept or kept.get("withdrawn"):
        print(json.dumps({"merged": False, "problem": "번호가 맞지 않음(없는 소식이거나, 같은 소식이거나, 남길 소식의 요약이 내려져 있음)"}, ensure_ascii=False))
        return 1
    if args.summary_file:
        try:
            summary = " ".join(pathlib.Path(args.summary_file).read_text(encoding="utf-8").split())
            source = pathlib.Path(args.source_file).read_text(encoding="utf-8", errors="replace")
        except OSError as error:
            print(f"파일을 읽지 못함: {error}")
            return 1
        found = revise.problems(kept, summary, "", source)
        if found:
            for line in found:
                print("문제:", line)
            print("문제가 있어 묶지 않았습니다.")
            return 1
        kept["summary"] = summary
        kept["revised"] = today()
    body["items"] = [row for row in items if row is not gone]
    body["builtAt"] = stamp()
    record = read_json(MERGED, {"merged": []})
    record["merged"] = [row for row in record.get("merged", []) if row.get("id") != args.id] + [
        {"id": args.id, "into": args.into, "reason": args.reason.strip()[:120], "at": stamp(), "item": gone}]
    digests = read_json(DIGESTS, {"digests": []})
    changed = swap_ids(digests.get("digests", []), args.id, args.into)
    write_json(ITEMS, body)
    write_json(MERGED, record)
    if changed:
        write_json(DIGESTS, digests)
    print(json.dumps({"merged": True, "id": args.id, "into": args.into, "digests": changed, "left": len(body["items"])}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
