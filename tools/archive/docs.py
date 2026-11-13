"""CBAM 규정과 이어진 EU 문서(제안, 보고서, 의견, 결정, 정오표)의 앞부분을 받아 둔다.

어떤 문서를 받을지는 EU 법령 데이터베이스 조회 결과(collected/archive/eur-lex-related.json)에서 고른다.
CBAM 규정을 근거로 삼거나 고치는 문서는 모두 받고, CBAM 규정을 인용만 하는 문서는 아래 ALSO에 적은 것만 받는다.
문서의 글은 EU 출판국의 자료 창구에서 받으며, 앞부분만 남긴다(긴 보고서와 의견은 조금 더 남긴다).
법원의 문서(판결, 결정, 법무관 의견: 번호가 6으로 시작)는 결론이 끝에 있으므로 끝부분도 남긴다(주문: On those grounds, the Court hereby …).
앞부분만 받아 둔 법원 문서는 한 번 더 받아 끝부분을 채운다.
"""
import pathlib
import re
import time
import urllib.parse

from tools.archive.store import ROOT, SINCE, save_index, save_text
from tools.common.htmltext import decode, parse
from tools.common.jsonio import read_json
from tools.common.net import fetch, header

CELLAR = "http://publications.europa.eu/resource/celex/{celex}"
EURLEX = "https://eur-lex.europa.eu/legal-content/EN/ALL/?uri=CELEX:{celex}"
# 인용만 하는 문서 가운데 CBAM의 진행 상황을 아는 데 필요한 것
ALSO = ["52025PC0408", "32025D2468", "52025PC0574", "52026PC0616", "52026PC0619", "52026DC0596", "62024CC0519"]
# 이미 다른 도구가 받는 법령(tools/archive/eurlex.py)
ACTS = {"32025R0486", "32025R2083", "32025R2210", "32025R2546", "32025R2547", "32025R2548", "32025R2549", "32025R2550", "32025R2551",
        "32025R2619", "32025R2620", "32025R2621", "32026R1740"}
LONG = {"52025DC0783", "52026AA0013", "52025AE4390", "52025PC0990", "52025PC0989", "52026PC0616"}
# 모으기 시작한 날(SINCE)보다 앞서 나왔지만 지금도 진행 중인 일의 근거가 되는 문서(예: 계류 중인 소송의 공고)
OLDER = {"62023CN0512"}
HEAD_LINES, LONG_LINES, LINE_LIMIT = 120, 420, 700
TAIL_LINES = 40  # 법원 문서에서 남기는 끝부분의 줄 수
PROCEDURE = re.compile(r"\b(20\d\d)/(\d{4}) ?\((COD|CNS|NLE|APP)\)")
PAUSE = 2.0


def wanted(entries):
    """조회 결과에서 받을 문서를 고른다. 통합본(0으로 시작)과 회의록(C/로 시작), 부속 작업문서(SC)는 뺀다."""
    chosen = []
    for entry in entries:
        celex = entry.get("celex", "")
        # 정오표(번호에 괄호가 든 것)는 자료 창구가 이 주소로 내어 주지 않는다. 날짜와 제목은 조회 결과에 있다.
        too_old = (entry.get("date") or "9999") < SINCE and celex not in OLDER
        if celex in ACTS or celex.startswith(("0", "C/")) or "(" in celex or too_old:
            continue
        linked = any(not relation.split(":")[0].endswith("work_cites_work") for relation in entry.get("relations", []))
        if celex in ALSO or (linked and celex[5:7] != "SC"):
            chosen.append(entry)
    return chosen


def procedures_in(lines):
    found = []
    for line in lines[:80]:
        for match in PROCEDURE.finditer(line):
            reference = f"{match.group(1)}/{match.group(2)}({match.group(3)})"
            if reference not in found:
                found.append(reference)
    return found


def kept_lines(celex, lines):
    """남길 줄과, 끝부분까지 담았는지. 법원 문서가 길면 앞부분 뒤에 끝부분(주문, 결론)을 붙인다."""
    head = LONG_LINES if celex in LONG else HEAD_LINES
    court = celex.startswith("6")
    if not court or len(lines) <= head + TAIL_LINES:
        return [line[:LINE_LIMIT] for line in lines[:head + TAIL_LINES if court else head]], court
    skipped = len(lines) - head - TAIL_LINES
    return ([line[:LINE_LIMIT] for line in lines[:head]] + [f"[… 가운데 {skipped}줄은 싣지 않음. 아래는 문서의 끝부분 …]"]
            + [line[:LINE_LIMIT] for line in lines[-TAIL_LINES:]]), True


