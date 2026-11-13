"""문서 하나의 국문 PDF를 만든다: 원문 PDF에서 번역이 있는 문단의 글자를 들어내고 그 자리에 국문을 앉힌다.

    python3 -m tools.pdfko.build 문서-id [만들 파일]

앉히지 못한 문단은 원문 그대로 남기고 까닭별로 센다(돌려주는 보고).
"""

import collections
import io
import json
import pathlib
import sys

import pikepdf

from tools.pdfko import bind, erase, fonts, geometry, glyphs, layout, match, tags, typeset

SUFFIX = " (비공식 국문 번역)"
SUBJECT = "유럽연합 집행위원회 문서의 비공식 국문 번역입니다. 법적 효력이 없으며 원문과 다를 때에는 원문이 우선합니다. 원문: "


def paragraphs(parts, memory):
    """번역이 있는 문단을 문서의 차례대로: [(열쇠, 원문, 번역)]."""
    from tools.laws import corpus, store

    out = []
    for part in parts:
        for text in corpus.texts(part):
            key = store.key(text)
            korean = memory.get(key)
            if korean and korean != text:
                out.append((key, text, korean))
    return out


def source(document):
    """문서의 원문 PDF 파일. 없으면 None."""
    text = pathlib.Path(document["path"])
    folder = pathlib.Path("originals/files") / text.parent.name / text.stem
    files = sorted(folder.glob("*.pdf"))
    return files[0] if files else None


def _others(pages, spots):
    """이 문단의 것이 아닌 글의 네모들: {쪽: [(x0, 위, x1, 아래)]}."""
    own = {}
    for spot in spots:
        own.setdefault(spot["page"], {}).setdefault(spot["line"], []).append(spot["box"])
    out = {}
    for number, mine in own.items():
        boxes = []
        for index, line in enumerate(pages[number]["lines"]):
            taken = mine.get(index)
            if not taken:
                boxes.append(line["box"])
                continue
            for word in line["words"]:
                middle = (word["box"][0] + word["box"][2]) / 2
                if not any(box[0] - 0.5 <= middle <= box[2] + 0.5 for box in taken):
                    boxes.append(word["box"])
        out[number] = boxes
    return out


def items(parts, units, memory):
    """단위가 있는 문서에서 앉힐 것들을 문서의 차례대로: [(단위의 차례, 원문, 번역, 줄 머리에 남겨 둘 표의 낱말들)].

    번호와 글머리표는 원문 것을 그대로 두고 번역에서는 뗀다(제목의 번호, 목록의 표, 각주 번호).
    """
    from tools.laws import store

    out = []
    for part in parts:
        title = part["title"]
        if part.get("head") is not None and title:
            korean = memory.get(store.key(title))
            if korean and korean != title:
                out.append((part["head"], title, korean, part["label"].split()))
        for text, index in zip(part["blocks"], part.get("units", [])):
            korean = memory.get(store.key(text))
            if not korean or korean == text:
                continue
            unit, lead = units[index], []
            label, head, pieces = unit.get("label", ""), text.split(" ", 1)[0], korean.split(" ", 1)
            if unit["kind"] == "note" and label:
                lead = [label]
                if korean.startswith(f"[{label}] "):
                    korean = korean[len(label) + 3:]
            elif label and not unit["text"].startswith(label):      # 표가 따로 적힌 목록 항목: 단위의 글자에 표가 없다
                if korean.startswith(label + " "):
                    korean = korean[len(label) + 1:]
            elif layout.MARKER.match(head) and len(pieces) == 2 and pieces[0] == head:
                lead, korean = [head], pieces[1]
            out.append((index, text, korean, lead))
    return out


