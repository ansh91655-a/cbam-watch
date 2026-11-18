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
    def test_translations_are_set_in_pretendard(self):
        self.assertEqual((fonts.face(False), fonts.face(True)), ("Pretendard-Regular", "Pretendard-Bold"))
        self.assertEqual((fonts.bold("ABCDEF+TimesNewRomanPS-BoldMT"), fonts.bold("XYZABC+ArialMT")), (True, False))   # 굵기만 원문을 따른다
        self.assertTrue(fonts.has("가") and fonts.has("A", True) and not fonts.has("\U00013000"))
        self.assertGreater(fonts.width("가나", False, 10), fonts.width("ab", False, 10))

    def test_tidy_drops_what_the_font_cannot_draw(self):
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
        for piece in ("적용 범위", "제품이 대상이다[1]", "철강", "부속서 I을 본다.", "비공식 국문 번역본", "공식 문서가 아닙니다", "(a)", "7"):
            self.assertIn(piece, text)                                        # 번역과 알림, 그대로 둔 표와 쪽 번호
        for piece in ("Scope", "Goods", "iron", "Annex"):
            self.assertNotIn(piece, text)                                     # 옮긴 자리의 원문은 남지 않는다


@unittest.skipUnless(pikepdf, "pikepdf와 reportlab이 있어야 한다")
@unittest.skipUnless(pikepdf, "pikepdf와 reportlab이 있어야 한다")
class ContentsTest(unittest.TestCase):
    def test_contents_lines_take_the_translated_titles(self):
        parts = [{"id": "sec-2-1", "kind": "section", "label": "2.1", "title": "Outputs of this work", "level": 2, "blocks": [], "units": []}]
        found = [{"kind": "toc", "text": "2.1 Outputs of this work ........ 4", "page": 2, "marks": []},
                 {"kind": "toc", "text": "2.2 Something else .... 5", "page": 2, "marks": []}]
        memory = {store.key("Outputs of this work"): "이 작업의 결과물"}
        self.assertEqual(build.items(parts, found, memory), [(0, "Outputs of this work", "이 작업의 결과물", ["2.1", "tail"])])

    def test_the_leader_and_page_number_stay(self):
        from tools.pdfko import bind

        def glyphs(text, start=0.0):
            return [(0, index, {"text": char, "x": start + index * 5 + 2.5, "x0": start + index * 5, "x1": start + index * 5 + 5, "size": 10}) for index, char in enumerate(text)]

        kept = bind._before_tail(glyphs("Scope....12"))
        self.assertEqual("".join(mark[2]["text"] for mark in kept), "Scope")
        self.assertEqual("".join(mark[2]["text"] for mark in bind._before_tail(glyphs("Annex 2") + glyphs("15", 100))), "Annex 2")
        self.assertEqual(len(bind._before_tail(glyphs("Annex 12"))), 8)       # 점줄도 틈도 없으면 숫자는 제목의 일부다


