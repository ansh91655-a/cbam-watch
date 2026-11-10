"""법령 부속서의 품목 표를 읽는다.

표는 줄마다 '코드 – 품목 이름', 그 아래에 'Except:'와 제외 품목들, 마지막에 온실가스 이름이 오는 꼴이다.
코드 앞의 ex는 그 코드의 품목 가운데 일부만 든다는 뜻이다. 한 줄에 코드가 둘 이상 올 수 있다('7202 21 00, 7202 29 – …').
"""
import re

SECTORS = {"cement": "cement", "electricity": "electricity", "fertilisers": "fertilisers", "iron and steel": "steel",
           "aluminium": "aluminium", "chemicals": "chemicals", "combined metal products": "combined"}
GASES = {"carbon dioxide": "co2", "nitrous oxide": "n2o", "perfluorocarbons": "pfc"}
MARKS = re.compile(r"[►▼◄]\S*|^[‘’'\[\]\s]+|[‘’'\[\]\s]+$")
ENTRY = re.compile(r"^(?P<ex>ex\s*-?\s*)?(?P<codes>\d[\d ]*(?:,\s*\d[\d ]*)*?)\s*(?:–|-)\s*(?P<text>\D.*)$")
LOOSE = re.compile(r"^(?P<ex>ex\s*-?\s*)(?P<codes>\d{4}(?: \d{2}){0,2})\s+(?P<text>[A-Z].*)$")  # 줄표 없이 적힌 줄('ex 7204 Ferrous waste …')


def clean(line):
    """줄에서 개정 표시(►M1, ◄, ▼B)와 따옴표·대괄호를 떼어 낸다."""
    text = str(line)
    for _ in range(3):
        text = MARKS.sub("", text).strip()
    return " ".join(text.split())


def entry_of(line):
    """'코드 – 이름' 줄이면 {codes, shown, ex, text}를, 아니면 None을 돌려준다."""
    match = ENTRY.match(line) or LOOSE.match(line)
    if not match:
        return None
    shown = " ".join(match.group("codes").split())
    codes = [re.sub(r"\D", "", part) for part in shown.split(",")]
    if not all(2 <= len(code) <= 10 for code in codes):
        return None
    return {"codes": codes, "shown": ("ex " if match.group("ex") else "") + shown, "ex": bool(match.group("ex")), "text": match.group("text").strip()}


def gases_of(line):
    """온실가스 줄이면 ['co2', 'n2o'] 같은 목록을, 아니면 None을 돌려준다."""
    lowered = line.lower()
    if not lowered.startswith("carbon dioxide"):
        return None
    return [key for name, key in GASES.items() if name in lowered]


def tables(lines):
    """줄 목록에서 품목 표를 읽어 품목의 목록을 돌려준다. 품목마다 sector, codes, shown, ex, text, gases, except를 가진다."""
    sector, current, excepting, entries = None, None, False, []
    for raw in lines:
        line = clean(raw)
        if not line or line in ("CN code", "Greenhouse gas"):
            continue
        if line.lower() in SECTORS:
            sector, current, excepting = SECTORS[line.lower()], None, False
            continue
        if sector is None:
            continue
        gases = gases_of(line)
        if gases is not None:
            if current is not None:
                current["gases"] = gases
            current, excepting = None, False
            continue
        if line.lower().startswith("except"):
            excepting = True
            line = line.split(":", 1)[1].strip() if ":" in line else ""
            if not line:
                continue
        found = entry_of(line)
        if found is None:
            continue
        if excepting and current is not None:
            current["except"].append(found)
        else:
            current = {"sector": sector, **found, "gases": [], "except": []}
            entries.append(current)
            excepting = False
    return entries


def between(lines, start, end):
    """start로 시작하는 줄 다음부터 end로 시작하는 줄 앞까지를 돌려준다(개정 표시는 떼고 견준다). 없으면 빈 목록."""
    begin = next((index for index, line in enumerate(lines) if clean(line) == start), None)
    if begin is None:
        return []
    finish = next((index for index in range(begin + 1, len(lines)) if clean(lines[index]) == end), len(lines))
    return lines[begin + 1:finish]
