"""품목 한 장 보기(#cn-<코드>)가 품목마다 잇는 곳을 만든다: 근거 조문과 해설서의 절.

- 무엇을 이을지는 sources/item-sheet.json이 정한다. 이름은 사이트의 자료에서 붙인다(손으로 적은 이름이 낡지 않게):
  근거 조문의 이름은 규정 원문의 목록(laws/index.json), 해설서의 절 이름은 사이트에 실은 해설서(handbook.json)에서 온다.
- when은 그 줄을 보여 줄 품목을 가린다. 없으면 모든 품목이다.
  direct    직접배출량만 넣는 품목(CBAM 규정 부속서 II)
  both      간접배출량도 넣는 품목
  priced    기본값과 CBAM 벤치마크의 표가 있는 품목(인증서 비용 추정의 자료에 있는 것)
  unpriced  그런 표가 없는 부문의 품목(전력)
- 가리키는 조각이나 절이 사이트에 없으면 문제로 돌려준다(사이트 만들기가 멈춘다).
- 만드는 것: data/sheet.json
  {"basis": [{"about", "act", "part", "label", "when"}], "read": [{"href", "chapter", "title", "when"}]}

쓰는 법: python -m tools.publish.item_sheet <사이트 폴더의 data>   (사이트 만들기가 부른다. 따로 돌리면 줄 수와 문제를 찍는다)
"""
import pathlib
import sys

from tools.common.jsonio import read_json, write_json
from tools.publish import crossrefs, handbook

SOURCE = "sources/item-sheet.json"
WHEN = ("", "direct", "both", "priced", "unpriced")


def _sections(book):
    """해설서의 절: {"장.절": (장의 제목, 절의 제목)}"""
    return {f"{chapter['id']}.{section['id']}": (chapter.get("title", ""), section.get("title", ""))
            for chapter in (book or {}).get("chapters", []) for section in chapter.get("sections", [])}


def problems(sheet, known, sections):
    """[(자리, 문제)]. known은 규정 원문의 문서와 조각(handbook.known_laws), sections는 해설서의 절(_sections)."""
    if not isinstance(sheet, dict) or not isinstance(sheet.get("basis"), list) or not isinstance(sheet.get("read"), list):
        return [("품목 한 장 보기", f"자료({SOURCE})를 읽지 못함")]
    found = []
    for at, row in enumerate(sheet["basis"], 1):
        where = f"근거 {at}"
        if not isinstance(row, dict) or not str(row.get("about", "")).strip():
            found.append((where, "about이 비어 있음"))
            continue
        if row.get("when", "") not in WHEN:
            found.append((where, f"모르는 when: {row.get('when')}"))
        if row.get("act") not in known["acts"]:
            found.append((where, f"규정 원문에 없는 문서: {row.get('act')}"))
        elif row.get("part") and row["part"] not in known["parts"][row["act"]]:
            found.append((where, f"규정 원문에 없는 조각: {row['act']}.{row['part']}"))
    for at, row in enumerate(sheet["read"], 1):
        where = f"해설서 {at}"
        if not isinstance(row, dict) or row.get("section") not in sections:
            found.append((where, f"해설서에 없는 절: {row.get('section') if isinstance(row, dict) else row}"))
        elif row.get("when", "") not in WHEN:
            found.append((where, f"모르는 when: {row.get('when')}"))
    if not sheet["basis"] or not sheet["read"]:
        found.append(("품목 한 장 보기", "근거나 해설서의 줄이 하나도 없음"))
    return found


def build(sheet, known, sections):
    """sheet.json의 내용."""
    basis = [{"about": row["about"], "act": row["act"], "part": row.get("part", ""), "label": crossrefs.label(known, row["act"], row.get("part", "")), "when": row.get("when", "")}
             for row in sheet["basis"]]
    read = [{"href": f"#handbook-{row['section']}", "chapter": sections[row["section"]][0], "title": sections[row["section"]][1], "when": row.get("when", "")}
            for row in sheet["read"]]
    return {"basis": basis, "read": read}


def write(data_out):
    """data/sheet.json을 쓰고 (줄 수, 문제)를 돌려준다. 문제가 있으면 쓰지 않는다. 규정 원문의 목록과 해설서가 먼저 만들어져 있어야 한다."""
    data_out = pathlib.Path(data_out)
    sheet = read_json(SOURCE, None)
    known = handbook.known_laws(read_json(data_out / "laws" / "index.json", None))
    sections = _sections(read_json(data_out / "handbook.json", None))
    found = problems(sheet, known, sections)
    if found:
        return 0, found
    body = build(sheet, known, sections)
    write_json(data_out / "sheet.json", body)
    return len(body["basis"]) + len(body["read"]), []


def main(argv):
    if len(argv) != 1:
        print(__doc__.strip().splitlines()[-1].strip())
        return 2
    count, found = write(argv[0])
    print(f"품목 한 장 보기: 잇는 곳 {count}줄, 문제 {len(found)}건")
    for where, problem in found:
        print(f"- {where}: {problem}")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