@unittest.skipUnless(pikepdf, "pikepdf와 reportlab이 있어야 한다")
class MaskTest(unittest.TestCase):
    def test_the_commission_logo_is_found_by_its_alternative_text(self):
        from tools.pdfko import tags

        tree = tags.Tree()
        tree.elements = [{"type": "Figure", "parent": None, "marks": [(0, 7)], "alt": "Logo of the European Commission, 12 yellow stars"},
                         {"type": "Figure", "parent": None, "marks": [(0, 8)], "alt": "A chart"}]
        sheet = type("Sheet", (), {"ink": {7: (50, 40, 120, 90), 8: (200, 300, 400, 500)}, "images": [(10, 10, 60, 40)], "width": 595, "height": 842})()
        white = {"fill": (1.0, 1.0, 1.0), "label": True, "round": False}
        self.assertEqual(build._masks([sheet], tree), {0: [{"box": (49, 39, 121, 91), **white}]})
        tree.elements = tree.elements[1:]       # 그런 글이 없으면 첫 쪽 위쪽의 작은 그림
        self.assertEqual(build._masks([sheet], tree), {0: [{"box": (9, 9, 61, 41), **white}]})

    def test_places_written_down_for_a_document_are_covered(self):
        pages = [{"lines": [{"text": "CARBON BORDER", "box": (40, 100, 200, 120), "words": []}, {"text": "Carbon  border!", "box": (40, 300, 180, 312), "words": []},
                            {"text": "Something else", "box": (40, 400, 180, 412), "words": []}]}, {"lines": []}]
        covers = [{"page": 1, "box": [228, 26, 392, 107.5], "label": True},
                  {"page": 1, "over": "Carbon Border", "pad": [12, 5], "fill": "#98c448", "round": True},
                  {"page": 2, "box": [18, 762, 130, 830]},
                  {"page": 3, "box": [0, 0, 10, 10]}, {"page": 1, "over": "not on the page"}, {"page": 1}]      # 없는 쪽, 없는 글, 빈 것은 넘긴다
        found = build._covered(pages, covers)
        self.assertEqual(sorted(found), [0, 1])
        self.assertEqual(found[0][0], {"box": (228.0, 26.0, 392.0, 107.5), "fill": (1.0, 1.0, 1.0), "label": True, "round": False})
        green = (0x98 / 255, 0xc4 / 255, 0x48 / 255)
        self.assertEqual(found[0][1:], [{"box": (28, 95, 212, 125), "fill": green, "label": False, "round": True},       # 글자와 숫자만 견주어 같은 줄을 모두
                                        {"box": (28, 295, 192, 317), "fill": green, "label": False, "round": True}])
        self.assertEqual(found[1], [{"box": (18.0, 762.0, 130.0, 830.0), "fill": (1.0, 1.0, 1.0), "label": False, "round": False}])
        self.assertEqual((build._covered(pages, None), build._covered(pages, [])), ({}, {}))

    @unittest.skipUnless(shutil.which("pdftotext"), "pdftotext가 있어야 한다")
    def test_the_covered_place_says_it_is_unofficial_only_where_it_can_be_read(self):
        from tools.pdfko import typeset

        def marks(box, label=True):
            made = typeset.overlay([(300, 200), (300, 200)], {}, {1: [{"box": box, "fill": (1.0, 1.0, 1.0), "label": label, "round": False}]})
            with tempfile.TemporaryDirectory() as folder:
                target = pathlib.Path(folder) / "made.pdf"
                target.write_bytes(made)
                second = subprocess.run(["pdftotext", "-f", "2", "-l", "2", str(target), "-"], capture_output=True, check=True).stdout.decode("utf-8")
            return second.count(typeset.MARK)

        self.assertEqual(marks((20, 40, 220, 100)), 1)                 # 넉넉한 자리
        self.assertEqual(marks((20, 40, 80, 100)), 1)                  # 좁으면 글자를 줄여 적는다
        self.assertEqual(marks((20, 40, 44, 100)), 0)                  # 읽을 수 없게 작아지면 적지 않는다
        self.assertEqual(marks((20, 40, 220, 45)), 0)                  # 낮은 자리도 마찬가지
        self.assertEqual(marks((20, 40, 220, 100), label=False), 0)    # 적지 말라고 한 자리


