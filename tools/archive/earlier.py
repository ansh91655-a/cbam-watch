"""법령의 앞선 판을 받아 두고 남긴다. 규정 원문 화면의 '개정 대조'(tools.laws.revisions)가 지금의 글과 견주는 데 쓴다.

- 처음 채택된 글(관보에 실린 글): ADOPTED에 적은 법령을 EU 출판국 자료 창구에서 한 번 받아 둔다.
  관보의 글은 바뀌지 않으므로 이미 받아 둔 것은 다시 받지 않는다. 손으로 돌린다: 워크플로 '소급 수집'에서 mode = crawl, steps = eu-earlier.
- 통합본이 새 판으로 바뀔 때: 받아 둔 글을 새 글로 덮어쓰기 전에 keep()으로 옛 판을 여기에 옮겨 둔다(tools.cn.refresh와 tools.archive.fulltext가 부른다).
목록은 collected/archive/eu-earlier.json, 글은 collected/archive/pages/eu-earlier/<판의 번호>.txt 다. EU 법령은 출처를 밝히고 다시 쓸 수 있다.
"""
import pathlib

from tools.archive.store import ROOT, save_text
from tools.cn import versions
from tools.common.jsonio import read_json, stamp, write_json

INDEX = ROOT / "eu-earlier.json"
EURLEX = "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:{code}"
# (법령의 번호, 관보에 실린 날, 받은 글에 꼭 있어야 하는 말). 통합본으로 싣는 법령의 처음 글이다.
ADOPTED = [("32023R0956", "2023-05-16", "ANNEX I")]
NOTE = ("법령의 앞선 판. act는 법령의 번호, code는 그 판의 번호(처음 채택된 글은 법령의 번호 그대로, 통합본은 02023R0956-20251020 꼴), "
        "kind는 adopted(관보에 실린 처음 글)나 consolidated(통합본), date는 그 판의 기준일이다.")


def entries():
    """남겨 둔 판의 목록. 기준일이 이른 것부터."""
    found = (read_json(INDEX, {}) or {}).get("entries", [])
    return sorted(found, key=lambda row: (str(row.get("act", "")), str(row.get("date", ""))))


def _save(found):
    write_json(INDEX, {"source": "eu-earlier", "note": NOTE, "savedAt": stamp(), "entries": sorted(found, key=lambda row: (row["act"], row["date"]))})


def _add(row):
    found = [entry for entry in entries() if entry.get("code") != row["code"]]
    _save(found + [row])


def keep(act, code, text_path):
    """받아 둔 판(code)의 글을 앞선 판으로 남긴다. 이미 남긴 판이면 그대로 둔다. 남긴 글의 경로를 돌려준다(남길 글이 없으면 빈 글)."""
    known = next((entry for entry in entries() if entry.get("code") == code), None)
    if known and pathlib.Path(known.get("textPath", "")).is_file():
        return known["textPath"]
    source = pathlib.Path(text_path)
    if not code or not source.is_file():
        return ""
    lines = source.read_text(encoding="utf-8").splitlines()
    path = save_text(f"eu-earlier/{code}.txt", lines)
    _add({"act": act, "code": code, "kind": "consolidated" if "-" in code else "adopted", "date": versions.day_of(code),
          "url": EURLEX.format(code=code), "lines": len(lines), "textPath": path})
    return path


def crawl(fetch_parts=None):
    """처음 채택된 글 가운데 아직 받아 두지 않은 것을 받는다. fetch_parts는 시험에서 바꿔 끼운다(tools.archive.fulltext.celex_parts와 같은 꼴)."""
    if fetch_parts is None:
        from tools.archive import fulltext
        fetch_parts = fulltext.celex_parts
    have = {entry.get("code") for entry in entries() if pathlib.Path(entry.get("textPath", "")).is_file()}
    stored, failures = 0, []
    for code, day, must in ADOPTED:
        if code in have:
            continue
        try:
            parts, why = fetch_parts(code)
        except Exception as problem:
            parts, why = [], f"{type(problem).__name__}: {problem}"[:160]
        lines = [line for _, _, part in parts for line in part]
        if not why and not any(must in line for line in lines):
            why = f"받은 글에 '{must}'가 없음(다른 문서일 수 있음)"
        if why:
            failures.append(f"{code}: {why}")
            continue
        path = save_text(f"eu-earlier/{code}.txt", [f"[주소] {parts[0][1]}", ""] + lines)
        _add({"act": code, "code": code, "kind": "adopted", "date": day, "url": EURLEX.format(code=code), "lines": len(lines), "textPath": path})
        stored += 1
    return {"stored": stored, "kept": len(entries()), "failures": failures}
