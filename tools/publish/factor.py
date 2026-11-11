"""CBAM 계수(무상할당을 줄여 가는 비율)의 현행 값과 개정안 값. 사이트의 그림과 비용 추정이 쓴다.

원본은 data/factor.json이다. 경로(paths)마다 해마다의 값(values)과 그 값이 적힌 법령 글(source.path)이 있다.
검사는 값 하나하나가 그 글에 실제로 적혀 있는지를 본다.
- 보통의 값은 글에 "97,5 % in 2026"처럼 적혀 있다(소수점은 쉼표나 마침표, 수와 % 사이는 붙거나 한 칸).
- 글이 다르게 적은 값(예: "15% from 2034 to 2037", "From 2034, no CBAM factor shall apply")은 stated에 그 대목을 적는다.
검사: python -m tools.publish.factor   (문제가 있으면 0이 아닌 값으로 끝난다)
"""
import pathlib
import re
import sys

from tools.common.jsonio import read_json

SOURCE = "data/factor.json"
ARCHIVE = pathlib.Path("collected/archive")
YEAR = re.compile(r"^20\d\d$")


def _number(value):
    """97.5 → 글에서 찾을 꼴(97[.,]5), 95 → 95."""
    text = f"{value:g}"
    return text.replace(".", "[.,]")


def path_problems(path):
    found = []
    where = f"경로 {path.get('key', '?')}"
    source = path.get("source") or {}
    if not path.get("name") or not str(source.get("url", "")).startswith("https://") or not source.get("text"):
        found.append((where, "이름이나 근거 자료의 이름·주소가 없음"))
    values = path.get("values") or {}
    if not values or any(not YEAR.match(str(year)) or not isinstance(value, (int, float)) or not 0 <= value <= 100 for year, value in values.items()):
        return found + [(where, "해마다의 값이 없거나 0~100 밖의 값이 있음")]
    years = sorted(int(year) for year in values)
    if years != list(range(years[0], years[-1] + 1)):
        found.append((where, "해가 이어져 있지 않음"))
    if any(values[str(later)] > values[str(earlier)] for earlier, later in zip(years, years[1:])):
        found.append((where, "값이 뒤로 가며 커짐(계수는 줄어들기만 한다)"))
    file = pathlib.Path(str(source.get("path", "")))
    if ARCHIVE not in file.parents or not file.exists():
        return found + [(where, f"근거 글이 없음: {file}")]
    text = " ".join(file.read_text(encoding="utf-8").split())
    stated = path.get("stated") or {}
    for year in years:
        value = values[str(year)]
        phrase = stated.get(str(year))
        if phrase:
            if phrase not in text:
                found.append((f"{where} {year}", f"근거 어긋남: 글에 없는 대목 '{phrase}'"))
            elif f"{value:g}" not in phrase and not (value == 0 and "no CBAM factor" in phrase):
                found.append((f"{where} {year}", f"근거 어긋남: 대목 '{phrase}'에 값 {value:g}이 없음"))
        elif not re.search(rf"(?<![\d.,]){_number(value)}\s?% in {year}\b", text):
            found.append((f"{where} {year}", f"근거 어긋남: 글에서 '{value:g} % in {year}'를 찾지 못함"))
    return found


def problems(body):
    """[(자리, 문제)] 목록. 자료가 없으면 한 줄로 알린다."""
    if not isinstance(body, dict) or not isinstance(body.get("paths"), list) or not body["paths"]:
        return [("CBAM 계수", "자료(data/factor.json)를 읽지 못함")]
    found = []
    keys = [path.get("key") for path in body["paths"]]
    if len(set(keys)) != len(keys) or not all(keys):
        found.append(("CBAM 계수", "경로의 열쇠가 없거나 겹침"))
    for path in body["paths"]:
        found += path_problems(path)
    return found


def public(body):
    """사이트에 실을 모양. 저장소 안의 파일 경로와 대조용 대목은 뺀다."""
    return {"asOf": body.get("asOf", ""), "title": body.get("title", ""), "about": body.get("about", ""),
            "paths": [{"key": path["key"], "name": path["name"], "note": path.get("note", ""),
                       "source": {"text": path["source"]["text"], "url": path["source"]["url"]},
                       "values": path["values"]} for path in body.get("paths", [])]}


def main():
    found = problems(read_json(SOURCE, None))
    for where, what in found:
        print(f"문제: {where}: {what}")
    print(f"CBAM 계수: 문제 {len(found)}건")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