class MatchTest(unittest.TestCase):
    """문단이 원문 PDF의 어느 낱말들인지 찾기(꾸러미 없이 도는 부분)."""

    @staticmethod
    def _line(text, top, gaps=None):
        """낱말을 왼쪽부터 놓은 줄 하나. gaps는 {낱말의 차례: 앞 낱말과의 틈}(적지 않으면 3pt)."""
        words, at = [], 20.0
        for index, word in enumerate(text.split(" ")):
            at += (gaps or {}).get(index, 3.0) if index else 0
            words.append({"text": word, "box": (at, top, at + 5.0 * len(word), top + 10.0)})
            at += 5.0 * len(word)
        return {"text": text, "box": (20.0, top, at, top + 10.0), "words": words}

    def test_a_short_paragraph_is_not_taken_from_the_start_of_another_sentence(self):
        from tools.pdfko import match

        pages = [{"lines": [self._line("Where objectively justified the period is extended", 100), self._line("where:", 120), self._line("Em is the emissions", 140)]}]
        found, lost = match.locate(pages, [("a", "Where objectively justified the period is extended", ""), ("b", "where:", ""), ("c", "Em is the emissions", "")])
        self.assertEqual(lost, [])
        self.assertEqual([found[name][0][0]["line"] for name in "abc"], [0, 1, 2])
        # 차례가 뒤바뀌어도 긴 문장의 첫 낱말을 짧은 문단으로 삼지 않는다
        found, lost = match.locate(pages, [("b", "where:", ""), ("a", "Where objectively justified the period is extended", "")])
        self.assertEqual((found["b"][0][0]["line"], found["a"][0][0]["line"], lost), (1, 0, []))

    def test_a_cell_followed_by_another_cell_is_still_found(self):
        from tools.pdfko import match

        pages = [{"lines": [self._line("Steel 1.5 2.5", 100, gaps={1: 60.0, 2: 60.0})]}]      # 표의 한 줄: 칸 사이가 넓다
        found, lost = match.locate(pages, [("name", "Steel", "")])
        self.assertEqual((lost, found["name"][0][0]["whole"], found["name"][0][0]["box"]), ([], False, (20.0, 100, 45.0, 110.0)))
        self.assertFalse(match._joined(match.flatten(pages)[0]["words"], 1))
        close = match.flatten([{"lines": [self._line("where the", 100)]}])[0]["words"]
        self.assertEqual([match._joined(close, end) for end in (0, 1, 2)], [False, True, False])       # 줄의 처음과 끝에는 이어진 낱말이 없다