class _Tally:
    """앉힌 것과 남긴 것을 모은다."""

    def __init__(self, sheets):
        self.sheets = sheets
        self.jobs, self.claimed = collections.defaultdict(list), collections.defaultdict(set)
        self.left, self.scales, self.notes = collections.Counter(), [], []

    def leave(self, why, page, text):
        self.left[why] += 1
        self.notes.append((why, page + 1, text[:60]))

    def take(self, placed, page, text):
        """앉힐 자리가 정해진 문단을 받아들인다. 다른 문단과 겹치거나 글자를 들어낼 수 없으면 남긴다."""
        drawn, gone, scale = placed
        if any(marks & self.claimed[number] for number, marks in gone.items()):
            return self.leave("다른 문단과 자리가 겹침", page, text)
        by_show = collections.defaultdict(set)
        for number, marks in gone.items():
            for order, glyph in marks:
                by_show[(number, order)].add(glyph)
        if not all(erase.able(self.sheets[number].shows[order], marks, self.sheets[number].once) for (number, order), marks in by_show.items()):
            return self.leave("들어낼 수 없는 글자", page, text)
        for number, marks in gone.items():
            self.claimed[number] |= marks
        for line in drawn:
            self.jobs[line["page"]].append(line)
        self.scales.append(scale)
        if scale < 0.8:
            self.notes.append((f"글자를 {scale:.2f}배로 줄임", page + 1, text[:60]))

    def report(self, total):
        return {
            "paragraphs": total, "placed": len(self.scales), "shrunk": sum(1 for scale in self.scales if scale < 1.0),
            "smallest": min(self.scales) if self.scales else 1.0, "left": dict(self.left), "notes": self.notes,
        }


def _arrange_units(pages, sheets, sound, wanted, units):
    """단위가 있는 문서: 단위가 가리키는 글자를 바로 찾아 앉힌다. 돌려주는 것은 (쪽마다 그릴 줄, 쪽마다 지울 글자, 보고)."""
    binding, tally = bind.Binding(pages, sheets, units), _Tally(sheets)
    for index, text, korean, lead in wanted:
        lines, why = binding.slots(index, lead)
        page = units[index]["page"] - 1
        if lines is None:
            tally.leave(why, page, text)
            continue
        if not all(sound[slot["page"]] for slot in lines):
            tally.leave("고칠 수 없는 쪽", page, text)
            continue
        placed, why = layout.settle(lines, pages, sheets, binding.others(index, {slot["page"] for slot in lines}), korean, tight="box" in units[index])
        if placed is None:
            tally.leave(why, page, text)
            continue
        tally.take(placed, page, text)
    return tally.jobs, tally.claimed, tally.report(len(wanted))


def _arrange(pages, sheets, sound, wanted):
    """단위가 없는 문서(꼬리표가 없는 PDF): 문단의 글을 원문의 낱말에 맞추어 자리를 찾는다."""
    found, _ = match.locate(pages, [(key, text, "") for key, text, _ in wanted])
    tally, turn = _Tally(sheets), collections.Counter()
    for key, text, korean in wanted:
        occurrences = found.get(key, [])
        index = turn[key]
        turn[key] += 1
        if index >= len(occurrences):
            tally.leave("원문에서 자리를 찾지 못함", 0, text)
            continue
        spots = occurrences[index]
        page = spots[0]["page"]
        if not all(sound[spot["page"]] for spot in spots):
            tally.leave("고칠 수 없는 쪽", page, text)
            continue
        spots, body = layout.hang(spots, pages, text, korean)
        if not spots:
            tally.leave("글머리표뿐인 줄", page, text)
            continue
        placed, why = layout.place(spots, pages, sheets, _others(pages, spots), body)
        if placed is None:
            tally.leave(why, page, text)
            continue
        tally.take(placed, page, text)
    return tally.jobs, tally.claimed, tally.report(len(wanted))


def build(path, wanted, target, title="", original="", units=None):
    """원문 PDF(path)에 번역을 앉혀 target에 쓴다. 보고를 돌려준다.

    units(단위들)를 주면 wanted는 items()가 만든 것이고, 없으면 paragraphs()가 만든 것이다.
    """
    pages = geometry.read(path)
    sheets = glyphs.read(path)
    if len(pages) != len(sheets):
        raise RuntimeError("쪽 수가 읽는 방법마다 다름")
    fonts.missing.clear()
    with pikepdf.open(path) as pdf:
        tree = tags.read(pdf)
        _classify(sheets, tree)
        masks = _masks(sheets, tree)
        sound = [sheet.plain and erase.sound(page, sheet) for page, sheet in zip(pdf.pages, sheets)]
        jobs, claimed, report = _arrange_units(pages, sheets, sound, wanted, units) if units else _arrange(pages, sheets, sound, wanted)
        removed, failed = 0, 0
        for number, marks in claimed.items():
            gone = collections.defaultdict(set)
            for order, glyph in marks:
                gone[order].add(glyph)
            done, bad = erase.strip(pdf, pdf.pages[number], sheets[number], gone)
            removed += done
            failed += len(bad)
        sizes = [(page["width"], page["height"]) for page in pages]
        with pikepdf.open(io.BytesIO(typeset.overlay(sizes, jobs, masks))) as cover:
            for number, page in enumerate(pdf.pages):
                # 겹칠 쪽을 양식으로 옮겨 와 원문 내용 뒤에 그린다. 이름을 쪽 번호로 정해 두어 같은 입력이면 같은 파일이 나온다
                form = pdf.copy_foreign(cover.pages[number].as_form_xobject())
                name = page.add_resource(form, pikepdf.Name.XObject, name=pikepdf.Name(f"/KoPage{number + 1}"))
                page.contents_add(b"q\n", prepend=True)
                page.contents_add(f"\nQ\nq {name} Do Q\n".encode("ascii"))
            _describe(pdf, title, original)
            pdf.save(target, deterministic_id=True, linearize=False)
    report.update({"pages": len(pages), "untouched": sound.count(False), "glyphs": removed, "failed": failed, "missing": "".join(sorted(fonts.missing)),
                   "masked": sum(len(boxes) for boxes in masks.values()),
                   "sizes": [[round(width, 1), round(height, 1)] for width, height in sizes]})
    return report


