"""품목 코드 조회 자료(data/cn.json)를 법령 원문에서 만든다.

쓰는 법: python -m tools.cn.build
읽는 것: collected/archive/pages/eu-fulltext/cbam-consolidated.txt(CBAM 규정 통합본), downstream-commission-DOC_2.txt(확대 개정안의 부속서),
        downstream-council.txt(이사회 일반적 접근의 본문: 집행위 목록에 더할 코드와 뺄 코드의 목록).
원문의 꼴이 바뀌어 품목을 제대로 읽지 못하면(아래 확인에 걸리면) 자료를 쓰지 않고 1로 끝난다.
새 통합본이 나왔을 때 본문을 다시 받아 이 프로그램을 돌리는 일은 tools.cn.refresh가 한다(날마다의 수집이 돌린다).
"""
import sys

from tools.cn import annex, versions
from tools.common.jsonio import read_json, today, write_json

FOLDER = "collected/archive/pages/eu-fulltext/"
OUT = "data/cn.json"
INDEX = "collected/archive/eu-fulltext.json"
ENACTED_SHARE = 0.8  # 개정안의 코드 가운데 이만큼이 지금의 목록에 있으면 개정안이 법이 된 것으로 본다
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


def council_lists(lines):
    """이사회 문서의 부속서 I에서 (더할 코드의 목록, 뺄 코드의 목록)을 읽는다. 목록의 머리말(NOTE 1, NOTE 2)을 찾지 못하면 빈 목록."""
    part = annex.between(lines, "ANNEX I", "ANNEX II")
    first = next((index for index, line in enumerate(part) if "NOTE 1:" in line and "integrated into the Annex I" in line), None)
    second = next((index for index, line in enumerate(part) if "NOTE 2:" in line and "deleted from Annex I" in line), None)
    if first is None or second is None or second < first:
        return [], []
    return annex.code_list(part[first + 1:second]), annex.code_list(part[second + 1:])


def council_problems(proposed, added, removed):
    """이사회 목록을 제대로 읽었는지: 더한 코드는 집행위 목록에 없던 것이어야 하고, 뺀 코드는 집행위 목록에 있던 것이어야 한다."""
    listed = [code for entry in proposed for code in entry["codes"]]
    found = []
    if len(added) < 50 or any(not entry["text"] for entry in added):
        found.append("이사회가 더한 코드의 목록을 제대로 읽지 못함")
    if any(code.startswith(have) for entry in added for code in entry["codes"] for have in listed):
        found.append("이사회가 더한 코드 가운데 집행위 목록에 이미 있는 것이 있음")
    if not removed or any(code not in listed for entry in removed for code in entry["codes"]):
        found.append("이사회가 뺀 코드 가운데 집행위 목록에 없는 것이 있음")
    return found


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


def enacted(current, proposed):
    """개정안의 품목이 이미 통합본에 들어와 있는가.

    지금의 목록에 개정안만의 부문(복합 금속 제품)이 있거나, 개정안의 코드 대부분이 지금의 목록에 있으면 그렇다고 본다.
    """
    if not proposed:
        return False
    if any(entry["sector"] == "combined" for entry in current):
        return True
    have = {code for entry in current for code in entry["codes"]}
    wanted = [code for entry in proposed for code in entry["codes"]]
    return bool(wanted) and sum(1 for code in wanted if code in have) / len(wanted) >= ENACTED_SHARE


def assemble(law, draft, council, celex):
    """원문의 줄 목록에서 자료를 만든다. (자료, 문제의 목록)을 돌려준다. 문제가 있으면 자료는 None이다.

    law: CBAM 규정 통합본, draft: 확대 개정안의 부속서, council: 이사회 일반적 접근의 본문, celex: 그 통합본의 번호.
    """
    current = annex.tables(annex.between(law, "ANNEX I", "ANNEX II"))
    direct = annex.tables(annex.between(law, "ANNEX II", "ANNEX III"))
    proposed = annex.tables(annex.between(draft, "ANNEX I", "ANNEX II"))
    added, removed = council_lists(council)
    found = problems(current, direct, proposed)
    done = not found and enacted(current, proposed)
    if not done:
        found += council_problems(proposed, added, removed)
    if found:
        return None, found
    direct_codes = {(entry["sector"], tuple(entry["codes"])) for entry in direct}
    for entry in current:  # 부속서 II에 있는 품목은 직접배출만 본다
        entry["directOnly"] = (entry["sector"], tuple(entry["codes"])) in direct_codes
    data = {
        "asOf": today(),
        "law": versions.law_meta(celex, address_of(law)),
        "proposal": {"name": "하류제품 확대 개정안의 부속서(집행위 제안 COM(2025) 989)", "celex": "52025PC0989",
                     "url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:52025PC0989", "fetched": address_of(draft)},
        "council": {"name": "EU 이사회 일반적 접근의 부속서(이사회 문서 10423/26, 2026년 6월 12일)", "url": address_of(council),
                    "added": [] if done else added, "removed": [] if done else removed},
        # 개정안이 통합본에 들어온 뒤에는 '개정안에는 들어 있습니다' 같은 안내를 하지 않도록 개정안의 목록을 비운다.
        "proposalEnacted": done,
        "current": current, "proposed": [] if done else proposed,
    }
    return data, []


def summary(data):
    current, proposed, council = data["current"], data["proposed"], data["council"]
    return (f"부속서 I {len(current)}줄(제외 {sum(len(entry['except']) for entry in current)}줄), 직접배출만 보는 품목 {sum(1 for entry in current if entry['directOnly'])}줄, "
            f"개정안 {len(proposed)}줄, 이사회가 더한 코드 {len(council['added'])}개·뺀 코드 {len(council['removed'])}개"
            + (", 개정안은 통합본에 들어온 것으로 봄" if data.get("proposalEnacted") else ""))


def stored_celex():
    """받아 둔 통합본의 번호. 받아 둔 기록에 없으면 지금의 자료에 적힌 번호, 그것도 없으면 처음에 쓴 판."""
    for row in read_json(INDEX, {}).get("entries", []):
        if row.get("name") == "cbam-consolidated" and row.get("code"):
            return str(row["code"])
    return str((read_json(OUT, {}).get("law") or {}).get("celex", "")) or versions.FIRST


def main():
    data, found = assemble(read_lines("cbam-consolidated.txt"), read_lines("downstream-commission-DOC_2.txt"), read_lines("downstream-council.txt"), stored_celex())
    if found:
        print("\n".join(found))
        return 1
    write_json(OUT, data)
    print(summary(data))
    return 0


if __name__ == "__main__":
    sys.exit(main())
