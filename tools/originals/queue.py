"""이번 실행에서 받을 문서의 차례를 정한다.

EC 사이트는 짧은 시간에 많이 받으면 접속을 막는다. 그래서 한 번에 정해진 건수만 받는다.
- 처음 보는 문서(아직 받지 못한 것)를 먼저 받는다.
- 남는 몫으로는 이미 아는 문서 가운데 가장 오래 확인하지 않은 것부터 다시 받아 바뀌었는지 본다.
아직 받지 못한 문서는 pending에 적어 두고 다음 실행에서 이어 받는다.
"""

BUDGET = 20   # 한 번 실행에 받는 문서 수
GIVE_UP = 5   # 이만큼 실패한 문서는 월요일에만 다시 시도한다


def note_new_links(pending, found, docs, quiet_pages, first_run, date):
    """처음 보는 문서 링크를 pending에 올린다. 화면을 처음 본 날의 문서는 소식 없이 등록할 것(quiet)으로 표시한다."""
    for doc_id, info in found.items():
        if doc_id in docs or doc_id in pending:
            continue
        pending[doc_id] = {"firstSeen": date, "quiet": bool(first_run or info["page"] in quiet_pages), "tries": 0, "page": info["page"], "name": info["filename"]}


def drop_vanished(pending, found, read_codes):
    """받기 전에 화면에서 사라진 링크는 pending에서 지운다(그 화면을 읽은 날에만)."""
    for doc_id in [doc_id for doc_id, entry in pending.items() if doc_id not in found and entry.get("page") in read_codes]:
        del pending[doc_id]


def build(found, docs, pending, full, monday):
    """받을 문서 번호의 목록을 차례대로 돌려준다."""
    fresh = [doc_id for doc_id in found if doc_id in pending and (pending[doc_id]["tries"] < GIVE_UP or monday or full)]
    fresh.sort(key=lambda doc_id: pending[doc_id]["tries"])
    known = [doc_id for doc_id in found if doc_id in docs]
    known.sort(key=lambda doc_id: docs[doc_id].get("lastChecked", ""))
    order = fresh + known
    return order if full else order[:BUDGET]
