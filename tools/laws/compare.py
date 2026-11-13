"""문서의 두 판을 문단 단위로 견준다. 받기와 쓰기는 하지 않는다(tools.laws.revisions가 불러 쓴다).

조각(조, 부속서, 절)의 이름과 문단을 글의 차례대로 늘어놓고, 글자가 같은 문단을 먼저 맞춘다. 맞지 않는 구간에서는 닮은 문단끼리
차례를 지키며 짝지어 '바뀜'으로, 짝이 없는 옛 문단은 '빠짐', 새 문단은 '더해짐'으로 본다.
머리(제목과 근거), 전문, 맺음, 각주, 표지는 견주지 않는다: 통합본에는 전문과 서명이 없고 각주의 번호가 달라, 판이 바뀌지 않아도 달라 보인다.

글은 그대로인데 싣는 꼴만 달라진 것은 달라진 것으로 보지 않는다.
- 각주 표시의 번호만 다른 문단: 통합본은 "( 7 )", 관보의 글은 "(1)", PDF 문서는 "[7]"로 적고, 판마다 번호를 새로 매긴다.
- 줄이 갈린 자리만 다른 문단: 한 판에서는 두 줄("72 –", "Iron and steel")인 것이 다른 판에서는 한 줄("72 – Iron and steel")인 곳.
- 글자 없이 수와 기호뿐인 줄이 더해지거나 빠진 것.
- 관보를 인용하는 각주의 줄("(1) Directive … (OJ L 158, …)")이 더해지거나 빠진 것: 관보의 글은 각주를 부속서 끝에, 통합본은 문서 끝에 싣는다.
"""
import difflib
import re

KINDS = ("article", "annex", "section", "appendix")  # 견주는 조각
SIMILAR = 0.5   # 낱말로 본 닮은 정도가 이만큼은 되어야 같은 문단이 바뀐 것으로 본다
WINDOW = 3600   # 맞지 않는 구간의 (옛 문단 수 × 새 문단 수)가 이보다 크면 닮은 것을 찾지 않는다(통째로 다시 쓴 곳이다)
LEAD = re.compile(r"^(\d+[a-z]{0,2}\.|\(\w{1,4}\))$")   # 문단 머리의 번호: "2.", "3a.", "(a)", "(15)"
SHORTEST = 5    # 같은 번호의 문단을 '들어 있는 비율'로 견줄 때, 짧은 쪽이 이만큼의 낱말은 되어야 한다
CONTAINED = 0.7  # 짧은 쪽의 낱말(번호는 빼고)이 긴 쪽에 이만큼 그대로 있으면 닮은 것으로 본다
QUOTES = str.maketrans({"‘": "'", "’": "'", "“": "'", "”": "'", '"': "'", "–": "-", "—": "-", "\u00a0": " "})  # 따옴표는 홑·겹을 가리지 않는다(개정 법령이 끼워 넣은 글은 겹따옴표로 실린다)


SPACED = re.compile(r"\(\s\d{1,3}\s\)")   # 통합본의 각주 표시: ( 7 )
BRACKET = re.compile(r"\[\d{1,3}\]")       # PDF 문서의 각주 표시: [7]
PLAIN = r"\(\d{1,3}\)"                     # 관보의 글의 각주 표시: (7). 조문을 가리키는 말("제5조(1), (2)")과 꼴이 같아 함부로 지우지 않는다
MASK = "(#)"
WORDY = re.compile(r"[A-Za-z]")
CITED = re.compile(r"^\(\s?\d{1,3}\s?\)\s.*\(OJ [LC] ")   # 관보를 인용하는 각주의 줄


def norm(text):
    """같은 문단인지 볼 때의 글: 띄어쓰기와 따옴표, 줄표의 꼴, 각주 표시의 번호(통합본과 PDF 문서의 꼴)가 다른 것은 같은 것으로 본다."""
    plain = re.sub(r"\s+", " ", str(text).translate(QUOTES)).strip()
    return BRACKET.sub("[#]", SPACED.sub(MASK, plain))


def _same_but_notes(old, new):
    """두 글(norm을 거친 것)이 각주 표시의 꼴과 번호만 다른가. 한쪽은 "( 7 )"로, 다른 쪽은 "(1)"로 적은 경우를 본다.

    띄어 적은 표시가 있는 쪽을 틀로 삼아, 그 자리에만 "(숫자)"가 있고 나머지 글자가 모두 같을 때만 같다고 본다.
    """
    for plain, spaced in ((old, new), (new, old)):
        if MASK in spaced and MASK not in plain:
            if re.fullmatch(re.escape(spaced).replace(re.escape(MASK), PLAIN), plain):
                return True
    return False


def entries(parts):
    """조각들을 견줄 줄로 편다: [{"part": 조각의 id, "at": 조각 안에서의 차례(이름은 -1), "text": 글}]"""
    found = []
    for part in parts:
        if part["kind"] not in KINDS:
            continue
        if part.get("title"):
            found.append({"part": part["id"], "at": -1, "text": part["title"]})
        found += [{"part": part["id"], "at": index, "text": text} for index, text in enumerate(part["blocks"])]
    return found


def _likeness(old, new):
    """두 문단이 낱말로 얼마나 닮았는가(0~1). 닮지 않은 것이 뻔하면 셈을 줄인다.

    같은 번호로 시작하는 두 문단은, 짧은 쪽의 낱말이 긴 쪽에 거의 그대로 들어 있으면 닮은 것으로 본다.
    문단 하나가 머리말과 목록으로 갈라지거나("2. … shall be determined:" 와 (a), (b)) 뒤에 말이 길게 붙은 경우다.
    """
    before, after = old.split(), new.split()
    matcher = difflib.SequenceMatcher(None, before, after, autojunk=False)
    numbered = bool(before and after and before[0] == after[0] and LEAD.match(before[0]))
    if not numbered and matcher.quick_ratio() < SIMILAR:
        return 0.0
    ratio = matcher.ratio()
    shorter = min(len(before), len(after))
    if numbered and shorter >= SHORTEST:
        kept = (sum(block.size for block in matcher.get_matching_blocks()) - 1) / (shorter - 1)   # 번호를 뺀 낱말 가운데 그대로 있는 비율
        if kept >= CONTAINED:
            ratio = max(ratio, 0.9 * kept)
    return ratio


