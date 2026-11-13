"""같은 문장은 같은 번역으로: 원문이 같은데 번역이 서로 다른 문단을 찾아 하나로 맞춘다.

여러 문서에 같은 문장이 되풀이된다(가이던스마다 붙은 정의 목록, 법령을 옮겨 적은 문장, 법령마다 같은 전문과 맺음말).
번역은 원문의 글자에서 만든 열쇠에 붙으므로 글자가 똑같으면 번역도 하나지만, 앞의 번호나 각주 번호, 끝의 문장부호가 다르면
다른 문단으로 보아 따로 옮겨지고, 그러다 보면 같은 문장이 문서마다 조금씩 다르게 읽힌다.

- 묶음: 원문에서 앞의 번호·글머리표와 각주 표시([12]), 끝의 문장부호를 떼고 소문자로 바꾼 글이 같은 문단들(짧은 글은 문맥에 따라 뜻이 달라 묶지 않는다).
- 묶음 안의 번역(같은 방식으로 다듬어 견준다)이 둘 이상이면 바탕으로 삼을 번역을 고른다:
  1) 법령의 문단이 쓰는 번역이 있으면 그것(안내 문서가 법령을 옮겨 적은 문장은 법령의 번역을 따른다),
  2) 그 가운데(법령의 것이 없으면 모두 가운데) 가장 많은 자리에서 쓰이는 번역, 같으면 문서의 차례에서 먼저 나온 것.
  3) 사람이나 검토자가 묶음마다 골라 둔 것이 있으면 그것이 먼저다(language/alike-picks.json의 "pick": {묶음의 열쇠: 바탕으로 삼을 문단의 열쇠}).
     "skip"에 적힌 묶음은 맞추지 않는다(자리마다 달리 옮기는 것이 옳은 문장).
- 다른 문단의 번역은 바탕 번역으로 바꾸되 그 문단의 것을 지킨다: 앞의 번호와 글머리표, 각주 번호(원문의 차례대로 짝지어 바꾼다), 끝의 문장부호.
  바꾼 번역이 넣기 전의 검사(tools.laws.check)에 걸리면 바꾸지 않고 알린다.
- 넣는 것은 tools.laws.apply가 한다. 번역이 바뀐 문단은 검수 표시가 지워져 검수 실행이 원문과 다시 견준다.

쓰는 법:
  python -m tools.laws.alike                 묶음의 수와 맞출 문단의 수
  python -m tools.laws.alike --show [N]      묶음을 N개까지 보여 준다(기본 20)
  python -m tools.laws.alike --write <파일>  맞춘 번역을 {"blocks": {열쇠: 국문}} 파일로 쓴다(python -m tools.laws.apply <파일>로 넣는다)
"""
import argparse
import collections
import json
import re
import sys

from tools.common.jsonio import read_json, write_json
from tools.laws import check, corpus, store

PICKS = "language/alike-picks.json"   # 묶음마다 골라 둔 바탕: {"pick": {다듬은 원문: 문단의 열쇠}, "skip": [다듬은 원문], "why": {다듬은 원문: 까닭}}
SHORTEST = 20     # 다듬은 원문이 이보다 짧으면 묶지 않는다("Source", "Total" 같은 말은 자리마다 뜻이 다를 수 있다)
# 문단 앞의 번호와 글머리표 하나: "1.", "(30)", "1a.", "2.1.", "(a)", "(iv)", "—", "•". 번호 뒤는 띄어 쓴 것만 번호로 본다.
# 번호가 아닌 것은 떼지 않는다: "(EU) 2023/956"(대문자), "2026. 1. 1."(네 자리 수), "0.5 tonnes"·"1.1.2026"(점 바로 뒤가 숫자),
# "(c)호의 목적상"(바로 뒤가 글자), "-5 %"(붙임표 바로 뒤가 글자).
PIECE = re.compile(r"(?:(?:\(?\d{1,3}(?:\.\d{1,3}){0,4}[a-z]?[.)]|\([a-z]{1,3}\))(?=\s|$)|[—–\-](?=\s)|[•▪■●○])\s*")
PIECES = 3        # 번호와 글머리표를 이만큼까지 뗀다: "• (a) (i) …"
BULLETS = "—–-•▪■●○"
MARK = re.compile(r"\[(\d+)\]")
GLOSS = re.compile(r"\([A-Za-z][A-Za-z0-9 ,.'’/&\-]*\)")   # 번역에 붙인 영문 병기(견줄 때는 본다: 병기만 다른 번역은 같은 번역이다)
TAILS = ".;:,"
QUOTES = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-", "—": "-", " ": " "})


