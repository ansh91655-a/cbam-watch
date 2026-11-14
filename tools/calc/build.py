"""인증서 비용 추정에 쓰는 품목 자료(data/calc-goods.json)를 받아 둔 법령의 표에서 만든다.

벤치마크 표의 품목(CN 8자리)마다 대한민국의 기본값 행을 짝짓고, 기본값으로 신고할 때 쓰는 벤치마크를 법령의 규칙대로 고른다.
- 기본값 행은 코드가 가장 길게 맞는 것을 쓴다(4, 6, 8자리는 앞자리가 같은 것, 10자리 TARIC 코드는 앞 8자리가 같은 것).
  TARIC 코드로 갈린 품목(백색·회색 클링커 등)은 행이 둘이라 고를 것이 둘이 된다.
- 대한민국 표에 값이 없으면('-') '그 밖의 나라와 영역' 표의 같은 행을 쓴다(부속서 I의 규칙). 어느 표의 값인지 origin에 적는다.
- 기본값으로 신고할 때의 벤치마크는 B열에서, 쓰는 기본값 행에 적힌 생산경로의 값을 고른다(부속서 5.1).
  합금강처럼 같은 코드에 합금 등급이 여럿이면(저합금강 F·G·H와 고합금강 J) 그 생산 연도의 값 가운데 큰 것을 쓴다(부속서 5.1).
  품목의 벤치마크에 경로 표시가 없으면 경로와 상관없는 값이다(기본값 이행규정 부속서 I의 규칙).
- 법령이 정하지 않은 경우(기본값 행의 경로가 벤치마크의 경로와 맞지 않는 것, 합금강인데 경로가 F가 아닌 것)를 만나면
  어림해서 넘기지 않고 멈춘다. 그때는 사람이 법령을 다시 읽고 규칙을 정해야 한다.

만들기: python -m tools.calc.build          (data/calc-goods.json을 고쳐 쓴다)
견주기: python -m tools.calc.build --check  (받아 둔 표로 다시 만든 것과 다르면 0이 아닌 값으로 끝난다)
"""
import json
import pathlib
import sys

from tools.calc import source
from tools.calc.source import Unreadable
from tools.common.jsonio import read_json

TARGET = "data/calc-goods.json"
PERIODS = (1, 2)       # 벤치마크 표의 (1) 2026~27년, (2) 2028~30년
ALLOY_LOW = ("F", "G", "H")
ALLOY_HIGH = "J"
ABOUT = "받아 둔 법령의 표에서 프로그램(tools.calc.build)이 만든 자료입니다. 손으로 고치지 않습니다."


def matching(code, rows):
    """품목 코드에 맞는 기본값 행의 자리들. 코드가 가장 길게 맞는 행만 남긴다('아래를 보라'고만 적힌 행은 건너뛴다)."""
    hits = [index for index, row in enumerate(rows) if row["state"] != "below"
            and (code.startswith(row["code"]) if len(row["code"]) <= 8 else row["code"][:8] == code)]
    longest = max((len(rows[index]["code"]) for index in hits), default=0)
    return [index for index in hits if len(rows[index]["code"]) == longest]


def value_at(variants, route, period):
    """경로와 연도 구간에 맞는 값. 표시가 없는 값 하나뿐이면 그 값이다. 없으면 None."""
    for want_route, want_period in ((route, period), (route, 0), ("", period), ("", 0)):
        for one in variants:
            if one["route"] == want_route and one["period"] == want_period:
                return one["value"]
    return None


def default_benchmark(good, routes):
    """(고른 경로, [2026~27년 값, 2028~30년 값]). 기본값으로 신고할 때 쓰는 B열의 값이다."""
    have = sorted({one["route"] for one in good["b"] if one["route"]})
    if not have:
        route = ""
    else:
        shared = [route for route in routes if route in have]
        if len(shared) != 1:
            raise Unreadable(f"{good['shown']}: 기본값 행의 경로 {routes or '없음'}가 벤치마크의 경로 {have}와 하나로 맞지 않음")
        route = shared[0]
    values = []
    for period in PERIODS:
        value = value_at(good["b"], route, period)
        if value is None:
            raise Unreadable(f"{good['shown']}: 경로 {route or '없음'}, 연도 구간 {period}의 B열 값이 없음")
        if ALLOY_HIGH in have:
            if route != "F":
                raise Unreadable(f"{good['shown']}: 합금강인데 기본값 행의 경로가 {route}임. 합금 등급 가운데 큰 값을 고르는 규칙을 다시 확인해야 함")
            value = max(value, value_at(good["b"], ALLOY_HIGH, period))
        values.append(value)
    return route, values


