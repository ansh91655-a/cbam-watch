"""국문 PDF 만들기: 글꼴 고르기, 자리 정하기, 글자 들어내기, 문서 하나 만들기(작은 PDF를 만들어서)."""
import pathlib
import shutil
import subprocess
import tempfile
import unittest

from tools.laws import store, unit_segment

try:
    import pikepdf
    import reportlab  # noqa: F401
    from tools.pdfko import build, erase, fonts, glyphs, layout, units
except ImportError:  # 꾸러미가 없는 환경에서는 건너뛴다
    pikepdf = None

from tests.test_units import _tagged_pdf


@unittest.skipUnless(pikepdf, "pikepdf와 reportlab이 있어야 한다")
class FontsTest(unittest.TestCase):
    def test_family_and_weight_follow_the_original_font(self):
        self.assertEqual((fonts.family("ABCDEF+TimesNewRomanPS-BoldMT"), fonts.bold("ABCDEF+TimesNewRomanPS-BoldMT")), ("serif", True))
        self.assertEqual((fonts.family("XYZABC+ArialMT"), fonts.bold("XYZABC+ArialMT")), ("sans", False))

    def test_each_character_gets_a_font_that_has_it(self):
        self.assertEqual(fonts.face("가", "sans", True)[0], "Pretendard-Bold")
        self.assertEqual(fonts.face("가", "serif", False)[0], "NanumMyeongjo-Regular")
        self.assertEqual(fonts.face("A", "serif", False)[0], "Tinos-Regular")      # 부리글꼴 문서의 로마자는 Times와 폭이 같은 글꼴
        self.assertEqual(fonts.pieces("가 A", "serif", False), [("NanumMyeongjo-Regular", "가"), ("Tinos-Regular", " A")])
        self.assertGreater(fonts.width("가나", "sans", False, 10), fonts.width("ab", "sans", False, 10))

    def test_tidy_drops_what_no_font_can_draw(self):
        fonts.missing.clear()
        self.assertEqual(fonts.tidy("앞\t(\U00013000)  뒤 ⚫"), "앞 뒤 ●")       # 빠진 글자만 든 괄호도 뺀다
        self.assertEqual(fonts.missing, {"\U00013000"})
        self.assertEqual(fonts.tidy("𝐸𝑚 값"), "Em 값")                         # 수식 글자는 여느 글자로


@unittest.skipUnless(pikepdf, "pikepdf와 reportlab이 있어야 한다")
class LayoutTest(unittest.TestCase):
    def test_wrap_fills_cells_in_order_and_breaks_long_words(self):
        measure = len
        cells = [(0, 10, 7), (0, 20, 7), (0, 30, 7)]
        self.assertEqual([line for _, line, _ in layout._wrap("가나 다라 마바사".split(), cells, measure, 1)], ["가나 다라", "마바사"])
        self.assertEqual([line for _, line, _ in layout._wrap(["가나다라마바사아자"], cells, measure, 1)], ["가나다라마바사", "아자"])
        self.assertIsNone(layout._wrap("하나 둘 셋 넷 다섯 여섯 일곱 여덟".split(), cells[:1], measure, 1))

    def test_share_splits_at_sentence_ends_by_weight(self):
        self.assertEqual(layout._share("첫 문장이다. 둘째 문장이다. 셋째 문장이다.", [10, 20]), ["첫 문장이다.", "둘째 문장이다. 셋째 문장이다."])
        self.assertIsNone(layout._share("문장 하나뿐이다.", [10, 20]))

    def test_hang_keeps_the_original_bullet(self):
        self.assertEqual(layout.hang([{"page": 0}], [], "• Mining of ore", "• 광석 채굴"), ([{"page": 0}], "광석 채굴"))
        self.assertEqual(layout.hang([{"page": 0}], [], "Mining of ore", "광석 채굴"), ([{"page": 0}], "광석 채굴"))


def _plain_pdf(path):
    pdf = pikepdf.new()
    page = pdf.add_blank_page(page_size=(300, 200))
    font = pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.Font, Subtype=pikepdf.Name.Type1, BaseFont=pikepdf.Name.Helvetica))
    page.obj.Resources = pikepdf.Dictionary(Font=pikepdf.Dictionary(F1=font))
    page.obj.Contents = pdf.make_stream(b"BT /F1 12 Tf 20 150 Td [(Hello) -300 (World)] TJ ( again) Tj 0 -20 Td (Second line) ' ET")
    pdf.save(path)


