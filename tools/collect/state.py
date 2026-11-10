"""출처별로 '이미 본 것'을 기억한다. 화면의 글 자체는 저장하지 않고 열쇠만 저장한다."""
from tools.common.jsonio import read_json, write_json

STATE_DIR = "collected/state"
MAX_SEEN = 6000


def path_of(code):
    return f"{STATE_DIR}/{code}.json"


def load(code):
    return read_json(path_of(code), None)


def save(code, state):
    seen = state.get("seen", {})
    if len(seen) > MAX_SEEN:  # 오래된 것부터 버린다
        keep = sorted(seen.items(), key=lambda pair: pair[1])[-MAX_SEEN:]
        state["seen"] = dict(keep)
    write_json(path_of(code), state)
