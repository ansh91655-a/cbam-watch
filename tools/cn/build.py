"""품목 코드 조회 자료(data/cn.json)를 법령 원문에서 만든다.

쓰는 법: python -m tools.cn.build
읽는 것: collected/archive/pages/eu-fulltext/cbam-consolidated.txt(CBAM 규정 통합본), downstream-commission-DOC_2.txt(확대 개정안의 부속서).
원문의 꼴이 바뀌어 품목을 제대로 읽지 못하면(아래 확인에 걸리면) 자료를 쓰지 않고 1로 끝난다.
"""
import sys

from tools.cn import annex
from tools.common.jsonio import read_json, today, write_json

FOLDER = "collected/archive/pages/eu-fulltext/"
OUT = "data/cn.json"
# 꼭 읽혀야 하는 품목(부문, 코드). 하나라도 없으면 원문을 잘못 읽은 것이다.
ANCHORS = [("cement", "25231000"), ("electricity", "27160000"), ("fertilisers", "3102"), ("steel", "72"), ("steel", "7318"), ("aluminium", "7601"), ("chemicals", "28041000")]


def read_lines(name):
    try:
        with open(FOLDER + name, encoding="utf-8") as handle:
            return handle.read().split("\n")
    except OSError:
        return []


def address_of(lines):
    return lines[0].replace("[주소]", "").strip() if lines and lines[0].startswith("[주소]") else ""


def problems(current, direct, proposed):
    found = []
    have = {(entry["sector"], code) for entry in current for code in entry["codes"]}
    found += [f"부속서 I에서 {sector} {code}를 읽지 못함" for sector, code in ANCHORS if (sector, code) not in have]
    steel = next((entry for entry in current if entry["sector"] == "steel" and entry["codes"] == ["72"]), None)
    if steel is None or len(steel["except"]) < 10:
        found.append("부속서 I의 철강(72) 제외 목록을 읽지 못함")
    if any(not entry["gases"] for entry in current):
        found.append("부속서 I에 온실가스가 적히지 않은 품목이 있음")
    if not direct:
        found.append("부속서 II를 읽지 못함")
    if proposed and not any(entry["sector"] == "combined" for entry in proposed):
        found.append("확대 개정안의 부속서에서 복합 금속 제품 표를 읽지 못함")
    return found


def main():
    law = read_lines("cbam-consolidated.txt")
    current = annex.tables(annex.between(law, "ANNEX I", "ANNEX II"))
    direct = annex.tables(annex.between(law, "ANNEX II", "ANNEX III"))
    draft = read_lines("downstream-commission-DOC_2.txt")
    proposed = annex.tables(annex.between(draft, "ANNEX I", "ANNEX II"))
    found = problems(current, direct, proposed)
    if found:
        print("\n".join(found))
        return 1
    direct_codes = {(entry["sector"], tuple(entry["codes"])) for entry in direct}
    for entry in current:  # 부속서 II에 있는 품목은 직접배출만 본다
        entry["directOnly"] = (entry["sector"], tuple(entry["codes"])) in direct_codes
    index = {row.get("name"): row for row in read_json("collected/archive/eu-fulltext.json", {}).get("entries", [])}
    write_json(OUT, {
        "asOf": today(),
        "law": {"name": "규정 (EU) 2023/956 부속서 I·II(2025년 10월 20일 통합본)", "celex": "02023R0956-20251020",
                "url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:02023R0956-20251020", "fetched": address_of(law)},
        "proposal": {"name": "하류제품 확대 개정안의 부속서(집행위 제안 COM(2025) 989)", "celex": "52025PC0989",
                     "url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:52025PC0989", "fetched": address_of(draft)},
        "current": current, "proposed": proposed,
    })
    print(f"부속서 I {len(current)}줄(제외 {sum(len(entry['except']) for entry in current)}줄), 직접배출만 보는 품목 {sum(1 for entry in current if entry['directOnly'])}줄, 개정안 {len(proposed)}줄")
    return 0


if __name__ == "__main__":
    sys.exit(main())