def leads(text):
    """글 앞의 번호와 글머리표를 차례대로(많아야 PIECES개)."""
    text, found, at = str(text), [], 0
    for _ in range(PIECES):
        hit = PIECE.match(text, at)
        if not hit:
            break
        found.append(hit.group(0))
        at = hit.end()
    return found


def numbered(pieces):
    """번호와 글머리표의 목록에서 번호(글머리표가 아닌 것)의 수."""
    return sum(1 for piece in pieces if piece.strip(BULLETS + " \t\u00a0"))


def shape(text, numbers=None):
    """글을 (앞의 번호·글머리표, 몸, 끝의 문장부호)로 가른다. 셋을 이으면 본디 글이다. numbers를 주면 번호는 그 수까지만 뗀다(글머리표는 세지 않는다)."""
    text = str(text)
    pieces = leads(text)
    if numbers is not None:
        kept = []
        for piece in pieces:
            if numbered([piece]) and numbered(kept) == numbers:
                break
            kept.append(piece)
        pieces = kept
    lead = "".join(pieces)
    body = text[len(lead):]
    tail = body[-1] if body and body[-1] in TAILS else ""
    return lead, body[:len(body) - len(tail)], tail


def shape_ko(source, korean):
    """번역을 (번호, 몸, 끝)으로 가른다. 번호는 원문에 있는 수만큼만 뗀다: 그보다 뒤의 것은 번호가 아니라 번역의 글이다("(2) (c) 목적상 …").

    글머리표(•, —)는 원문에 없어도 글머리표로 본다: 뜻을 싣지 않는 표시이고, 글머리표만 다른 번역을 다른 번역으로 보지 않아야 한다.
    """
    return shape(korean, numbered(leads(source)))


def marks(text):
    """글에 나온 각주 번호를 차례대로."""
    return MARK.findall(str(text))


def norm(source):
    """묶음의 열쇠: 번호와 각주 표시, 끝의 문장부호, 띄어쓰기와 따옴표의 꼴을 떼어 낸 원문."""
    body = MARK.sub("", shape(str(source).translate(QUOTES))[1])
    return re.sub(r"\s+", " ", body).strip().rstrip(TAILS).strip().lower()


def kind(korean, source=None):
    """번역을 견주는 꼴: 번호와 각주 표시, 끝의 문장부호, 띄어쓰기, 영문 병기를 떼어 낸 것. 원문을 주면 번호는 원문에 있을 때만 뗀다."""
    korean = str(korean).translate(QUOTES)
    body = shape(korean)[1] if source is None else shape_ko(str(source).translate(QUOTES), korean)[1]
    body = GLOSS.sub("", MARK.sub("", body))
    return re.sub(r"\s+", "", body).rstrip(TAILS)


def groups(documents, memory, picks=None):
    """원문이 같은데 번역이 다른 묶음: [{"same", "base", "rows": [{"key", "source", "korean", "act", "part", "law", "uses"}]}]. base는 바탕으로 삼을 줄이다.

    picks는 골라 둔 바탕({"pick": {...}, "skip": [...]})이고, 주지 않으면 language/alike-picks.json을 읽는다.
    """
    picks = read_json(PICKS, {}) if picks is None else picks
    chosen, skipped = picks.get("pick") or {}, set(picks.get("skip") or [])
    found = collections.OrderedDict()
    for act, parts in documents:
        law = act.get("group", "act") == "act"
        for part in parts:
            for text in corpus.texts(part):
                block_key = store.key(text)
                if block_key not in memory or not check.needs(text):
                    continue
                same = norm(text)
                if len(same) < SHORTEST:
                    continue
                rows = found.setdefault(same, collections.OrderedDict())
                if block_key in rows:
                    rows[block_key]["law"] = rows[block_key]["law"] or law
                    rows[block_key]["uses"] += 1
                else:
                    rows[block_key] = {"key": block_key, "source": text, "korean": memory[block_key], "act": act["id"], "part": part["id"], "law": law, "uses": 1}
    result = []
    for same, rows in found.items():
        kinds = collections.OrderedDict()
        for row in rows.values():
            kinds.setdefault(kind(row["korean"], row["source"]), []).append(row)
        if len(kinds) < 2 or same in skipped:
            continue
        legal = [members for members in kinds.values() if any(row["law"] for row in members)]
        pool = legal or list(kinds.values())
        best = max(pool, key=lambda members: sum(row["uses"] for row in members))   # 같은 수이면 먼저 나온 것(max는 처음 만난 것을 고른다)
        base = rows.get(chosen.get(same, "")) or best[0]
        result.append({"same": same, "base": base, "rows": list(rows.values())})
    return result


