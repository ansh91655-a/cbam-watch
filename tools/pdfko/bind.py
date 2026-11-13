"""뜻 단위(tools.pdfko.units)를 원문 PDF의 글자와 줄에 잇는다: 단위마다 어느 줄의 어느 글자인지, 그 밖의 글은 어디에 있는지.

단위는 내용 조각 번호(쪽, MCID)로 제 글자를 가리킨다. 그림 안의 이름표는 번호를 여럿이 함께 쓰므로 네모로 가리킨다.
"""

import collections

from tools.pdfko import layout


class Binding:
    """lines는 {단위: {(쪽, 줄): [글자, …]}}, words는 쪽마다의 [(줄, 네모, 단위 또는 None, 글)]."""

    def __init__(self, pages, sheets, units):
        self.pages, self.sheets = pages, sheets
        owner, boxes = {}, collections.defaultdict(list)
        for index, unit in enumerate(units):
            for page, mark in unit.get("marks", []):
                owner[(page, mark)] = index
            if "box" in unit:
                boxes[unit["page"] - 1].append((index, unit["box"]))
        self.lines, self.words = collections.defaultdict(dict), []
        for number, (page, sheet) in enumerate(zip(pages, sheets)):
            row = []
            for at, line in enumerate(page["lines"]):
                for word in line["words"]:
                    marks = [mark for mark in sheet.pick(word["box"]) if not sheet.shows[mark[0]]["hidden"]]
                    votes = collections.Counter()
                    for order, _, glyph in marks:
                        show = sheet.shows[order]
                        if glyph["text"].strip() and not show["artifact"] and show["mcid"] is not None:
                            votes[owner.get((number, show["mcid"]))] += 1
                    index = votes.most_common(1)[0][0] if votes else None
                    if index is None and votes:     # 구조 트리의 그림에 든 글자: 네모로 이름표를 찾는다
                        x, y = (word["box"][0] + word["box"][2]) / 2, (word["box"][1] + word["box"][3]) / 2
                        index = next((unit for unit, box in boxes.get(number, []) if box[0] - 1 <= x <= box[2] + 1 and box[1] - 1 <= y <= box[3] + 1), None)
                    row.append((at, word["box"], index, word["text"]))
                    if index is not None:
                        self.lines[index].setdefault((number, at), []).extend(marks)
            self.words.append(row)

    def slots(self, index, lead=()):
        """단위의 줄 칸들(글의 차례대로). lead는 첫 줄 머리에 남겨 둘 표(번호, 글머리표)의 낱말들이다. 돌려주는 것은 (줄 칸들, "") 또는 (None, 까닭)."""
        found = self.lines.get(index)
        if not found:
            return None, "글자를 찾지 못함"
        out = []
        ordered = sorted(found.items(), key=lambda entry: (entry[0][0], min((order, glyph) for order, glyph, _ in entry[1])))
        for position, ((number, at), marks) in enumerate(ordered):
            if position == 0 and lead:
                marks = self._after_lead(number, at, index, marks, lead)
                if not marks:
                    continue        # 첫 줄에 표만 있다
            inked = [glyph for _, _, glyph in marks if glyph["text"].strip()]
            if not inked:
                continue
            box = self.pages[number]["lines"][at]["box"]
            made, why = layout.slot(number, (min(glyph["x0"] for glyph in inked), box[1], max(glyph["x1"] for glyph in inked), box[3]), marks, self.sheets[number])
            if made is None:
                return None, why
            out.append(made)
        return (out, "") if out else (None, "글자를 찾지 못함")

    def _after_lead(self, number, at, index, marks, lead):
        """첫 줄에서 머리의 표(와 그 뒤의 기호)를 뺀 글자들. 표가 원문과 다르면 그대로 돌려준다."""
        words = sorted((word for word in self.words[number] if word[0] == at and word[2] == index), key=lambda word: word[1][0])
        plain = lambda text: text.strip("[]().:").lower()
        if len(words) < len(lead) or any(plain(word[3]) != plain(token) for word, token in zip(words, lead)):
            return marks
        keep = len(lead)
        while keep < len(words) and not any(char.isalnum() for char in words[keep][3]):
            keep += 1               # 표 뒤의 줄표나 쌍점도 원문 것을 둔다
        if keep >= len(words):
            return []
        edge = words[keep][1][0] - 0.5
        return [mark for mark in marks if mark[2]["x"] >= edge]

    def others(self, index, numbers):
        """이 단위의 것이 아닌 글의 네모들: {쪽: [(x0, 위, x1, 아래)]}."""
        out = {}
        for number in numbers:
            mine = {at for at, _, unit, _ in self.words[number] if unit == index}
            boxes = [line["box"] for at, line in enumerate(self.pages[number]["lines"]) if at not in mine]
            boxes += [box for at, box, unit, _ in self.words[number] if at in mine and unit != index]
            out[number] = boxes
        return out
