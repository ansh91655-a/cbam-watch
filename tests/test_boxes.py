"""꼬리표가 없는 PDF를 쪽에 놓인 글 상자대로 읽기(tools/pdfko/boxes.py)와, 그렇게 읽은 단위를 문서마다 골라 쓰는 것(tools/laws/corpus.py)."""
import json
import os
import pathlib
import tempfile
import unittest

from tools.laws import corpus, unit_segment
from tools.pdfko import boxes, geometry

CHAR = 5      # 글자 하나의 너비(포인트)
HIGH = 12     # 줄의 높이


def word(text, x, y, height=HIGH, width=None):
    return f'<word xMin="{x}" yMin="{y}" xMax="{x + (width if width is not None else CHAR * len(text))}" yMax="{y + height}">{text}</word>', x + CHAR * len(text) + CHAR


def line(text, x, y, small=(), low=()):
    """줄 하나. small에 든 낱말은 작게 올려 적고(위첨자), low에 든 낱말은 작게 내려 적는다(아래첨자)."""
    out, at = [], x
    for one in text.split(" "):
        if one in small:
            made, at = word(one, at - CHAR, y, height=6)
        elif one in low:
            made, at = word(one, at - CHAR, y + HIGH - 5, height=6)
        else:
            made, at = word(one, at, y)
        out.append(made)
    return f'<line xMin="{x}" yMin="{y}" xMax="{at - CHAR}" yMax="{y + HIGH}">{"".join(out)}</line>'


def block(x, y, *texts, small=(), low=()):
    lines = [line(text, x, y + index * HIGH, small, low) for index, text in enumerate(texts)]
    right = x + max(CHAR * len(text) for text in texts)
    return f'<flow><block xMin="{x}" yMin="{y}" xMax="{right}" yMax="{y + HIGH * len(texts)}">{"".join(lines)}</block></flow>'


def upright(text, x, y):
    """세로로 누운 글 한 줄: 낱말이 아래에서 위로 쌓이고, 낱말마다 너비는 좁고 높이는 길다."""
    out, at = [], y
    for one in reversed(text.split(" ")):
        out.append(f'<word xMin="{x}" yMin="{at}" xMax="{x + 7}" yMax="{at + CHAR * len(one)}">{one}</word>')
        at += CHAR * len(one) + 2
    return f'<flow><block xMin="{x}" yMin="{y}" xMax="{x + 7}" yMax="{at}"><line xMin="{x}" yMin="{y}" xMax="{x + 7}" yMax="{at}">{"".join(reversed(out))}</line></block></flow>'


def page(*blocks):
    return f'<page width="600" height="800">{"".join(blocks)}</page>'


def read(*pages):
    return boxes.units(geometry.parse("".join(pages)))