@unittest.skipUnless(pikepdf, "pikepdf와 reportlab이 있어야 한다")
class EraseTest(unittest.TestCase):
    def test_removed_glyphs_leave_the_rest_in_place(self):
        with tempfile.TemporaryDirectory() as folder:
            source, target = pathlib.Path(folder) / "a.pdf", pathlib.Path(folder) / "b.pdf"
            _plain_pdf(source)
            sheet = glyphs.read(source)[0]
            where = {(order, index): glyph for order, show in enumerate(sheet.shows) for index, glyph in enumerate(show["glyphs"])}
            gone = {0: {0, 1, 2, 3, 4}, 2: {0, 1}}      # "Hello"와 둘째 줄의 "Se"
            self.assertTrue(all(erase.able(sheet.shows[order], marks) for order, marks in gone.items()))
            with pikepdf.open(source) as pdf:
                self.assertTrue(erase.sound(pdf.pages[0], sheet))
                self.assertEqual(erase.strip(pdf, pdf.pages[0], sheet, gone), (7, []))
                pdf.save(target)
            after = glyphs.read(target)[0]
            left = [(glyph["text"], round(glyph["x0"], 2), round(glyph["base"], 2)) for show in after.shows for glyph in show["glyphs"]]
            kept = [(glyph["text"], round(glyph["x0"], 2), round(glyph["base"], 2)) for key, glyph in sorted(where.items()) if key[1] not in gone.get(key[0], ())]
            self.assertEqual(left, kept)
            self.assertEqual("".join(text for text, _, _ in left), "World againcond line")

    def test_text_inside_a_shared_form_is_left_alone(self):
        show = {"stream": 12, "counts": [3], "unit": 1, "glyphs": []}
        self.assertFalse(erase.able(show, {0}))
        self.assertTrue(erase.able(show, {0}, once={12}))
        self.assertFalse(erase.able({"stream": glyphs.PAGE, "counts": [3], "unit": None, "glyphs": []}, {0}))  # 글자 경계를 모르는 글꼴은 통째로만


@unittest.skipUnless(pikepdf and shutil.which("pdftotext"), "pikepdf, reportlab, pdftotext가 있어야 한다")
class BuildTest(unittest.TestCase):
    def test_builds_a_korean_pdf_in_the_same_places(self):
        korean = {"Scope": "적용 범위", "Goods are covered[1]": "제품이 대상이다[1]", "(a) iron and steel": "(a) 철강", "[1] See Annex I.": "[1] 부속서 I을 본다."}
        memory = {store.key(text): value for text, value in korean.items()}
        with tempfile.TemporaryDirectory() as folder:
            source = pathlib.Path(folder) / "small.pdf"
            _tagged_pdf(source)
            found = units.read(source)["units"]
            parts = unit_segment.parts(found)
            wanted = build.items(parts, found, memory)
            self.assertEqual([(text, ko, lead) for _, text, ko, lead in wanted], [
                ("Scope", "적용 범위", ["1"]), ("Goods are covered[1]", "제품이 대상이다[1]", []), ("(a) iron and steel", "철강", []), ("[1] See Annex I.", "부속서 I을 본다.", ["1"])])
            made = [pathlib.Path(folder) / name for name in ("one.pdf", "two.pdf")]
            reports = [build.build(source, wanted, target, "시험 문서", "A test", found) for target in made]
            self.assertEqual((reports[0]["placed"], reports[0]["left"], reports[0]["failed"], reports[0]["pages"]), (4, {}, 0, 1))
            self.assertEqual(made[0].read_bytes(), made[1].read_bytes())      # 같은 입력이면 같은 파일
            text = subprocess.run(["pdftotext", str(made[0]), "-"], capture_output=True, check=True).stdout.decode("utf-8")
            with pikepdf.open(made[0]) as pdf:
                self.assertEqual((len(pdf.pages), str(pdf.docinfo["/Title"])), (1, "시험 문서 (비공식 국문 번역)"))
        for piece in ("적용 범위", "제품이 대상이다[1]", "철강", "부속서 I을 본다.", "비공식 국문 번역입니다", "(a)", "7"):
            self.assertIn(piece, text)                                        # 번역과 알림, 그대로 둔 표와 쪽 번호
        for piece in ("Scope", "Goods", "iron", "Annex"):
            self.assertNotIn(piece, text)                                     # 옮긴 자리의 원문은 남지 않는다


if __name__ == "__main__":
    unittest.main()
