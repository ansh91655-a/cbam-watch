"""이번 실행에서 받을 문서의 차례를 정한다.

한 번에 정해진 건수만 받는다(출처 사이트에 부담을 주지 않고, 막혔을 때 피해를 줄이려는 것이다).
1. 처음 보는 문서(한 번도 받아 보지 않은 것)를 먼저 받는다.
2. 남는 몫으로 이미 아는 문서 가운데 가장 오래 확인하지 않은 것부터 다시 받아 바뀌었는지 본다.
3. 전에 받지 못했던 문서는 맨 뒤에서 몇 건만 다시 시도한다. GIVE_UP번 실패한 문서는 월요일에만 다시 시도한다.
아직 받지 못한 문서는 pending에 적어 두고 다음 실행에서 이어 받는다.
"""

BUDGET = 20       # 한 번 실행에 받는 문서 수
RETRY_LIMIT = 4   # 그 가운데 전에 받지 못한 문서를 다시 시도하는 건수
GIVE_UP = 3       # 이만큼 실패한 문서는 월요일에만 다시 시도한다


def note_new_links(pending, found, docs, quiet_pages, first_run, date):
    """처음 보는 문서 링크를 pending에 올린다. 화면을 처음 본 날의 문서는 소식 없이 등록할 것(quiet)으로 표시한다."""
    for doc_id, info in found.items():
        if doc_id in pending and not pending[doc_id].get("label") and info.get("label"):
            pending[doc_id]["label"] = info["label"]   # 전에 올린 문서에도 이름을 채운다(무엇을 받지 못하는지 보고에서 알 수 있게)
        if doc_id in docs or doc_id in pending:
            continue
        pending[doc_id] = {"firstSeen": date, "quiet": bool(first_run or info["page"] in quiet_pages), "tries": 0, "page": info["page"], "name": info["filename"],
                           "label": info.get("label", "")}


def drop_vanished(pending, found, read_codes):
    """받기 전에 화면에서 사라진 링크는 pending에서 지운다(그 화면을 읽은 날에만)."""
    for doc_id in [doc_id for doc_id, entry in pending.items() if doc_id not in found and entry.get("page") in read_codes]:
        del pending[doc_id]


def build(found, docs, pending, full, monday):
    """받을 문서 번호의 목록을 차례대로 돌려준다."""
    fresh = [doc_id for doc_id in found if doc_id in pending and pending[doc_id]["tries"] == 0]
    retry = [doc_id for doc_id in found if doc_id in pending and pending[doc_id]["tries"] > 0 and (pending[doc_id]["tries"] < GIVE_UP or monday or full)]
    retry.sort(key=lambda doc_id: pending[doc_id]["tries"])
    known = [doc_id for doc_id in found if doc_id in docs]
    known.sort(key=lambda doc_id: docs[doc_id].get("lastChecked", ""))
    if full:
        return fresh + known + retry
    if not monday:
        retry = retry[:RETRY_LIMIT]
    room = max(0, BUDGET - len(fresh) - len(retry))
    return fresh + known[:room] + retry


def unreachable(pending):
    """여러 번 받지 못해 평소에는 다시 시도하지 않는 문서의 번호."""
    return [doc_id for doc_id, entry in pending.items() if entry["tries"] >= GIVE_UP]


def names(pending):
    """받지 못하는 문서의 이름들(화면에 적힌 링크의 글, 없으면 파일 이름). 이름을 아는 것부터 늘어놓고, 모르는 것은 실린 화면만 적는다."""
    known, unknown = [], []
    for doc_id in unreachable(pending):
        entry = pending[doc_id]
        name = str(entry.get("label") or entry.get("name") or "").strip()
        (known if name else unknown).append(name[:90] if name else f"이름을 모르는 문서({entry.get('page', '?')})")
    return known + unknown
