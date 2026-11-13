"""PDF의 꼬리표에서 읽은 뜻 단위: 단위 읽기(작은 PDF를 만들어서), 단위에서 조각 만들기, 옛 번역 옮겨 붙이기."""
import decimal
import pathlib
import shutil
import tempfile
import unittest

from tools.laws import carry, unit_segment

try:
    import pikepdf
except ImportError:  # 꾸러미가 없는 환경에서는 PDF를 만드는 시험만 건너뛴다
    pikepdf = None


def unit(kind, text, **more):
    return {"kind": kind, "text": text, "page": 1, "marks": [], **more}


class PartsTest(unittest.TestCase):
    def test_headings_open_sections_and_other_units_become_blocks(self):
        found = unit_segment.parts([
            unit("p", "A cover line."),
            unit("h", "1. FIRST", level=1),
            unit("p", "Body one.[3]"),
            unit("note", "A footnote.", label="3"),
            unit("li", "First item", label="•", depth=1),
            unit("li", "(a) labelled in the text", label="(a)", depth=2),
            unit("h", "Not numbered", level=2),
            unit("cell", "Head", table=1, row=1, column=2, head=True),
            unit("cell", "Value", table=1, row=2, column=2, head=False),
            unit("h", "1.1 Second", level=2),
            unit("caption", "Figure 1: A picture"),
            unit("h", "ANNEX A – Forms", level=1),
            unit("figure", "A label", box=[0, 0, 1, 1]),
        ])
        self.assertEqual([(part["id"], part["kind"], part["label"], part["title"], part["level"]) for part in found], [
            ("cover", "cover", "", "", 0), ("sec-1", "section", "1", "FIRST", 1), ("sec-1-1", "section", "1.1", "Second", 2),
            ("annex-a", "appendix", "Annex A", "Forms", 1)])
        first = found[1]
        self.assertEqual(first["blocks"], ["Body one.[3]", "• First item", "(a) labelled in the text", "Not numbered", "Head", "Value", "[3] A footnote."])
        self.assertEqual(first["shapes"], ["p", "li1", "li2", "h2", "th:1:1:2", "td:1:2:2", "note"])  # 각주는 조각의 끝에 싣는다
        self.assertEqual(first["units"], [2, 4, 5, 6, 7, 8, 3])
        self.assertEqual((found[2]["head"], found[2]["shapes"], found[3]["shapes"]), (9, ["caption"], ["figure"]))

    def test_number_that_does_not_follow_is_not_a_section(self):
        found = unit_segment.parts([unit("h", "1 One", level=1), unit("h", "2026 in review", level=2), unit("h", "2 Two", level=1)])
        self.assertEqual([part["id"] for part in found], ["sec-1", "sec-2"])
        self.assertEqual((found[0]["blocks"], found[0]["shapes"]), (["2026 in review"], ["h2"]))

    def test_outline_none_keeps_one_body(self):
        found = unit_segment.parts([unit("h", "1 One", level=1), unit("p", "Text")], "none")
        self.assertEqual([(part["id"], part["blocks"]) for part in found], [("sec-body", ["1 One", "Text"])])

    def test_borrows_headings_when_the_document_has_no_heading_tags(self):
        old = [{"id": "cover", "kind": "cover", "label": "", "title": "", "level": 0, "blocks": []},
               {"id": "sec-1", "kind": "section", "label": "1", "title": "Introduction", "level": 1, "blocks": []},
               {"id": "sec-2", "kind": "section", "label": "2", "title": "Why we process", "level": 1, "blocks": []}]
        units = [unit("p", "Front"), unit("li", "Introduction", label="1.", depth=1), unit("p", "Words."), unit("p", "2. Why we process"), unit("p", "More.")]
        found = unit_segment.parts(units, "auto", lambda: old)
        self.assertEqual([(part["id"], part["title"], part["blocks"]) for part in found],
                         [("cover", "", ["Front"]), ("sec-1", "Introduction", ["Words."]), ("sec-2", "Why we process", ["More."])])
        self.assertEqual([part["id"] for part in unit_segment.parts(units, "auto")], ["cover"])  # 빌릴 것이 없으면 표지 하나


class CarryTest(unittest.TestCase):
    def test_same_letters_and_marker(self):
        self.assertEqual(carry.squash("• The declarant[4], via  e-mail"), carry.squash("The declarant4 , via e‑mail"))
        self.assertEqual(carry._with_marker("• Mining of ore", "광석 채굴"), "• 광석 채굴")
        self.assertEqual(carry._with_marker("(a) Mining", "(a) 채굴"), "(a) 채굴")
        self.assertEqual(carry._with_marker("Mining of ore", "광석 채굴"), "광석 채굴")


