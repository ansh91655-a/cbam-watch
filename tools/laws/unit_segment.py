"""꼬리표로 읽은 단위(tools.pdfko.units)에서 조각을 만든다. guide_segment.parts와 같은 꼴에 문단의 꼴("shapes")이 더 붙는다.

제목은 PDF에 제목으로 적힌 것(H1–H6)만 쓴다. 번호가 앞 제목의 번호에 이어지는 것은 절(section), "ANNEX A" 꼴은 부속서(appendix)가 되고,
번호가 없거나 이어지지 않는 제목은 그 자리의 문단으로 두되 꼴을 "h"로 적는다.
문단의 꼴: p(문단), h2(작은 제목과 그 단), li1(목록 항목과 들여쓴 단), th:표:줄:칸 / td:표:줄:칸(표의 칸. 칸 안의 목록 항목은 뒤에 ":li1"처럼, 합쳐진 칸은 그 뒤에 ":s칸수x줄수"로 붙는다),
caption(그림·표의 제목), note(각주), figure(그림 안의 이름표), formula(수식).
각주는 그 번호가 나온 조각의 끝에 "[3] …"으로 싣는다(guide_segment와 같다).
"""

from tools.laws import guide_segment

NUMBERED, ANNEX = guide_segment.NUMBERED, guide_segment.ANNEX


def _heading(unit, previous):
    """제목 단위가 새 조각을 여는가: (종류, 열쇠, 이름표, 제목, 단, 번호) 또는 None."""
    text = unit["text"]
    hit = NUMBERED.match(text)
    if hit:
        number = guide_segment._number(hit.group(1))
        if guide_segment.follows(previous, number) and hit.group(3).strip():
            return "section", "sec-" + "-".join(str(part) for part in number), guide_segment._dotted(number), hit.group(3).strip(), len(number), number
    hit = ANNEX.match(text)
    if hit and len(text) <= guide_segment.TITLE_MAX:
        letter = hit.group(2)
        return "appendix", "annex-" + letter.lower(), f"Annex {letter}", hit.group(3).strip(), 1, None
    return None


def _shape(unit):
    kind = unit["kind"]
    inner = {"h": f"h{unit.get('level', 1)}", "li": f"li{unit.get('depth', 1)}", "cell": ""}.get(kind, kind)
    if "table" in unit and kind != "caption":   # 표의 칸과 그 안에 든 것(목록 항목 따위). 칸 안의 꼴은 뒤에 붙인다
        cell = f"{'th' if unit.get('head') else 'td'}:{unit['table']}:{unit['row']}:{unit['column']}"
        if unit.get("cols", 1) > 1 or unit.get("rows", 1) > 1:      # 합쳐진 칸: 칸 수 x 줄 수
            return f"{cell}:{inner}:s{unit.get('cols', 1)}x{unit.get('rows', 1)}"
        return f"{cell}:{inner}" if inner else cell
    return inner or "p"


def _block(unit):
    label, text = unit.get("label", ""), unit["text"]
    if unit["kind"] == "note":
        return f"[{label}] {text}" if label else text
    if unit["kind"] == "li" and label and not text.startswith(label):
        return f"{label} {text}"
    return text


def _squash(text):
    return "".join(char for char in text.lower() if char.isalnum())


def _borrowed(units, old):
    """제목 꼬리표가 없는 문서: 글에서 찾아 둔 제목(old 조각들)과 글이 같은 단위를 제목으로 삼는다. {단위의 차례: 옛 조각}."""
    heads = [part for part in old if part["kind"] in ("section", "appendix") and part["title"]]
    found, at = {}, 0
    for index, unit in enumerate(units):
        if unit["kind"] in ("figure", "formula", "cell", "note", "toc") or len(unit["text"]) > guide_segment.TITLE_MAX + 20:
            continue
        text = _squash(_block(unit))
        for ahead in range(at, min(at + 3, len(heads))):
            part = heads[ahead]
            if text in (_squash(part["label"] + part["title"]), _squash(part["title"])):
                found[index] = part
                at = ahead + 1
                break
    return found


def parts(units, outline="auto", fallback=None):
    """단위들을 조각의 목록으로. 조각은 {"id", "kind", "label", "title", "level", "blocks", "shapes", "units", "page"}다.

    "units"는 문단마다 그 단위가 단위 목록의 몇 번째인지(국문 PDF를 만들 때 자리를 찾는 데 쓴다), "head"는 조각의 제목이 된 단위의 차례다.
    outline이 none이면 제목으로 나누지 않고 글 전체를 조각 하나로 둔다.
    fallback은 글에서 나눈 옛 조각을 돌려주는 함수다. 제목 꼬리표로 절을 하나도 찾지 못한 문서에서 그 제목들을 빌린다.
    """
    whole = outline == "none"
    borrowed = {}
    if not whole and fallback and not any(_heading(unit, None) for unit in units if unit["kind"] == "h"):
        borrowed = _borrowed(units, fallback())
    first = guide_segment._part("section", guide_segment.BODY_ID, guide_segment.BODY_LABEL, "", 1) if whole else guide_segment._part("cover", "cover", "", "", 0)
    found, seen, previous = [first], {first["id"]}, None
    first.update({"blocks": [], "shapes": [], "units": [], "notes": []})
    for index, unit in enumerate(units):
        if unit["kind"] == "toc":       # 차례의 줄은 싣지 않는다(국문 PDF를 만들 때만 쓴다)
            continue
        if index in borrowed:
            old = borrowed[index]
            heading = (old["kind"], old["id"], old["label"], old["title"], old["level"], None)
        else:
            heading = _heading(unit, previous) if unit["kind"] == "h" and not whole else None
        if heading:
            kind, key, label, title, level, number = heading
            previous = number or previous
            base, count = key, 2
            while key in seen:
                key, count = f"{base}-{count}", count + 1
            seen.add(key)
            part = guide_segment._part(kind, key, label, title, level)
            part.update({"blocks": [], "shapes": [], "units": [], "notes": [], "head": index})
            found.append(part)
            continue
        home = found[-1]
        if unit["kind"] == "note":
            home["notes"].append((_block(unit), index))
            continue
        home["blocks"].append(_block(unit))
        home["shapes"].append(_shape(unit))
        home["units"].append(index)
    for part in found:
        for text, index in part.pop("notes"):
            part["blocks"].append(text)
            part["shapes"].append("note")
            part["units"].append(index)
        del part["lines"], part["pages"]
        first = part.get("head", part["units"][0] if part["units"] else None)   # 차례의 줄은 units에 없으므로 차례 쪽을 가리키지 않는다
        if first is not None:
            part["page"] = units[first]["page"]     # 조각이 시작하는 쪽(PDF로 보는 화면에서 그 쪽을 연다)
    return [part for part in found if part["blocks"] or part["title"]]
