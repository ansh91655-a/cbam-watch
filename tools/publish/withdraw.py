"""게시한 항목의 요약을 내린다(다시 대조했더니 원문과 어긋난 경우). 항목을 지우지는 않는다.

쓰는 법: python -m tools.publish.withdraw --id <항목 id> --reason "<어긋난 내용, 120자 이내>"
내린 항목은 사이트에서 제목과 원문 링크만 보이고, 요약 자리에 다시 확인하고 있다는 안내가 나온다.
"""
import argparse
import json
import sys

from tools.common.jsonio import read_json, stamp, write_json

PATH = "data/items.json"


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", required=True)
    parser.add_argument("--reason", required=True)
    args = parser.parse_args(argv)
    data = read_json(PATH, {"items": []})
    target = next((item for item in data["items"] if item.get("id") == args.id), None)
    if target is None:
        print(json.dumps({"withdrawn": False, "problem": "그런 항목이 없음"}, ensure_ascii=False))
        return 1
    if not target.get("withdrawn"):
        target["withdrawn"] = {"at": stamp(), "reason": args.reason.strip()[:120]}
        data["builtAt"] = stamp()
        write_json(PATH, data)
    print(json.dumps({"withdrawn": True, "id": args.id}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
