"""표를 칸의 자리를 살려 읽고(htmlgrid), 한 줄로 적고 다시 읽고(rowtext), 받아 둘 표를 고르는 일(archive.tables)."""
import unittest

from tools.archive import tables
from tools.common.htmlgrid import expand, grids
from tools.common.rowtext import format_row, parse_row, read_tables

COUNTRY = """<p>{name}</p>
<table><tr><th>Product CN Code / TARIC Code</th><th>Description</th><th>Default Value (direct emissions)</th>
<th>Default Value (total emissions)</th><th>Underlying production route determining CBAM BM</th></tr>
<tr><td colspan="5"><p>Cement</p></td></tr>
<tr><td><p>2523 21 00</p></td><td><p>White</p><p>Portland cement</p></td><td>-</td><td>-</td><td></td></tr>
<tr><td rowspan="2">7208</td><td>Flat-rolled</td><td>1,5</td><td>1,6</td><td>(C)</td></tr>
<tr><td>Flat-rolled, alloy<table><tr><td>(a)</td><td>note</td></tr></table></td><td>2,5</td><td>2,6</td><td>(F)</td></tr>
</table>"""
PAGE = "<html><body><p>Intro</p>" + "".join(COUNTRY.format(name=name) for name in ("Albania", "Korea, Republic of", "Other countries and territories")) + "</body></html>"


class GridTest(unittest.TestCase):
    def test_empty_cells_keep_their_place_and_spans_are_filled(self):
        table = grids(COUNTRY.format(name="Albania"))[0]
        self.assertEqual(table["caption"], "Albania")
        self.assertEqual(table["rows"][1], ["Cement"] * 5)
        self.assertEqual(table["rows"][2], ["2523 21 00", "White Portland cement", "-", "-", ""])
        self.assertEqual([row[0] for row in table["rows"][3:]], ["7208", "7208"])

    def test_a_table_inside_a_cell_is_returned_too_and_its_words_stay_in_the_cell(self):
        found = grids(COUNTRY.format(name="Albania"))
        self.assertEqual(len(found), 2)
        self.assertEqual(found[0]["rows"][4][1], "Flat-rolled, alloy (a) note")
        self.assertEqual(found[1]["rows"], [["(a)", "note"]])

    def test_a_table_that_wraps_the_whole_page_does_not_hide_the_tables_inside(self):
        wrapped = "<table><tr><td>" + COUNTRY.format(name="Albania") + "</td></tr></table>"
        captions = [table["caption"] for table in grids(wrapped)]
        self.assertIn("Albania", captions)
        self.assertEqual([table["caption"] for table in tables.data_tables(wrapped)], ["Albania"])

    def test_short_rows_are_padded_and_absurd_spans_are_capped(self):
        self.assertEqual(expand([[("a", 1, 1), ("b", 1, 1)], [("c", 1, 1)]]), [["a", "b"], ["c", ""]])
        self.assertEqual(len(grids('<table><tr><td colspan="99999">a</td></tr></table>')[0]["rows"][0]), 400)


class RowTextTest(unittest.TestCase):
    def test_a_row_survives_being_written_and_read_back(self):
        for cells in (["a", "", "c"], ["", "b", ""], ["2523 21 00", "White Portland cement", "-", ""], ["a | b", "c"]):
            line = format_row(cells)
            self.assertEqual(parse_row(line), [cell.replace("|", "/") for cell in cells])
        self.assertIsNone(parse_row("[표 3] Albania"))
        self.assertIsNone(parse_row("plain words"))

    def test_tables_are_read_back_with_their_captions(self):
        lines = ["[주소] x", "[읽는 법] y", "", "[표 4] Korea, Republic of", format_row(["a", "", "c"]), format_row(["d", "e", ""]), "", "[표 9] Other", format_row(["x", "y", "z"])]
        found = read_tables(lines)
        self.assertEqual([(table["number"], table["caption"], len(table["rows"])) for table in found], [(4, "Korea, Republic of", 2), (9, "Other", 1)])
        self.assertEqual(found[0]["rows"][1], ["d", "e", ""])


class PickTest(unittest.TestCase):
    def test_only_the_tables_for_korea_and_other_countries_are_kept(self):
        kept, names, why = tables.pick_defaults(tables.data_tables(PAGE))
        self.assertEqual(why, "")
        self.assertEqual(names, ["Albania", "Korea, Republic of", "Other countries and territories"])
        self.assertEqual([table["caption"] for table in kept], ["Korea, Republic of", "Other countries and territories"])

    def test_a_missing_korea_table_is_a_failure_that_names_what_was_found(self):
        page = PAGE.replace("Korea, Republic of", "Korea, Democratic People's Republic of")
        kept, _, why = tables.pick_defaults(tables.data_tables(page))
        self.assertEqual(kept, [])
        self.assertIn("대한민국의 표를 찾지 못함", why)
        self.assertIn("Albania", why)

    def test_a_title_row_inside_the_table_becomes_the_caption(self):
        page = PAGE.replace("<p>Korea, Republic of</p>\n<table>", '<p>(unrelated)</p><table><tr><td colspan="5">Korea, Republic of</td></tr>')
        kept, _, why = tables.pick_defaults(tables.data_tables(page))
        self.assertEqual(why, "")
        self.assertEqual(kept[0]["caption"], "Korea, Republic of")
        self.assertTrue(kept[0]["rows"][0][0].startswith("Product CN Code"))

    def test_a_document_with_too_few_rows_is_not_taken_for_the_benchmark_table(self):
        kept, why = tables.pick_benchmarks(tables.data_tables(COUNTRY.format(name="x")))
        self.assertEqual(kept, [])
        self.assertIn("벤치마크 표로 볼 만한 행", why)

    def test_the_words_around_a_value_table_are_kept_in_order_with_a_mark_where_the_table_was(self):
        page = ("<p>4. EARLIER PART</p><p>5. CBAM BENCHMARKS</p><p>5.1. Rules</p>"
                "<table><tr><td>(a)</td><td>first rule</td></tr></table>"
                + COUNTRY.format(name="5.3. Table") +
                "<table><tr><td>(1)</td><td>applies in 2026 and 2027</td></tr></table><p>last words</p>")
        lines = tables.outside_text(page, "CBAM BENCHMARKS")
        self.assertEqual(lines[:5], ["5. CBAM BENCHMARKS", "5.1. Rules", "(a)", "first rule", "5.3. Table"])
        self.assertEqual(lines[5:], ["[여기에 표 2]", "(1)", "applies in 2026 and 2027", "last words"])
        self.assertEqual(tables.outside_text(page, "NO SUCH HEADING"), [])

    def test_the_stored_text_lists_each_table_under_its_number_and_caption(self):
        kept, _, _ = tables.pick_defaults(tables.data_tables(PAGE))
        back = read_tables(tables.text_lines(kept))
        self.assertEqual([table["caption"] for table in back], ["Korea, Republic of", "Other countries and territories"])
        self.assertEqual(back[0]["rows"][2], ["2523 21 00", "White Portland cement", "-", "-", ""])


if __name__ == "__main__":
    unittest.main()
