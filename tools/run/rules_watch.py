"""규제 진행 상황에 쓰는 공식 기록이 지난번에 본 뒤로 달라졌는지 찾는다.

쓰는 법: python -m tools.run.rules_watch            달라진 것을 JSON으로 찍는다(달라진 것이 있어도 0으로 끝난다)
        python -m tools.run.rules_watch --accept   지금 상태를 '본 것'으로 적는다(규제 자료에 반영한 뒤에 돌린다)
보는 것: 유럽의회 절차의 사건·단계·예정 일정, 집행위 의견수렴의 단계, EU 법령 데이터베이스의 연관 문서와 법원 사건,
        집행위 보도자료, 영국 법령, 미국 연방관보 공고. 본 것은 data/rules-seen.json에 적는다.
"""
import argparse
import json
import sys

from tools.common.jsonio import read_json, stamp, write_json

ARCHIVE = "collected/archive/"
SEEN = "data/rules-seen.json"


def entries(name):
    return read_json(f"{ARCHIVE}{name}.json", {}).get("entries", [])


def report(name):
    return read_json(f"{ARCHIVE}{name}.json", {}).get("report", {})


def snapshot():
    """기록마다 {열쇠: 값}의 꼴로 지금 상태를 모은다. 값이 바뀌면 달라진 것으로 본다."""
    procedures = {reference: info for reference, info in report("ep-oeil").get("procedures", {}).items() if isinstance(info, dict)}
    return {
        "의회 절차의 사건": {f"{row['procedure']} {row['date']} {row['event']}": row.get("reference", "") for row in entries("ep-oeil")},
        "의회 절차의 단계": {reference: info.get("status", "") for reference, info in procedures.items()},
        "의회 절차의 예정 일정": {reference: "; ".join(f"{row['date']} {row['subject']}" for row in info.get("forecasts", [])) for reference, info in procedures.items()},
        "집행위 의견수렴": {f"{row['id']} {row['title']}": "; ".join(f"{item['stage']}/{item['feedback']}/{item['start'][:10]}~{item['end'][:10]}" for item in row.get("statuses", []))
                      for row in entries("ec-hys")},
        "법령 데이터베이스의 연관 문서": {row["celex"]: f"{row.get('date', '')} {row.get('title', '')[:120]}" for row in entries("eur-lex-related")},
        "법원 사건 문서": dict(read_json(f"{ARCHIVE}report/eur-lex-related.json", {}).get("result", {}).get("cases", {})),
        "집행위 보도자료": {row["reference"]: f"{row['date']} {row['title'][:120]}" for row in entries("ec-press")},
        "영국 법령": {row["number"]: row["title"] for row in entries("uk-legislation")},
        "미국 연방관보": {row["number"]: f"{row['date']} {row['title'][:120]}" for row in entries("us-fedreg")},
    }


def changes(before, now):
    """(기록, 열쇠, 전 값, 지금 값)의 목록. 새로 생긴 것은 전 값이 None, 사라진 것은 지금 값이 None이다."""
    found = []
    for group, rows in now.items():
        old = before.get(group, {})
        if not rows and old:  # 기록을 통째로 읽지 못한 날은 '모두 사라짐'으로 보지 않는다
            found.append({"group": group, "key": "(기록 전체)", "before": f"{len(old)}건", "now": None})
            continue
        for key, value in rows.items():
            if key not in old:
                found.append({"group": group, "key": key, "before": None, "now": value})
            elif old[key] != value:
                found.append({"group": group, "key": key, "before": old[key], "now": value})
        found += [{"group": group, "key": key, "before": old[key], "now": None} for key in old if key not in rows]
    return found


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("--accept", action="store_true")
    args = parser.parse_args(argv)
    now = snapshot()
    seen = read_json(SEEN, None)
    if args.accept or seen is None:
        write_json(SEEN, {"acceptedAt": stamp(), "seen": now})
        print(json.dumps({"accepted": True, "groups": {group: len(rows) for group, rows in now.items()}}, ensure_ascii=False))
        return 0
    found = changes(seen.get("seen", {}), now)
    print(json.dumps({"since": seen.get("acceptedAt", ""), "count": len(found), "changes": found}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