class ActSourceTest(unittest.TestCase):
    """법령의 원문 PDF는 받아 둔 관보 PDF다(tools/archive/actpdf.py의 목록에서 찾는다)."""

    def _stored(self, folder, *numbers):
        import json

        folder = pathlib.Path(folder)
        entries = []
        for celex in numbers:
            (folder / f"{celex}.pdf").write_bytes(b"%PDF-1.7")
            entries.append({"celex": celex, "file": str(folder / f"{celex}.pdf"), "url": f"https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=CELEX:{celex}"})
        listing = folder / "eu-pdfs.json"
        listing.write_text(json.dumps({"entries": entries}), encoding="utf-8")
        return listing

    @unittest.skipUnless(pikepdf, "pikepdf와 reportlab이 있어야 한다")
    def test_an_act_uses_the_stored_gazette_pdf(self):
        from unittest import mock

        with tempfile.TemporaryDirectory() as folder:
            listing = self._stored(folder, "32025R2548", "02023R0956-20251020")
            with mock.patch.object(build, "ACT_PDFS", str(listing)):
                act = {"id": "32025R2548", "celex": "32025R2548", "format": "act", "consolidated": ""}
                self.assertEqual(build.act_pdf(act)["celex"], "32025R2548")
                self.assertEqual(build.source(act), pathlib.Path(folder) / "32025R2548.pdf")
                self.assertIsNone(build.source({"id": "32025R9999", "celex": "32025R9999", "format": "act"}))       # 받아 두지 않은 법령
                # CBAM 규정은 사이트가 싣는 통합본과 같은 판의 PDF만 쓴다
                shown = {"id": "32023R0956", "celex": "32023R0956", "format": "act", "consolidated": "2025-10-20"}
                self.assertEqual(build.act_pdf(shown)["celex"], "02023R0956-20251020")
                self.assertIsNone(build.act_pdf({**shown, "consolidated": "2027-01-01"}))
                (pathlib.Path(folder) / "32025R2548.pdf").unlink()
                self.assertIsNone(build.source(act))                                                                   # 목록에는 있는데 파일이 없다

    @unittest.skipUnless(pikepdf, "pikepdf와 reportlab이 있어야 한다")
    def test_the_site_lists_acts_beside_the_commission_documents(self):
        from unittest import mock

        from tools.pdfko import site

        derive = type("Derive", (), {"STORE": "originals/files/", "PUBLIC_FILES": "files/"})
        with tempfile.TemporaryDirectory() as folder:
            listing = self._stored(folder, "32026R1740")
            entries = [{"celex": "32026R1740", "file": str(pathlib.Path(folder) / "32026R1740.pdf"), "url": "https://example.org/whole", "fullPages": 1913, "kept": [[1, 4], [821, 862]], "about": "조문과 대한민국의 표"}]
            listing.write_text(__import__("json").dumps({"entries": entries}), encoding="utf-8")
            with mock.patch.object(build, "ACT_PDFS", str(listing)):
                act = {"id": "32026R1740", "celex": "32026R1740", "format": "act"}
                self.assertTrue(site._sided(act) and site._sided({"id": "guide-1", "format": "pdf"}))
                self.assertFalse(site._sided({"id": "32025R9999", "celex": "32025R9999", "format": "act"}))             # 관보 PDF가 없는 법령
                self.assertEqual(site._whole(act, build), {"origin": "https://example.org/whole", "part": {"of": 1913, "kept": [[1, 4], [821, 862]], "about": "조문과 대한민국의 표"}})
                self.assertEqual(site._whole({"id": "guide-1", "format": "pdf"}, build), {})
                out = pathlib.Path(folder) / "site"
                self.assertEqual(site._original(out, "originals/files/guide/a/b.pdf", derive), "files/guide/a/b.pdf")    # 원문 대장의 파일은 이미 실려 있다
                self.assertEqual(site._original(out, str(pathlib.Path(folder) / "32026R1740.pdf"), derive), "files/acts/32026R1740.pdf")
                self.assertEqual((out / "files/acts/32026R1740.pdf").read_bytes(), b"%PDF-1.7")


