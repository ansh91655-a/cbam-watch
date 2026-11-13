"""제목만 옮겨 실은 소식(brief)의 요약을, 본문을 읽고 다시 쓴 것으로 바꾼다.

쓰는 법:
  python -m tools.publish.revise --list 12
      다시 쓸 대상을 JSON으로 찍는다. 자료와 동향을 먼저, 날짜가 가까운 것부터 고른다.
      지난 행사 안내(60일 넘은 것), 글 하나를 가리키지 않는 링크(여러 소식이 같은 주소를 쓰는 것), 이미 살펴보고 그대로 두기로 한 것,
      사이트가 자동 읽기를 막아 둔 출처의 소식은 뺀다.
  python -m tools.publish.revise --id <소식 id> --summary-file <새 요약 파일> --source-file <본문에서 뽑은 글 파일> [--impact "<실무 영향 한 문장>"]
      새 요약을 검사하고(문체, 용어, 길이, 수치와 날짜가 뽑은 글에 있는지) 통과하면 data/items.json의 그 소식을 고친다.
      brief 표시를 떼고 고친 날(revised)을 적는다.
  python -m tools.publish.revise --id <소식 id> --keep
      본문에 제목보다 더 알려 주는 것이 없을 때: 요약은 그대로 두고, 다시 고르지 않게 살펴본 날(briefChecked)만 적는다.
  python -m tools.publish.revise --id <소식 id> --fail
      그 글을 읽지 못했거나 새 요약이 검사를 끝내 통과하지 못했을 때: 해 본 횟수(briefTries)만 올린다.
      두 번 실패한 소식은 다시 고르지 않는다(한 줄로 남는다).
  python -m tools.publish.revise --id <소식 id> --correct --summary-file <새 요약 파일> --source-file <근거가 되는 글 파일> [--title "<새 제목>"] [--impact "…"] [--importance 높음]
      이미 실은 소식(brief가 아닌 것)을 바로잡는다: 나중에 확인된 결론을 더하거나 틀린 곳을 고칠 때 쓴다. 검사는 위와 같고, 제목도 문체와 용어를 본다.
      고친 날(revised)을 적는다. 소식의 날짜와 출처, 링크는 그대로다.
검사에 걸리면 고치지 않고 1로 끝난다. 뽑은 글 파일은 저장소 밖에 둔다(저장소에 올리지 않는다).
"""
import argparse
import collections
import datetime
import json
import pathlib
import sys

from tools.check import fact_check, style_check, term_check
from tools.common.jsonio import read_json, today, write_json

ITEMS = "data/items.json"
OLD_EVENT_DAYS = 60
SHORT, LONG = 60, 600  # 새 요약의 길이(글자)
MAX_TRIES = 2  # 이만큼 실패한 소식은 다시 고르지 않는다
# 사이트가 자동 읽기를 막아 둔 출처(robots.txt). 글을 열어 볼 수 없으므로 고르지 않는다. 이 출처의 소식은 한 줄로 남는다.
NO_AUTO_READ = {"compass"}


def candidates(items, limit, now=None):
    """다시 쓸 대상을 고른다."""
    now = now or today()
    shared = {link for link, count in collections.Counter(item.get("link", "") for item in items).items() if count > 1}
    cutoff = (datetime.date.fromisoformat(now) - datetime.timedelta(days=OLD_EVENT_DAYS)).isoformat()
    rows = [item for item in items if item.get("brief") and not item.get("briefChecked") and not item.get("withdrawn")
            and int(item.get("briefTries", 0) or 0) < MAX_TRIES and item.get("sourceCode") not in NO_AUTO_READ and item.get("link") not in shared and not (item.get("kind") == "행사" and str(item.get("published", "")) < cutoff)]
    rows.sort(key=lambda item: str(item.get("published", "")), reverse=True)
    rows.sort(key=lambda item: item.get("kind") == "행사")  # 자료와 동향을 먼저
    return [{key: item.get(key, "") for key in ("id", "published", "title", "summary", "kind", "sourceCode", "sourceName", "link")} for item in rows[:limit]]