def matched(base, row):
    """row의 번역을 base의 번역에 맞춘 글과 사유. 맞출 수 없으면 ("", 사유), 이미 같으면 (지금의 번역, "")."""
    if kind(row["korean"], row["source"]) == kind(base["korean"], base["source"]):
        return row["korean"], ""
    theirs, mine = marks(base["source"]), marks(row["source"])
    inside = marks(base["korean"])
    if len(theirs) != len(mine) or sorted(inside) != sorted(theirs) or len(set(theirs)) != len(theirs):
        return "", "각주 번호를 짝지을 수 없음"
    renumber = dict(zip(theirs, mine))
    base_lead, body, tail = shape_ko(base["source"], base["korean"])
    lead, _, own_tail = shape_ko(row["source"], row["korean"])
    # 번역이 원문의 번호를 그대로 지닌 것끼리만 맞춘다: 번호의 수가 원문과 다르면 어디까지가 번호인지 알 수 없다
    if numbered(leads(base_lead)) != numbered(leads(base["source"])) or numbered(leads(lead)) != numbered(leads(row["source"])):
        return "", "번호의 꼴이 원문과 달라 맞출 수 없음"
    body = MARK.sub(lambda hit: f"[{renumber[hit.group(1)]}]", body)
    if shape(base["source"])[2] != shape(row["source"])[2]:
        tail = own_tail   # 원문의 끝이 다르면(쉼표와 마침표) 이 문단의 끝을 지킨다
    text = f"{lead}{body}{tail}"
    hard = check.problems(row["source"], text)["hard"]
    return ("", "검사에 걸림: " + "; ".join(hard)[:160]) if hard else (text, "")


def plan(documents=None, memory=None, picks=None):
    """(바꿀 번역 {열쇠: 국문}, 맞추지 못한 것 [(열쇠, 사유)], 묶음의 수)."""
    if documents is None:
        documents, memory = corpus.everything(history=True)
    changes, stuck = {}, []
    found = groups(documents, memory, picks)
    for group in found:
        for row in group["rows"]:
            text, why = matched(group["base"], row)
            if why:
                stuck.append((row["key"], why))
            elif text != row["korean"]:
                changes[row["key"]] = text
    return changes, stuck, len(found)


def summary(documents=None, memory=None, picks=None):
    """한 줄: 같은 문장이 다르게 옮겨진 묶음이 없으면 빈 글."""
    changes, stuck, count = plan(documents, memory, picks)
    if not count:
        return ""
    return f"같은 문장의 번역: 묶음 {count:,}개가 서로 다름(맞출 수 있는 문단 {len(changes):,}개, 맞추지 못하는 문단 {len(stuck):,}개)"


def main(argv):
    parser = argparse.ArgumentParser(description="같은 문장이 다르게 옮겨진 문단을 찾아 하나로 맞춘다.")
    parser.add_argument("--show", nargs="?", type=int, const=20, default=0)
    parser.add_argument("--write", default="")
    args = parser.parse_args(argv)
    documents, memory = corpus.everything(history=True)
    found = groups(documents, memory)
    changes, stuck, count = plan(documents, memory)
    for group in found[:args.show]:
        print(f"== {group['same'][:110]}")
        for row in group["rows"]:
            sign = "바탕" if row is group["base"] else ("바꿈" if row["key"] in changes else "그대로")
            print(f"   [{sign}] {row['act']}.{row['part']}: {row['korean'][:120]}")
    if args.write:
        write_json(args.write, {"blocks": changes})
    for block_key, why in stuck[:10]:
        print(f"맞추지 못함: {block_key}: {why}")
    print(json.dumps({"groups": count, "changes": len(changes), "stuck": len(stuck)}, ensure_ascii=False))   # 마지막 줄은 늘 이 한 줄이다(실행이 읽는다)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
