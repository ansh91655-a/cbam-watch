"""원문을 열지 못해 보류된 초안을 몇 번까지 다시 검증에 내는지 정해 둔 곳.

몇 번째 검증인지는 초안 id의 끝에서 읽는다: 표시가 없으면 첫 번째, `-c2`면 두 번째, `-c3`이면 세 번째다.
다시 내는 프로그램(holds_to_recheck)과 그날의 요약(day_summary)이 같은 규칙을 쓰도록 여기에 모았다.
운영 콘솔의 `console/js/model.js`에도 같은 규칙이 있다. 한쪽을 고치면 다른 쪽도 고친다.
"""
import re

GATE = "확인 불가"
LAST = 3  # 세 번째에도 원문을 열지 못하면 사람이 볼 보류로 남긴다
_MARK = re.compile(r"-c(\d+)$")


def attempt(item_id):
    """이 초안이 몇 번째로 검증에 나온 것인지."""
    found = _MARK.search(str(item_id))
    return int(found.group(1)) if found else 1


def root(item_id):
    """다시 낸 표시를 뗀 처음의 id."""
    return _MARK.sub("", str(item_id))


def next_id(item_id):
    """다시 낼 때 쓸 id. 더 내지 않는 초안이면 빈 글."""
    turn = attempt(item_id)
    return f"{root(item_id)}-c{turn + 1}" if turn < LAST else ""


def is_last(item_id):
    return attempt(item_id) >= LAST