class BoxesTest(unittest.TestCase):
    def test_a_box_is_one_paragraph_and_boxes_are_read_band_by_band(self):
        found = read(page(
            block(300, 300, "If producer is not in the", "CBAM Registry"),         # 오른쪽 상자가 파일에는 먼저 적혀 있다
            block(40, 300, "If producer is in the", "CBAM Registry"),
            block(40, 100, "TITLE OF THE LEAFLET"),
            block(40, 500, "EU importers"), block(240, 500, "Producers"), block(440, 500, "Verifiers"),
            block(30, 520, "Work with your producers.", "Use verified values."), block(230, 520, "Monitor your emissions."), block(430, 520, "Contact the body."),
            block(40, 160, "Left column first paragraph", "which runs over", "three lines."), block(40, 204, "Left column second paragraph", "of two lines."),
            block(300, 160, "Right column first paragraph", "of two lines."), block(300, 190, "Right column second paragraph", "which also runs over", "three lines."),
        ))
        self.assertEqual([unit["text"] for unit in found], [
            "TITLE OF THE LEAFLET",
            "Left column first paragraph which runs over three lines.", "Left column second paragraph of two lines.",   # 위아래로 겹치는 두 칸: 왼쪽 칸을 다 읽고 오른쪽 칸
            "Right column first paragraph of two lines.", "Right column second paragraph which also runs over three lines.",
            "If producer is in the CBAM Registry", "If producer is not in the CBAM Registry",   # 한 상자의 두 줄은 한 문단, 같은 높이의 상자는 왼쪽부터
            "EU importers", "Work with your producers. Use verified values.",               # 세 칸: 칸마다 제목 다음에 그 글
            "Producers", "Monitor your emissions.", "Verifiers", "Contact the body."])
        self.assertEqual({unit["kind"] for unit in found}, {"p"})
        self.assertEqual((found[0]["page"], found[0]["box"]), (1, [40, 100, 140, 112]))

    def test_text_lying_on_its_side_is_left_out(self):
        found = read(page(block(40, 100, "The body of the page."), upright("Catalogue number: KP-01-26-017-EN-N", 580, 500), upright("© European Union, 2026", 5, 600)))
        self.assertEqual([unit["text"] for unit in found], ["The body of the page."])

    def test_footnote_numbers_are_tied_to_their_lines(self):
        found = read(page(
            block(200, 100, "Are your imports", ">= 50 tonnes annually 1 ?", small=("1",)),
            block(200, 200, "Obtain a reference number 2 . It can be used", "at customs.", small=("2",)),
            block(200, 300, "Direct CO 2 emissions count.", low=("2",)),
            f'<flow><block xMin="41" yMin="700" xMax="44" yMax="718">{line("1", 41, 700)[:0]}'
            '<line xMin="41" yMin="700" xMax="44" yMax="706"><word xMin="41" yMin="700" xMax="44" yMax="706">1</word></line>'
            '<line xMin="41" yMin="712" xMax="44" yMax="718"><word xMin="41" yMin="712" xMax="44" yMax="718">2</word></line></block></flow>',
            block(49, 700, "with the exception of electricity", "valid until 31 March 2026"),
            block(49, 760, "7"),                                           # 가리키는 줄이 없는 수는 문단으로 남는다
        ))
        self.assertEqual([(unit["kind"], unit.get("label", ""), unit["text"]) for unit in found], [
            ("p", "", "Are your imports >= 50 tonnes annually[1]?"),                    # 올려 적은 번호: 각주가 있으면 [1], 뒤의 문장부호도 붙인다
            ("p", "", "Obtain a reference number[2]. It can be used at customs."),
            ("p", "", "Direct CO2 emissions count."),                                    # 내려 적은 2는 그 번호의 각주가 있어도 글자다
            ("note", "1", "with the exception of electricity"),
            ("note", "2", "valid until 31 March 2026"),
            ("p", "", "7")])
        # 조각으로 만들면 각주는 조각 끝에 "[1] …"로 실린다(꼬리표로 읽은 각주와 같다)
        parts = unit_segment.parts(found, "none")
        self.assertEqual(parts[0]["blocks"][-2:], ["[1] with the exception of electricity", "[2] valid until 31 March 2026"])
        self.assertEqual(parts[0]["shapes"][-2:], ["note", "note"])

    def test_a_small_number_without_a_note_is_just_a_letter(self):
        found = read(page(block(40, 100, "Direct CO 2 emissions and 10 m 3 of gas", small=("3",), low=("2",))))
        self.assertEqual(found[0]["text"], "Direct CO2 emissions and 10 m3 of gas")

    def test_lines_are_joined_the_way_they_were_broken(self):
        found = read(page(
            block(40, 100, "Visit: https://taxation-cu", "stoms.ec.europa.eu/carbon-", "border-adjustment-mechanis", "m_en"),   # 너비가 모자라 꺾인 주소: 줄마다 꽉 찼다
            block(40, 300, "See https://europa.eu/x", "Annex"),                       # 주소 뒤의 낱말은 주소가 아니다
            block(40, 400, "This is a non-", "legislative act."),
            block(40, 500, "Read https://europa.eu/y and then", "go.on"),             # 주소로 끝나지 않은 줄 뒤에는 붙이지 않는다
        ))
        self.assertEqual([unit["text"] for unit in found], [
            "Visit: https://taxation-customs.ec.europa.eu/carbon-border-adjustment-mechanism_en",
            "See https://europa.eu/x Annex", "This is a non-legislative act.", "Read https://europa.eu/y and then go.on"])

    def test_control_characters_are_not_text(self):
        found = read(page(block(40, 100, "Buy\x07 and hold \x07 certificates.")))
        self.assertEqual(found[0]["text"], "Buy and hold certificates.")


class ChoiceTest(unittest.TestCase):
    """글 상자대로 읽은 단위는 그렇게 읽기로 한 문서에서만 쓴다(나누는 방식이 바뀌면 이미 옮긴 번역이 떨어진다)."""

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.previous = os.getcwd()
        os.chdir(self.folder.name)
        self.text = pathlib.Path("originals/text/doc-1/abc.txt")
        self.text.parent.mkdir(parents=True)
        self.text.write_text("If producer is in the\nCBAM Registry\n", encoding="utf-8")
        side = corpus.units_path(self.text)
        side.parent.mkdir(parents=True)
        side.write_text(json.dumps({"pages": 1, "tagged": False, "layout": True,
                                    "units": [{"kind": "p", "text": "If producer is in the CBAM Registry", "page": 1, "box": [0, 0, 1, 1]}]}), encoding="utf-8")

    def tearDown(self):
        os.chdir(self.previous)
        self.folder.cleanup()

    def act(self, **more):
        return {"id": "leaflet", "format": "pdf", "path": str(self.text), "outline": "none", **more}

    def test_only_a_document_that_asks_for_it_is_read_by_its_boxes(self):
        self.assertEqual(corpus.units(self.act()), [])                                   # 적지 않은 문서는 전과 같이 글에서 나눈다
        self.assertEqual(corpus.units(self.act(units=False)), [])
        self.assertEqual([unit["text"] for unit in corpus.units(self.act(units="layout"))], ["If producer is in the CBAM Registry"])
        self.assertEqual(corpus.marked(self.act(units="layout")), [])                     # 국문 PDF는 꼬리표로 읽은 단위로만 만든다
        boxed = corpus.read(self.act(units="layout"))
        self.assertEqual([part["blocks"] for part in boxed], [["If producer is in the CBAM Registry"]])
        plain = corpus.read(self.act())
        self.assertEqual(sum(len(part["blocks"]) for part in plain), 2)                   # 줄 단위로는 두 문단으로 갈린다

    def test_tagged_units_are_used_whatever_the_document_says(self):
        side = corpus.units_path(self.text)
        side.write_text(json.dumps({"pages": 1, "tagged": True, "units": [{"kind": "p", "text": "Tagged text.", "page": 1, "marks": [[0, 1]]}]}), encoding="utf-8")
        for mode in ({}, {"units": True}, {"units": "layout"}):
            self.assertEqual([unit["text"] for unit in corpus.units(self.act(**mode))], ["Tagged text."], mode)
        self.assertEqual(len(corpus.marked(self.act())), 1)


if __name__ == "__main__":
    unittest.main()