def _tagged_pdf(path):
    """꼬리표가 있는 한 쪽짜리 PDF: 제목, 각주 번호가 붙은 문단, 목록 항목, 각주, 쪽 번호(꾸밈)."""
    pdf = pikepdf.new()
    page = pdf.add_blank_page(page_size=(400, 300))
    font = pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.Font, Subtype=pikepdf.Name.Type1, BaseFont=pikepdf.Name.Helvetica))
    page.obj.Resources = pikepdf.Dictionary(Font=pikepdf.Dictionary(F1=font))
    lines = [("H1", 0, 14, 40, 250, "1 Scope"), ("P", 1, 10, 40, 220, "Goods are covered"), ("Lbl", 2, 10, 40, 200, "(a)"),
             ("LBody", 3, 10, 60, 200, "iron and steel"), ("Note", 4, 8, 40, 60, "1 See Annex I.")]
    stream = ["/Artifact BMC BT /F1 8 Tf 190 20 Td (7) Tj ET EMC"]
    for tag, mark, size, x, y, text in lines:
        stream.append(f"/{tag} <</MCID {mark}>> BDC BT /F1 {size} Tf {x} {y} Td ({text}) Tj ET EMC")
    stream.append("/P <</MCID 5>> BDC BT /F1 6 Tf 132 224 Td (1) Tj ET EMC")  # 문단 끝의 위첨자 각주 번호
    page.obj.Contents = pdf.make_stream(" ".join(stream).encode())

    def element(kind, parent, kids):
        node = pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.StructElem, S=pikepdf.Name("/" + kind), P=parent, Pg=page.obj))
        node.K = pikepdf.Array(kids(node))
        return node

    root = pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.StructTreeRoot))
    item = lambda parent: [element("LI", parent, lambda node: [element("Lbl", node, lambda _: [2]), element("LBody", node, lambda _: [3])])]
    document = element("Document", root, lambda node: [
        element("H1", node, lambda _: [0]),
        element("P", node, lambda paragraph: [1, 5, element("Note", paragraph, lambda _: [4])]),
        element("L", node, item)])
    root.K = pikepdf.Array([document])
    pdf.Root.StructTreeRoot = root
    pdf.save(path)


@unittest.skipUnless(pikepdf and shutil.which("pdftotext"), "pikepdf와 pdftotext가 있어야 한다")
class ReadTest(unittest.TestCase):
    def test_reads_units_from_a_tagged_pdf(self):
        from tools.pdfko import units

        with tempfile.TemporaryDirectory() as folder:
            path = pathlib.Path(folder) / "small.pdf"
            _tagged_pdf(path)
            found = units.read(path)
        self.assertTrue(found["tagged"])
        self.assertEqual([(one["kind"], one["text"], one.get("label", "")) for one in found["units"]], [
            ("h", "1 Scope", ""), ("p", "Goods are covered[1]", ""), ("note", "See Annex I.", "1"), ("li", "iron and steel", "(a)")])
        self.assertEqual(found["units"][1]["marks"], [(0, 1), (0, 5)])

        parts = unit_segment.parts(found["units"])
        self.assertEqual([(part["id"], part["blocks"]) for part in parts], [("sec-1", ["Goods are covered[1]", "(a) iron and steel", "[1] See Annex I."])])

    def test_raised_marks_are_footnote_numbers_only_when_the_note_exists(self):
        from tools.pdfko import units

        mark = lambda text: f"{units.OPEN}{text}{units.CLOSE}"
        found = units._settle([
            {"kind": "p", "text": f"declarant{mark('4')}, 5 m{mark('3')} and 10{mark('4')} with emissions’{mark('4')} or word{mark('9')}"},
            {"kind": "note", "text": "A note.", "label": "4"}])
        self.assertEqual(found[0]["text"], "declarant[4], 5 m3 and 104 with emissions’[4] or word9")

    def test_untagged_pdf_has_no_units(self):
        from tools.pdfko import units

        with tempfile.TemporaryDirectory() as folder:
            path = pathlib.Path(folder) / "plain.pdf"
            pdf = pikepdf.new()
            pdf.add_blank_page(page_size=(200, 200))
            pdf.save(path)
            self.assertEqual(units.read(path), {"pages": 1, "tagged": False, "units": []})


if __name__ == "__main__":
    unittest.main()