class KeepTest(unittest.TestCase):
    """만들지 못한 국문 PDF는 지난 배포의 것을 그대로 싣는다(꾸러미가 없어도 도는 부분)."""

    def _git(self, folder, *arguments):
        subprocess.run(["git", "-C", str(folder), "-c", "user.name=t", "-c", "user.email=t@example.com", *arguments], check=True, capture_output=True)

    def test_a_document_that_could_not_be_built_keeps_the_last_deployed_file(self):
        import json

        from tools.pdfko import site

        with tempfile.TemporaryDirectory() as folder:
            last, out = pathlib.Path(folder) / "last", pathlib.Path(folder) / "site"
            for name, body in (("pdf/a-ko.pdf", "old a"), ("pdf/b-ko.pdf", "old b"), ("pdf/c-ko.pdf", "old c")):
                (last / name).parent.mkdir(parents=True, exist_ok=True)
                (last / name).write_text(body, encoding="utf-8")
            entry = lambda name: {"pages": 1, "ko": f"pdf/{name}-ko.pdf", "en": f"files/{name}.pdf"}
            (last / "data/laws").mkdir(parents=True)
            (last / "data/laws/pdf.json").write_text(json.dumps({"docs": {name: entry(name) for name in "abc"}}), encoding="utf-8")
            self._git(last, "init", "-q", "-b", "gh-pages")
            self._git(last, "add", "-A")
            self._git(last, "commit", "-q", "-m", "last")

            # 이번에는 a만 만들어졌고 b는 만들지 못했다. c는 원문이 없어져 더는 싣지 않는 문서다
            (out / "pdf").mkdir(parents=True)
            (out / "pdf/a-ko.pdf").write_text("new a", encoding="utf-8")
            (out / "files").mkdir()
            for name in "ab":
                (out / f"files/{name}.pdf").write_text("original", encoding="utf-8")
            (out / "data/laws").mkdir(parents=True)
            listing = out / "data/laws/pdf.json"
            listing.write_text(json.dumps({"docs": {"a": entry("a")}, "wanted": 2, "failed": ["b"], "tools": True}), encoding="utf-8")
            self._git(out, "init", "-q", "-b", "gh-pages")
            self._git(out, "remote", "add", "origin", str(last))
            self._git(out, "fetch", "-q", "origin", "gh-pages")

            self.assertEqual(site.keep(out), ["b"])
            now = json.loads(listing.read_text(encoding="utf-8"))
            self.assertEqual((sorted(now["docs"]), now["kept"]), (["a", "b"], ["b"]))
            self.assertEqual(((out / "pdf/a-ko.pdf").read_text(encoding="utf-8"), (out / "pdf/b-ko.pdf").read_text(encoding="utf-8")), ("new a", "old b"))
            self.assertFalse((out / "pdf/c-ko.pdf").exists())
            self.assertEqual(site.keep(out), [])     # 다 찼으면 더 하지 않는다

    def test_the_gazette_pdf_of_an_act_is_kept_with_its_translation(self):
        import json

        from tools.pdfko import site

        with tempfile.TemporaryDirectory() as folder:
            last, out = pathlib.Path(folder) / "last", pathlib.Path(folder) / "site"
            entries = {"act": {"pages": 1, "ko": "pdf/act-ko.pdf", "en": "files/acts/32025R2548.pdf"}, "gone": {"pages": 1, "ko": "pdf/gone-ko.pdf", "en": "files/gone.pdf"}}
            for name, body in (("pdf/act-ko.pdf", "old act"), ("files/acts/32025R2548.pdf", "gazette"), ("pdf/gone-ko.pdf", "old gone"), ("files/gone.pdf", "original")):
                (last / name).parent.mkdir(parents=True, exist_ok=True)
                (last / name).write_text(body, encoding="utf-8")
            (last / "data/laws").mkdir(parents=True)
            (last / "data/laws/pdf.json").write_text(json.dumps({"docs": entries}), encoding="utf-8")
            self._git(last, "init", "-q", "-b", "gh-pages")
            self._git(last, "add", "-A")
            self._git(last, "commit", "-q", "-m", "last")

            # 이번에는 법령의 국문 PDF를 만들지 못했다. 관보 PDF는 만들 때 옮겨 싣는 것이라 사이트 폴더에 없다
            (out / "data/laws").mkdir(parents=True)
            listing = out / "data/laws/pdf.json"
            listing.write_text(json.dumps({"docs": {}, "wanted": 1, "failed": ["act"], "tools": True}), encoding="utf-8")
            self._git(out, "init", "-q", "-b", "gh-pages")
            self._git(out, "remote", "add", "origin", str(last))
            self._git(out, "fetch", "-q", "origin", "gh-pages")

            self.assertEqual(site.keep(out), ["act"])        # 원문 대장의 파일이 없어진 문서(gone)는 가져오지 않는다
            self.assertEqual(((out / "pdf/act-ko.pdf").read_text(encoding="utf-8"), (out / "files/acts/32025R2548.pdf").read_text(encoding="utf-8")), ("old act", "gazette"))
            self.assertFalse((out / "pdf/gone-ko.pdf").exists() or (out / "files/gone.pdf").exists())

    def test_nothing_is_kept_when_there_is_no_last_deployment(self):
        import json

        from tools.pdfko import site

        with tempfile.TemporaryDirectory() as folder:
            out = pathlib.Path(folder)
            (out / "data/laws").mkdir(parents=True)
            (out / "data/laws/pdf.json").write_text(json.dumps({"docs": {}, "wanted": 3, "failed": [], "tools": False}), encoding="utf-8")
            self._git(out, "init", "-q", "-b", "gh-pages")
            self.assertEqual(site.keep(out), [])


if __name__ == "__main__":
    unittest.main()