def problems(old, summary, impact, source, term_index=None):
    """새 요약의 문제를 글의 목록으로 돌려준다."""
    found = []
    if not SHORT <= len(summary) <= LONG:
        found.append(f"요약의 길이가 {SHORT}~{LONG}자가 아님({len(summary)}자)")
    if summary.strip() == str(old.get("summary", "")).strip():
        found.append("요약이 전과 같음")
    text = "\n".join(part for part in (summary, impact) if part)
    found += [f"문체({hit['rule']}: {hit['sample']})" for hit in style_check.check(text) if hit["hard"]]
    found += [f"쓰지 않는 용어({hit['avoid']} → {hit['use']})" for hit in term_check.check(text, term_index or term_check.load()) if hit["hard"]]
    if not source.strip():
        found.append("본문에서 뽑은 글이 비어 있음")
    else:
        result = fact_check.check(text, str(old.get("title", "")) + "\n" + source)
        if not result["ok"]:
            found.append("사실 대조: 뽑은 글에서 찾지 못함 " + ", ".join(result["missingDates"] + result["missingNumbers"])[:120])
    return found


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("--list", type=int, default=0)
    parser.add_argument("--id", default="")
    parser.add_argument("--summary-file", default="")
    parser.add_argument("--source-file", default="")
    parser.add_argument("--impact", default="")
    parser.add_argument("--keep", action="store_true")
    parser.add_argument("--fail", action="store_true")
    parser.add_argument("--correct", action="store_true")
    parser.add_argument("--title", default="")
    parser.add_argument("--importance", default="", choices=["", "높음", "보통", "낮음"])
    args = parser.parse_args(argv)
    body = read_json(ITEMS, None)
    if body is None:
        print("data/items.json 을 읽지 못함")
        return 1
    items = body.get("items", [])
    if args.list:
        print(json.dumps({"left": len(candidates(items, 10 ** 6)), "items": candidates(items, args.list)}, ensure_ascii=False, indent=1))
        return 0
    item = next((row for row in items if row.get("id") == args.id), None)
    if item is None or item.get("withdrawn") or not (item.get("brief") or args.correct):
        print(f"다시 쓸 대상이 아님: {args.id}")
        return 1
    if args.keep:
        item["briefChecked"] = today()
        write_json(ITEMS, body)
        print(json.dumps({"ok": True, "id": args.id, "kept": True}, ensure_ascii=False))
        return 0
    if args.fail:
        item["briefTries"] = int(item.get("briefTries", 0) or 0) + 1
        write_json(ITEMS, body)
        print(json.dumps({"ok": True, "id": args.id, "tries": item["briefTries"], "again": item["briefTries"] < MAX_TRIES}, ensure_ascii=False))
        return 0
    try:
        summary = " ".join(pathlib.Path(args.summary_file).read_text(encoding="utf-8").split())
        source = pathlib.Path(args.source_file).read_text(encoding="utf-8", errors="replace")
    except OSError as error:
        print(f"파일을 읽지 못함: {error}")
        return 1
    title = " ".join(args.title.split()) if args.correct else ""
    found = problems(item, summary, "\n".join(part for part in (args.impact.strip(), title) if part), source)
    if found:
        for line in found:
            print("문제:", line)
        print("문제가 있어 고치지 않았습니다.")
        return 1
    item["summary"] = summary
    if args.impact.strip():
        item["impact"] = args.impact.strip()
    if title:
        item["title"] = title
    if args.correct and args.importance:
        item["importance"] = args.importance
    item.pop("brief", None)
    item.pop("briefTries", None)
    item["revised"] = today()
    write_json(ITEMS, body)
    print(json.dumps({"ok": True, "id": args.id, "revised": item["revised"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