def _classify(sheets, tree):
    """꼬리표가 있는 문서에서 글자 찍기마다 그림 안의 글자인지 적는다(그림이라고 표시되었거나 어느 문단에도 들지 않은 글자)."""
    if not tree.elements:
        return
    for number, sheet in enumerate(sheets):
        for show in sheet.shows:
            kinds = tree.kinds(number, show["mcid"]) if show["mcid"] is not None else []
            show["figure"] = not show["artifact"] and (not kinds or "Figure" in kinds or "Formula" in kinds)


LOGO = ("logo", "emblem")


def _masks(sheets, tree):
    """기관의 표장이 놓인 자리: {쪽: [(x0, 위, x1, 아래)]}. 번역본이 기관의 공식 문서로 보이지 않게 가린다.

    꼬리표에 그림을 대신하는 글이 "Logo of the European Commission …"으로 적힌 그림을 찾는다.
    그런 글이 없는 문서는 첫 쪽 위쪽의 작은 그림(표장이 놓이는 자리)을 가린다.
    """
    found = {}
    for element in tree.elements:
        if element["type"] == "Figure" and any(word in element.get("alt", "").lower() for word in LOGO):
            for number, mark in element["marks"]:
                box = sheets[number].ink.get(mark) if number < len(sheets) else None
                if box and box[2] - box[0] > 4 and box[3] - box[1] > 4:
                    found.setdefault(number, []).append((box[0] - 1, box[1] - 1, box[2] + 1, box[3] + 1))
    if not found and sheets:
        first = sheets[0]
        small = [box for box in first.images if box[1] < 0.2 * first.height and 20 < box[2] - box[0] <= 0.3 * first.width and 12 < box[3] - box[1] <= 0.12 * first.height]
        if small:
            found[0] = [(box[0] - 1, box[1] - 1, box[2] + 1, box[3] + 1) for box in small]
    return found


def _describe(pdf, title, original):
    """문서 정보: 비공식 번역임을 밝히고, 원문의 꼬리표 짜임은 글자가 바뀌었으므로 뗀다."""
    for name in ("/Metadata", "/StructTreeRoot", "/MarkInfo"):
        if name in pdf.Root:
            del pdf.Root[name]
    pdf.Root.Lang = pikepdf.String("ko-KR")
    info = pdf.docinfo
    for name in ("/Author", "/Creator", "/Keywords", "/ModDate", "/Company", "/Manager"):
        if name in info:
            del info[name]
    info["/Title"] = (title or "국문 번역") + SUFFIX
    info["/Subject"] = SUBJECT + (original or "")
    info["/Producer"] = "cbam-watch"


def main(arguments):
    from tools.laws import corpus

    wanted = arguments[0]
    documents, memory = corpus.everything()
    document, parts = next((document, parts) for document, parts in documents if document["id"] == wanted)
    path = source(document)
    if path is None:
        print("원문 PDF가 없습니다:", wanted)
        return 1
    target = arguments[1] if len(arguments) > 1 else f"{wanted}-ko.pdf"
    units = corpus.units(document)
    wanted = items(parts, units, memory) if units else paragraphs(parts, memory)
    report = build(path, wanted, target, document.get("name", ""), document.get("official", ""), units)
    notes = report.pop("notes")
    print(json.dumps(report, ensure_ascii=False))
    for why, page, text in notes:
        print(f"  {page:3d}쪽 {why}: {text}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
