"""인증서 가격 자료(data/prices.json)를 공식 가격표에서 새로 만든다. 출처 수집 뒤에 돈다.

쓰는 법: python -m tools.prices.run [--page collected/pages/ec-price.txt] [--out data/prices.json]
- 한 번 실은 가격은 화면에서 사라져도 지우지 않는다(2027년에 표가 주간 가격으로 바뀌어도 2026년 분기 가격이 남는다).
- 같은 기간의 가격이 바뀌면 새 값으로 고치고 revisions에 적는다.
- 읽지 못한 행은 unparsed에 적는다. 내용이 달라졌을 때만 파일을 다시 쓴다.
마지막 줄에 결과를 JSON으로 출력한다.
"""
import argparse
import json
import pathlib
import sys

from tools.common.jsonio import read_json, stamp, today, write_json
from tools.prices import parse

SOURCE = {
    "code": "ec-price",
    "name": "EC Price of CBAM Certificates",
    "url": "https://taxation-customs.ec.europa.eu/carbon-border-adjustment-mechanism/price-cbam-certificates_en",
}
KEEP = ("period", "kind", "label", "from", "to", "published", "value", "raw", "assumed")


def merge(old, priced, day):
    """이전 자료에 새로 읽은 행을 합친다. (가격 목록, 새로 실은 기간, 고친 기록)을 돌려준다."""
    book = {row["period"]: dict(row) for row in old}
    added, revised = [], []
    for row in priced:
        fresh = {key: row[key] for key in KEEP if key in row}
        before = book.get(row["period"])
        if before is None:
            fresh["firstSeen"] = day
            book[row["period"]] = fresh
            added.append(row["period"])
        else:
            if before.get("value") != fresh["value"]:
                revised.append({"period": row["period"], "was": before.get("value"), "now": fresh["value"], "at": day})
            fresh["firstSeen"] = before.get("firstSeen", day)
            book[row["period"]] = fresh
    return sorted(book.values(), key=lambda row: (row["from"], row["to"])), added, revised


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("--page", default="collected/pages/ec-price.txt")
    parser.add_argument("--out", default="data/prices.json")
    args = parser.parse_args(argv)
    page = pathlib.Path(args.page)
    if not page.is_file():
        print(json.dumps({"skipped": "가격 화면 글이 없음"}, ensure_ascii=False))
        return 0
    old = read_json(args.out, {}) or {}
    priced, upcoming, unparsed = parse.read(page.read_text(encoding="utf-8", errors="replace"))
    prices, added, revised = merge(old.get("prices", []), priced, today())
    known = {row["period"] for row in prices}
    body = {
        "source": SOURCE,
        "unit": "유로",
        "prices": prices,
        "upcoming": [{key: row[key] for key in KEEP if key in row} for row in upcoming if row["period"] not in known],
        "revisions": (old.get("revisions", []) + revised)[-50:],
        "unparsed": unparsed,
    }
    same = all(old.get(key) == body[key] for key in body)
    if not same:
        body["updated"] = stamp()
        write_json(args.out, body)
    print(json.dumps({"prices": len(prices), "added": added, "revised": revised, "upcoming": len(body["upcoming"]), "unparsed": unparsed, "written": not same}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