def _compact(variants):
    return [[one["value"], one["route"], one["period"]] for one in variants]


def build():
    """data/calc-goods.json에 쓸 내용을 만들어 돌려준다. 표가 기대와 다르면 Unreadable을 던진다."""
    book, _ = source.benchmarks()
    tables = source.defaults()
    korea, other = tables["korea"]["rows"], tables["other"]["rows"]
    used, rows, goods = {}, [], []

    def row_number(index):
        """쓰는 기본값 행을 rows에 한 번만 싣고 그 자리를 돌려준다."""
        if index not in used:
            origin, row = ("kr", korea[index]) if korea[index]["state"] == "value" else ("other", other[index])
            if row["state"] != "value":
                raise Unreadable(f"{korea[index]['shown']}: 대한민국 표와 그 밖의 나라 표 어디에도 값이 없음")
            used[index] = len(rows)
            rows.append({"shown": row["shown"], "text": row["text"], "origin": origin, "direct": row["direct"],
                         "indirect": row["indirect"], "total": row["total"], "routes": row["routes"]})
        return used[index]

    for good in book["rows"]:
        hits = matching(good["code"], korea)
        if not hits:
            raise Unreadable(f"{good['shown']}: 맞는 기본값 행이 없음")
        choices = []
        for index in hits:
            number = row_number(index)
            route, values = default_benchmark(good, rows[number]["routes"])
            choices.append({"row": number, "route": route, "benchmark": values})
        goods.append({"code": good["code"], "shown": good["shown"], "text": good["text"], "sector": good["sector"],
                      "a": _compact(good["a"]), "b": _compact(good["b"]), "defaults": choices})
    return {
        "about": ABOUT,
        "builtFrom": {
            "benchmarks": {"path": str(source.BENCHMARKS), "table": book["table"], "goods": len(goods)},
            "defaults": {"path": str(source.DEFAULTS), "korea": {"caption": tables["korea"]["caption"], "table": tables["korea"]["table"]},
                         "other": {"caption": tables["other"]["caption"], "table": tables["other"]["table"]}, "rows": len(rows)},
        },
        "rows": rows,
        "goods": goods,
    }


def dump(body):
    """파일에 쓸 글. 행과 품목을 한 줄에 하나씩 적어, 법령의 표가 바뀌었을 때 무엇이 달라졌는지 한눈에 보이게 한다."""
    def line(value):
        return json.dumps(value, ensure_ascii=False, separators=(", ", ": "))

    def block(name, items, last=False):
        return [f' "{name}": ['] + [f"  {line(item)}{',' if index < len(items) - 1 else ''}" for index, item in enumerate(items)] + [" ]" + ("" if last else ",")]

    lines = ["{", f' "about": {line(body["about"])},', f' "builtFrom": {line(body["builtFrom"])},']
    lines += block("rows", body["rows"]) + block("goods", body["goods"], last=True) + ["}"]
    return "\n".join(lines) + "\n"


def main(argv):
    try:
        body = build()
    except Unreadable as problem:
        print(f"품목 자료를 만들지 못함: {problem}")
        return 1
    if "--check" in argv:
        same = read_json(TARGET, None) == body
        print("품목 자료가 받아 둔 표와 같음" if same else f"품목 자료({TARGET})가 받아 둔 표로 다시 만든 것과 다름: python -m tools.calc.build")
        return 0 if same else 1
    pathlib.Path(TARGET).write_text(dump(body), encoding="utf-8")
    other = sum(1 for row in body["rows"] if row["origin"] == "other")
    print(f"{TARGET}: 품목 {len(body['goods'])}개, 기본값 행 {len(body['rows'])}개(그 밖의 나라 표의 값 {other}개)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
