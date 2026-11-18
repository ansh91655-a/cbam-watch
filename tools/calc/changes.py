"""인증서 비용 추정의 품목 자료(data/calc-goods.json)가 법령의 표가 바뀌어 달라졌을 때, 무엇이 얼마나 달라졌는지 품목마다 견준다.

법령의 표를 다시 받아 `python -m tools.calc.build`로 자료를 다시 만든 뒤에 돌린다. 앞의 자료는 git에 올라가 있는 것(또는 따로 둔 파일)이다.
견주는 것(품목 코드마다)
- 기본값: 그 품목이 쓰는 기본값 행(행이 다른 것으로 바뀌었는지)과 그 행의 직접배출량, 간접배출량, 총배출량, 생산경로, 값이 온 표(대한민국 표인지 '그 밖의 나라와 영역' 표인지)
- CBAM 벤치마크: A열과 B열의 값(생산경로와 연도 구간마다), 기본값으로 신고할 때 고르는 벤치마크
- 품목이 새로 생겼거나 없어진 것
만드는 것: 사람이 읽는 요약(화면에 찍는다)과, --json을 주면 달라진 것의 목록(사이트에 '바뀐 값'을 실을 때의 자료).

쓰는 법: python -m tools.calc.changes [--from <git의 판 또는 파일>] [--to <파일>] [--json <쓸 파일>]
         --from을 주지 않으면 HEAD의 자료, --to를 주지 않으면 이 저장소의 data/calc-goods.json과 견준다(어느 폴더에서 돌려도 같다).
         달라진 것이 없으면 0, 있으면 1로 끝난다. 자료를 읽지 못했거나 자료의 꼴이 달라 견주지 못했으면 2로 끝난다.
"""
import itertools
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]   # 저장소의 맨 위
TARGET = "data/calc-goods.json"
SHAPE = (KeyError, IndexError, TypeError, ValueError, AttributeError)   # 자료의 꼴이 생각한 것과 다를 때 나는 것들
PERIODS = {0: "", 1: "2026~2027년", 2: "2028~2030년"}   # 벤치마크 표의 연도 구간(0은 구간과 상관없는 값)
ORIGINS = {"kr": "대한민국 표", "other": "그 밖의 나라와 영역 표"}
FIELDS = (("direct", "기본값(직접배출량)"), ("indirect", "기본값(간접배출량)"), ("total", "기본값(총배출량)"))


def load(place):
    """파일이면 그 파일, 아니면 git의 그 판에 올라가 있는 자료. 읽지 못하면 None.
    '-'로 시작하는 이름은 받지 않는다(git이 판의 이름이 아니라 선택 사항으로 읽는다)."""
    place = str(place)
    if not place or place.startswith("-"):
        return None
    path = pathlib.Path(place)
    try:
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8"))
        done = subprocess.run(["git", "show", f"{place}:{TARGET}"], capture_output=True, text=True, check=False, cwd=ROOT)
        return json.loads(done.stdout) if done.returncode == 0 else None
    except (OSError, ValueError):
        return None


def _variants(rows):
    """벤치마크의 값들: {(생산경로, 연도 구간): 값}"""
    return {(route, period): value for value, route, period in rows}


def _defaults(good, rows):
    """그 품목이 쓰는 기본값 행들: {생산경로: {"shown", "direct", "indirect", "total", "origin", "benchmark"}}. shown은 그 행의 품목 코드(행이 무엇인지)다."""
    found = {}
    for choice in good.get("defaults", []):
        row = rows[choice["row"]]
        found[choice.get("route") or ""] = {"shown": row.get("shown", ""), "direct": row.get("direct"), "indirect": row.get("indirect"), "total": row.get("total"),
                                            "origin": row.get("origin", ""), "benchmark": list(choice.get("benchmark", []))}
    return found


def _by_route(pair):
    """생산경로와 연도 구간의 차례(빈 것이 섞여 있어도 견줄 수 있게)"""
    return (str(pair[0] or ""), pair[1] or 0)


def _line(what, before, after, route="", period=0):
    return {"what": what, "route": route, "period": PERIODS.get(period, str(period)), "before": before, "after": after}


def good_changes(old, new, old_rows, new_rows):
    """품목 하나의 달라진 것 목록. 달라진 것이 없으면 빈 목록."""
    found = []
    was, now = _defaults(old, old_rows), _defaults(new, new_rows)
    for route in sorted(set(was) | set(now)):
        if route not in was or route not in now:
            found.append(_line("기본값 행의 생산경로", "있음" if route in was else "없음", "있음" if route in now else "없음", route))
            continue
        if was[route]["shown"] != now[route]["shown"]:   # 같은 품목이 다른 행의 값을 쓰게 된 것(아래의 값이 달라진 까닭이 된다)
            found.append(_line("기본값 행", was[route]["shown"], now[route]["shown"], route))
        for name, label in FIELDS:
            if was[route][name] != now[route][name]:
                found.append(_line(label, was[route][name], now[route][name], route))
        if was[route]["origin"] != now[route]["origin"]:
            found.append(_line("기본값이 온 표", ORIGINS.get(was[route]["origin"], was[route]["origin"]), ORIGINS.get(now[route]["origin"], now[route]["origin"]), route))
        for at, (before, after) in enumerate(itertools.zip_longest(was[route]["benchmark"], now[route]["benchmark"]), 1):   # 한쪽에만 있는 구간도 본다
            if before != after:
                found.append(_line("기본값으로 신고할 때의 벤치마크", before, after, route, at))
    for column, label in (("a", "CBAM 벤치마크 A열"), ("b", "CBAM 벤치마크 B열")):
        before, after = _variants(old.get(column, [])), _variants(new.get(column, []))
        for route, period in sorted(set(before) | set(after), key=_by_route):
            if before.get((route, period)) != after.get((route, period)):
                found.append(_line(label, before.get((route, period)), after.get((route, period)), route, period))
    return found


