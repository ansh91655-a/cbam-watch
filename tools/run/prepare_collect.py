"""수집·작성 실행이 다룰 후보를 고른다.

저장소의 collected/feed 에서 최근 며칠의 새 항목을 읽고, 데이터베이스에 이미 기록된 후보(candidates)를 뺀다.
쓰는 법: python -m tools.run.prepare_collect --db-dir /tmp/run/db --out /tmp/run/candidates.json [--days 5] [--limit 25]
"""
import argparse
import datetime
import sys

from tools.common.jsonio import now_kst, read_json, write_json
from tools.run import dbdump


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("--db-dir", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--days", type=int, default=5)
    parser.add_argument("--limit", type=int, default=25)
    args = parser.parse_args(argv)

    registry = read_json("sources/registry.json", {"sources": []})["sources"]
    by_code = {source["code"]: source for source in registry}
    by_code["ec-documents"] = {"code": "ec-documents", "name": "EC CBAM 문서(원문 대장)", "tier": "A", "group": "EU 공식",
                               "url": "https://taxation-customs.ec.europa.eu/carbon-border-adjustment-mechanism/cbam-legislation-and-guidance_en"}
    known = dbdump.ids(args.db_dir, "candidates")
    today = now_kst().date()
    fresh, waiting = [], 0
    for back in range(args.days - 1, -1, -1):  # 오래된 날부터
        date = (today - datetime.timedelta(days=back)).isoformat()
        feed = read_json(f"collected/feed/{date}.json", None)
        for item in (feed or {}).get("items", []):
            if item["id"] in known:
                continue
            if len(fresh) >= args.limit:
                waiting += 1
                continue
            source = by_code.get(item["source"], {})
            item.update({"feedDate": date, "sourceName": source.get("name", item["source"]), "tier": source.get("tier", "C"), "sourceUrl": source.get("url", "")})
            fresh.append(item)
    claude_sources = [{"code": s["code"], "name": s["name"], "url": s["url"], "tier": s["tier"], "note": s.get("note", "")} for s in registry if s.get("collector") == "claude"]
    status = read_json("collected/status.json", {})
    write_json(args.out, {"today": today.isoformat(), "candidates": fresh, "waiting": waiting, "claudeSources": claude_sources, "collectCheckedAt": status.get("checkedAt", "")})
    print(f"새 후보 {len(fresh)}건(다음으로 미룬 것 {waiting}건), 직접 열 출처 {len(claude_sources)}곳, 자동 수집 시각 {status.get('checkedAt', '없음')}")
    for item in fresh:
        print(f"  {item['id']} [{item['source']}/{item['kind']}/{item['tier']}] {item['text'][:80]}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
