"""문단을 나누는 방식이 바뀐 문서에서, 글자와 숫자는 같고 띄어쓰기·문장부호·글머리표만 달라진 문단에 옛 번역을 옮겨 붙인다.

PDF 문서를 글의 줄에서 나누다가(guide_segment) PDF의 꼬리표에서 읽은 단위로 나누게 되면(unit_segment) 문단의 열쇠가 달라진다.
뜻이 같은 문단까지 다시 옮기지 않도록, 옛 방식으로 나눈 문단과 글자·숫자가 똑같은 새 문단에는 그 번역과 검수 표시를 그대로 붙인다.
옮겨 붙인 번역도 검사(tools.laws.check)를 지나야 한다. 지나지 못하면 붙이지 않는다(번역할 것으로 남는다).

    python3 -m tools.laws.carry            # 모든 PDF 문서에서 옮겨 붙이고 문서마다 몇 개인지 알린다
"""
import pathlib
import re
import sys

from tools.common.jsonio import read_json
from tools.laws import check, corpus, guide_segment, guides, plan, store

MARKER = re.compile(r"^(?:[•◦▪■●○‣·\-–—*o>]|\(?[0-9a-zA-Z]{1,4}[.)])$")


def squash(text):
    return "".join(char for char in text.lower() if char.isalnum())


def _with_marker(source, korean):
    """새 원문이 글머리표로 시작하는데 옛 번역에는 없으면 같은 표를 붙인다."""
    head = source.split(" ", 1)[0]
    if MARKER.match(head) and not korean.startswith(head):
        return f"{head} {korean}"
    return korean


def carry(act, memory, checked):
    """문서 하나에서 옮겨 붙인다. 돌려주는 것은 (붙인 문단 수, 검사에 걸려 붙이지 못한 수)."""
    path = pathlib.Path(act["path"])
    if act.get("format") != "pdf" or not path.is_file() or not corpus.units(act):
        return 0, 0
    old = guide_segment.parts(path.read_text(encoding="utf-8"), act.get("outline", "auto"))
    loose = {}
    for part in old:
        for text in corpus.texts(part):
            korean = memory.get(store.key(text))
            if korean and korean != text:
                loose.setdefault(squash(text), (korean, store.key(text) in checked))
    blocks = store.load(act["id"])
    marks = store.load_checked(act["id"])
    screen, excused = act["id"].startswith("reg-"), plan.excused()
    added = failed = 0
    for part in corpus.read(act):
        for text in corpus.texts(part):
            block_key = store.key(text)
            if block_key in memory or block_key in blocks or not check.needs(text):
                continue
            found = loose.get(squash(text))
            if not found:
                continue
            korean = _with_marker(text, found[0])
            if check.problems(text, korean, screen=screen, excused=block_key in excused)["hard"]:
                failed += 1
                continue
            blocks[block_key] = korean
            if found[1]:
                marks.add(block_key)
            added += 1
    if added:
        store.save(act["id"], blocks, (read_json(store.path_of(act["id"]), {}) or {}).get("updated"), marks)
    return added, failed


def main():
    memory, checked = store.load_all(), store.checked_all()
    total = 0
    for act in guides.documents():
        added, failed = carry(act, memory, checked)
        if added or failed:
            print(f"{act['id']}: 옮겨 붙임 {added}개" + (f", 검사에 걸려 남김 {failed}개" if failed else ""))
        total += added
    print(f"모두 {total}개를 옮겨 붙였습니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
