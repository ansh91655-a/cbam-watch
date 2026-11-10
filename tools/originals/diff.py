"""두 판의 본문을 문단 단위로 비교한다."""
import difflib
import re

MAX_BLOCKS = 300
MAX_CHARS = 1500


def paragraphs(text):
    """본문을 문단으로 나눈다. 쪽 번호만 있는 줄과 빈 줄은 버리고 공백을 하나로 줄인다."""
    result = []
    for block in re.split(r"\n\s*\n|\f", text or ""):
        line = re.sub(r"\s+", " ", block).strip()
        if not line or re.fullmatch(r"(page\s*)?\d{1,4}(\s*/\s*\d{1,4})?", line, re.I):
            continue
        result.append(line)
    return result


def compare(old_text, new_text):
    """바뀐 곳의 목록과 건수를 돌려준다. op는 added, removed, changed 가운데 하나다."""
    old, new = paragraphs(old_text), paragraphs(new_text)
    matcher = difflib.SequenceMatcher(a=old, b=new, autojunk=False)
    blocks = []
    stats = {"added": 0, "removed": 0, "changed": 0, "same": 0}
    for tag, a0, a1, b0, b1 in matcher.get_opcodes():
        if tag == "equal":
            stats["same"] += a1 - a0
            continue
        if tag == "insert":
            stats["added"] += b1 - b0
            pairs = [("added", "", text) for text in new[b0:b1]]
        elif tag == "delete":
            stats["removed"] += a1 - a0
            pairs = [("removed", text, "") for text in old[a0:a1]]
        else:  # 바뀐 구간: 짝이 맞는 문단은 '바뀜', 남는 문단은 '더해짐'이나 '빠짐'으로 센다
            pairs = []
            for index in range(max(a1 - a0, b1 - b0)):
                before = old[a0 + index] if a0 + index < a1 else ""
                after = new[b0 + index] if b0 + index < b1 else ""
                op = "changed" if before and after else ("added" if after else "removed")
                stats[op] += 1
                pairs.append((op, before, after))
        for op, before, after in pairs:
            if len(blocks) < MAX_BLOCKS:
                blocks.append({"op": op, "old": before[:MAX_CHARS], "new": after[:MAX_CHARS]})
    return {"stats": stats, "blocks": blocks, "truncated": sum(stats[k] for k in ("added", "removed", "changed")) > len(blocks)}