def _pairs(olds, news):
    """맞지 않는 구간의 옛 문단과 새 문단을 차례를 지키며 짝짓는다: [(옛 차례나 None, 새 차례나 None)].

    닮은 정도의 합이 가장 큰 짝짓기를 고른다. 구간이 너무 크면 짝짓지 않고 옛 문단은 모두 빠진 것, 새 문단은 모두 더해진 것으로 둔다.
    """
    if not olds or not news or len(olds) * len(news) > WINDOW:
        return [(index, None) for index in range(len(olds))] + [(None, index) for index in range(len(news))]
    score = [[_likeness(old, new) for new in news] for old in olds]
    best = [[0.0] * (len(news) + 1) for _ in range(len(olds) + 1)]
    for i in range(len(olds) - 1, -1, -1):
        for j in range(len(news) - 1, -1, -1):
            paired = score[i][j] + best[i + 1][j + 1] if score[i][j] >= SIMILAR else -1.0
            best[i][j] = max(best[i + 1][j], best[i][j + 1], paired)
    found, i, j = [], 0, 0
    while i < len(olds) and j < len(news):
        if score[i][j] >= SIMILAR and best[i][j] == score[i][j] + best[i + 1][j + 1]:
            found.append((i, j))
            i, j = i + 1, j + 1
        elif best[i][j] == best[i + 1][j]:
            found.append((i, None))
            i += 1
        else:
            found.append((None, j))
            j += 1
    return found + [(index, None) for index in range(i, len(olds))] + [(None, index) for index in range(j, len(news))]


def _joins(olds, news):
    """맞지 않는 구간에서 줄이 갈린 자리만 다른 곳을 찾는다: 한쪽의 이웃한 두 문단을 이은 것이 다른 쪽의 문단 하나와 같은 곳.

    돌려주는 것은 [((옛 차례들), (새 차례들))]이고 두 쪽 모두에서 차례가 뒤로만 간다.
    """
    found, i, j = [], 0, 0
    while i < len(olds) and j < len(news):
        hit = None
        for ahead in range(j, len(news)):   # 옛 두 문단 = 새 한 문단
            if i + 1 < len(olds) and f"{olds[i]} {olds[i + 1]}" == news[ahead]:
                hit = ((i, i + 1), (ahead,))
                break
        if hit is None:
            for ahead in range(j, len(news) - 1):   # 옛 한 문단 = 새 두 문단
                if olds[i] == f"{news[ahead]} {news[ahead + 1]}":
                    hit = ((i,), (ahead, ahead + 1))
                    break
        if hit:
            found.append(hit)
            i, j = hit[0][-1] + 1, hit[1][-1] + 1
        else:
            i += 1
    return found


def _window(olds, news):
    """맞지 않는 구간 하나를 푼다: ([(옛 차례나 None, 새 차례나 None)], 같은 것으로 본 문단의 수).

    줄이 갈린 자리만 다른 곳을 먼저 같은 것으로 빼고, 그 사이사이를 닮은 문단끼리 짝짓는다. 각주 표시만 다른 짝도 같은 것으로 뺀다.
    """
    found, same, a, b = [], 0, 0, 0
    for old_span, new_span in _joins(olds, news) + [((len(olds),), (len(news),))]:
        for i, j in _pairs(olds[a:old_span[0]], news[b:new_span[0]]):
            before, after = (a + i if i is not None else None), (b + j if j is not None else None)
            if before is not None and after is not None and _same_but_notes(olds[before], news[after]):
                same += 1
                continue
            found.append((before, after))
        same += 1 if old_span[0] < len(olds) else 0
        a, b = old_span[-1] + 1, new_span[-1] + 1
    return found, same


def rows(old_parts, new_parts):
    """두 판에서 달라진 문단을 글의 차례대로: [{"op": "changed"|"added"|"removed", "old": 옛 줄이나 None, "new": 새 줄이나 None}].

    줄은 entries()의 것이다. 같은 문단은 싣지 않는다. 돌려주는 둘째 값은 같은 문단의 수다.
    """
    old, new = entries(old_parts), entries(new_parts)
    matcher = difflib.SequenceMatcher(a=[norm(row["text"]) for row in old], b=[norm(row["text"]) for row in new], autojunk=False)
    found, same = [], 0
    for tag, a0, a1, b0, b1 in matcher.get_opcodes():
        if tag == "equal":
            same += a1 - a0
            continue
        paired, alike = _window([norm(row["text"]) for row in old[a0:a1]], [norm(row["text"]) for row in new[b0:b1]])
        same += alike
        for i, j in paired:
            before = old[a0 + i] if i is not None else None
            after = new[b0 + j] if j is not None else None
            if not (before and after) and (not WORDY.search((before or after)["text"]) or CITED.match((before or after)["text"])):
                continue   # 글자 없이 수와 기호뿐인 줄이나 관보를 인용하는 각주의 줄이 더해지거나 빠진 것은 싣지 않는다
            found.append({"op": "changed" if before and after else ("added" if after else "removed"), "old": before, "new": after})
    return found, same


def stats(found):
    """달라진 문단의 수: {"changed", "added", "removed"}"""
    return {name: sum(row["op"] == name for row in found) for name in ("changed", "added", "removed")}