ACCEPT = {"Accept": "application/xhtml+xml, text/html;q=0.9", "Accept-Language": "eng"}


def lines_of(celex, notes):
    """문서의 글을 줄 목록으로 돌려준다. 받지 못하면 (빈 목록, 사유).

    한 문서에 파일이 여럿이면(본문과 부속서) 자료 창구가 고를 목록을 준다(300). 그때는 목록의 첫 파일(본문)을 받는다.
    정오표는 번호의 괄호를 풀어 쓴 주소로 한 번 더 묻는다.
    """
    addresses = [CELLAR.format(celex=celex)]
    if "(" in celex:
        addresses.append(CELLAR.format(celex=urllib.parse.quote(celex, safe="")))
    reason = ""
    for address in addresses:
        status, headers, body, error = fetch(address, timeout=240, retries=1, headers=ACCEPT)
        time.sleep(PAUSE)
        if status == 300 and body:
            links, _, _ = parse(decode(body, header(headers, "Content-Type")), address)
            choices = [url for url, _ in links if "/resource/cellar/" in url]
            choices.sort(key=lambda url: (not url.endswith("DOC_1"), url))
            notes.append(f"{celex}: 고를 파일 {len(choices)}개, 첫째 {choices[0] if choices else '없음'}")
            for choice in choices[:4]:
                status, headers, body, error = fetch(choice, timeout=240, retries=1, headers=ACCEPT)
                time.sleep(PAUSE)
                if status == 200 and body and b"<" in body[:400]:
                    break
        if status == 200 and body:
            _, lines, _ = parse(decode(body, header(headers, "Content-Type")), address)
            if len(lines) >= 5:
                return lines, ""
            reason = f"글이 거의 없음: {len(lines)}줄"
        else:
            reason = f"{status} {error[:60]}"
    return [], reason


def crawl(deadline=None):
    related = read_json(ROOT / "eur-lex-related.json", {}).get("entries", [])
    targets = wanted(related)
    entries, report = [], {"targets": len(targets), "stored": 0, "kept": 0, "failures": [], "notes": []}
    have = {entry["celex"]: entry for entry in read_json(ROOT / "eur-lex-docs.json", {}).get("entries", [])}
    for target in targets:
        celex = target["celex"]
        known = have.get(celex)
        stored = bool(known) and pathlib.Path(known.get("textPath", "")).exists()
        current = {**known, "relations": target.get("relations", known.get("relations", []))} if stored else None
        short = stored and celex.startswith("6") and not known.get("ending")  # 앞부분만 받아 둔 법원 문서: 끝부분을 채운다
        late = deadline and time.monotonic() > deadline
        if stored and (not short or late):  # 이미 받은 문서는 그대로 둔다
            entries.append(current)
            report["kept"] += 1
            continue
        if late:  # 시간이 다 되면 새 문서는 다음에 받는다. 이미 받은 문서는 뒤에 있어도 목록에 남긴다
            report.setdefault("stoppedAt", celex)
            continue
        source = CELLAR.format(celex=celex)
        lines, reason = lines_of(celex, report["notes"])
        if not lines:
            report["failures"].append(f"{celex} ({reason})")
            if stored:  # 다시 받지 못했으면 받아 둔 것을 그대로 쓴다
                entries.append(current)
                report["kept"] += 1
            continue
        kept, ending = kept_lines(celex, lines)
        url = EURLEX.format(celex=celex)
        name = celex.replace("(", "-").replace(")", "")
        entry = {"date": target.get("date", ""), "celex": celex, "title": target.get("title", "") or lines[0][:300],
                 "relations": target.get("relations", []), "procedures": procedures_in(lines), "lines": len(lines), "url": url,
                 "textPath": save_text(f"eur-lex-docs/{name}.txt", [f"[주소] {url}", f"[받은 곳] {source}", ""] + kept)}
        if ending:
            entry["ending"] = True
        entries.append(entry)
        report["stored"] += 1
        if short:
            report["notes"].append(f"{celex}: 끝부분을 채움")
    save_index("eur-lex-docs", sorted(entries, key=lambda entry: (entry["date"], entry["celex"])), report)
    return report