def diff(old, new):
    """두 자료를 견준 것: {"goods": [{code, shown, text, sector, kind, changes}], "summary": {…}}.

    kind는 "added"(새 품목), "removed"(없어진 품목), "changed"(값이 달라진 품목)이다. 품목의 차례는 새 자료의 차례를 따르고, 없어진 품목은 끝에 둔다.
    """
    before = {good["code"]: good for good in old.get("goods", [])}
    after = {good["code"]: good for good in new.get("goods", [])}
    goods = []
    for code, good in after.items():
        head = {"code": code, "shown": good.get("shown", code), "text": good.get("text", ""), "sector": good.get("sector", "")}
        if code not in before:
            goods.append({**head, "kind": "added", "changes": []})
            continue
        changes = good_changes(before[code], good, old.get("rows", []), new.get("rows", []))
        if changes:
            goods.append({**head, "kind": "changed", "changes": changes})
    goods += [{"code": code, "shown": good.get("shown", code), "text": good.get("text", ""), "sector": good.get("sector", ""), "kind": "removed", "changes": []}
              for code, good in before.items() if code not in after]
    by_kind = {kind: sum(1 for good in goods if good["kind"] == kind) for kind in ("added", "removed", "changed")}
    by_what, by_sector = {}, {}
    for good in goods:
        by_sector[good["sector"]] = by_sector.get(good["sector"], 0) + 1
        for what in {change["what"] for change in good["changes"]}:
            by_what[what] = by_what.get(what, 0) + 1
    return {"goods": goods, "summary": {"before": len(before), "after": len(after), **by_kind, "byWhat": by_what, "bySector": by_sector}}


def _number(value):
    return "없음" if value is None else str(value)


def report(found, limit=40):
    """사람이 읽는 요약의 줄들."""
    summary = found["summary"]
    lines = [f"품목 {summary['before']}개 → {summary['after']}개: 값이 달라진 품목 {summary['changed']}개, 새 품목 {summary['added']}개, 없어진 품목 {summary['removed']}개"]
    if summary["byWhat"]:
        lines.append("달라진 것(품목 수): " + ", ".join(f"{what} {count}" for what, count in sorted(summary["byWhat"].items(), key=lambda pair: -pair[1])))
    if summary["bySector"]:
        lines.append("부문별(품목 수): " + ", ".join(f"{sector or '?'} {count}" for sector, count in sorted(summary["bySector"].items(), key=lambda pair: -pair[1])))
    for good in found["goods"][:limit]:
        if good["kind"] != "changed":
            lines.append(f"- {good['shown']} {good['text'][:50]}: {'새 품목' if good['kind'] == 'added' else '없어진 품목'}")
            continue
        parts = [f"{change['what']}{'(' + change['route'] + ')' if change['route'] else ''}{' ' + change['period'] if change['period'] else ''} {_number(change['before'])} → {_number(change['after'])}"
                 for change in good["changes"]]
        lines.append(f"- {good['shown']} {good['text'][:50]}: " + "; ".join(parts))
    if len(found["goods"]) > limit:
        lines.append(f"… 그 밖에 {len(found['goods']) - limit}개(모두 보려면 --json으로 받는다)")
    return lines


def main(argv):
    options = {"--from": "HEAD", "--to": TARGET, "--json": ""}
    rest = list(argv)
    while rest:
        name = rest.pop(0)
        if name not in options or not rest:
            print(__doc__.strip().split("쓰는 법:")[1].strip())
            return 2
        options[name] = rest.pop(0)
    to = options["--to"] if options["--to"] != TARGET else str(ROOT / TARGET)
    old, new = load(options["--from"]), load(to)
    if not isinstance(old, dict) or not isinstance(new, dict):
        print(f"자료를 읽지 못함: {options['--from'] if not isinstance(old, dict) else options['--to']}")
        return 2
    try:
        found = diff(old, new)
        lines = report(found)
    except SHAPE as error:   # 달라진 것이 있을 때의 1과 섞이지 않게 따로 끝낸다
        print(f"자료의 꼴이 달라 견주지 못함: {type(error).__name__}: {error}")
        return 2
    print("\n".join(lines))
    if options["--json"]:
        pathlib.Path(options["--json"]).write_text(json.dumps({"from": options["--from"], "to": options["--to"], **found}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return 1 if found["goods"] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
