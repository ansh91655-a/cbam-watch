"""안내 문서(PDF에서 뽑은 글): 쪽 읽기, 문단 묶기, 절 나누기, 문서 목록, 번역 실행의 갈래, 견주기 시험, 사이트 자료."""
import json
import pathlib
import shutil
import tempfile
import unittest

from tools.laws import build, corpus, guide_segment, guides, pdf_blocks, pdf_pages, plan, status, store, todo, trial, wording
from tools.run import laws_health

COVER = """EUROPEAN TEST OFFICE
Test Unit

Brussels, 1 March 2099

GUIDANCE DOCUMENT 9: A TEST

Disclaimer: This guidance document is not legally binding.

Commission européenne/Europese Commissie, 1049 Bruxelles/Brussel, BELGIQUE/BELGIË – Tel. +32 22991111
"""

CONTENTS = """CONTENTS
1

PREFACE

3

1.1

Purpose of this document

3

2

RULES FOR GOODS

4

2.1 Scope of the rules
2.2 Worked example.
4

2.3

Borrowed title

5

ANNEX A

LIST OF TERMS

5

2
"""

PAGE_3 = """1

PREFACE

1.1

Purpose of this document

This series of documents has been written to support readers by explaining the rules in a
plain language. It should help many readers.
A second paragraph starts here and it is long enough to fill the whole width of the lines
before it ends on a short line.
•

The first item of the list;

•

The second item of the list.

Hydrogen is a simple good1 and it stays simple across the page break because the sentence

1

Source: the test regulation.

3
"""

PAGE_4 = """continues here with a lowercase word.

2 RULES FOR GOODS

2.1 Scope of the rules
The rules apply to goods. See the table:
Goods

3

Steel

2.2

Worked example.

The example shows the steps.
4.5. This line starts with a number that is not next in order.

4
"""

PAGE_5 = """2.3

the text under a heading whose title was lost starts in lower case.

ANNEX A

LIST OF TERMS

Term
Meaning of the term

5
"""

GUIDE = "\f".join([COVER, CONTENTS, PAGE_3, PAGE_4, PAGE_5])

QUESTIONS = """Questions and Answers

1. GENERAL
1.1. What must importers do before they bring goods into the customs
territory?
Importers must apply first. They then wait.

1.2. When does it start?
It starts in 2026.
2. The next step is the payment. It takes a day.
3. Once the payment is completed, the certificates are available.
"""


class PagesTest(unittest.TestCase):
    def test_page_numbers_and_the_address_line_are_dropped(self):
        pages = pdf_pages.strip_page_numbers(pdf_pages.split(GUIDE))
        self.assertEqual(len(pages), 5)
        self.assertEqual(pages[2][-1], "Source: the test regulation.")
        self.assertFalse(any("Tel." in line for line in pages[0]))

    def test_a_number_at_the_end_of_one_page_only_is_not_a_page_number(self):
        pages = pdf_pages.strip_page_numbers([["Text", "7"], ["More text"], ["Even more"], ["The end"]])
        self.assertEqual(pages[0], ["Text", "7"])

    def test_headers_repeated_on_most_pages_are_dropped(self):
        goods = ["cement", "steel", "aluminium", "hydrogen", "fertilisers", "electricity", "iron", "clinker"]
        pages = [[f"Registry manual – page {number + 1}", f"This page is about {name}."] for number, name in enumerate(goods)]
        self.assertEqual(pdf_pages.strip_repeated(pages)[3], ["This page is about hydrogen."])

    def test_the_contents_pages_are_taken_out_and_read(self):
        document = pdf_pages.read(GUIDE)
        self.assertEqual(len(document["pages"]), 5)                      # 차례 쪽은 빈 쪽으로 남는다
        self.assertEqual(document["pages"][1]["lines"], [])
        self.assertIn("2.1", document["toc"]["numbers"])
        self.assertEqual(document["toc"]["titles"]["2.1"], ["Scope of the rules"])
        self.assertEqual(document["toc"]["titles"]["2.3"], ["Borrowed title"])
        self.assertIn("RULES FOR GOODS", document["toc"]["titles"]["2"])

    def test_footnotes_are_taken_from_the_foot_of_the_page_and_marked_in_the_text(self):
        page = pdf_pages.read(GUIDE)["pages"][2]
        self.assertEqual(page["notes"], [(1, "Source: the test regulation.")])
        self.assertIn("a simple good[1] and", page["lines"][-1])

    def test_a_number_at_the_foot_without_a_mark_in_the_text_is_left_alone(self):
        lines = ["A table follows.", "", "1", "", "First row of the table"]
        self.assertEqual(pdf_pages.take_notes(lines, 1), (lines, [], 1))

    def test_units_formulas_and_decimals_are_not_footnote_marks(self):
        mark = pdf_pages._reference(2)
        for text in ("10 m2 of area", "2 tCO2 per tonne", "a factor of 0.2 applies", "in 2022 and later"):
            self.assertIsNone(mark.search(text), text)
        for text in ("the period2 ends", "see the BREF2 documents", "(Regulation 2019/331)2", "as defined.2 Next"):
            self.assertIsNotNone(mark.search(text), text)


class BlocksTest(unittest.TestCase):
    def test_a_short_line_that_ends_a_sentence_ends_the_paragraph(self):
        full = "This sentence is long enough to fill the line and then it stops right at the margin."
        lines = [full, "A short end.", "Another paragraph begins here and", "ends."]
        self.assertEqual(pdf_blocks.blocks(lines, 90), [f"{full} A short end.", "Another paragraph begins here and ends."])

    def test_bullets_on_their_own_line_join_the_item_and_semicolons_split_items(self):
        lines = ["•", "", "First item;", "", "•", "", "Second item.", "", "has a long first part;", "has a second part."]
        self.assertEqual(pdf_blocks.blocks(lines, 90), ["• First item;", "• Second item.", "has a long first part;", "has a second part."])

    def test_hyphenated_line_ends_join_without_a_space(self):
        self.assertEqual(pdf_blocks.joined(["explained in a non-", "legislative language"]), "explained in a non-legislative language")

    def test_a_short_heading_is_split_from_the_text_but_a_capital_title_stays_whole(self):
        self.assertEqual(pdf_blocks.blocks(["Presentation of numbers", "To align with other documents, numbers are written this way."], 90),
                         ["Presentation of numbers", "To align with other documents, numbers are written this way."])
        self.assertEqual(pdf_blocks.blocks(["GUIDANCE DOCUMENT 9: SECTOR", "DOCUMENT ON A TEST"], 90), ["GUIDANCE DOCUMENT 9: SECTOR DOCUMENT ON A TEST"])


class SegmentTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parts = guide_segment.parts(GUIDE)
        cls.by_id = {part["id"]: part for part in cls.parts}

    def test_headings_follow_one_another(self):
        self.assertTrue(guide_segment.follows(None, (1,)))
        self.assertTrue(guide_segment.follows((2, 3, 3), (2, 3, 4)))
        self.assertTrue(guide_segment.follows((2, 3, 3), (3,)))
        self.assertTrue(guide_segment.follows((2, 2), (2, 3, 1)))       # 제목 하나를 놓친 경우
        self.assertFalse(guide_segment.follows((2, 3, 3), (4,)))
        self.assertFalse(guide_segment.follows((2, 3), (2, 3)))

    def test_the_document_is_cut_at_its_headings(self):
        self.assertEqual([part["id"] for part in self.parts], ["cover", "sec-1", "sec-1-1", "sec-2", "sec-2-1", "sec-2-2", "sec-2-3", "annex-a"])
        self.assertEqual(self.by_id["sec-2"]["title"], "RULES FOR GOODS")
        self.assertEqual(self.by_id["sec-2-1"]["title"], "Scope of the rules")
        self.assertEqual(self.by_id["sec-2-2"]["title"], "Worked example.")
        self.assertEqual([self.by_id[key]["level"] for key in ("sec-1", "sec-1-1", "annex-a")], [1, 2, 1])
        self.assertEqual(guide_segment.label_ko(self.by_id["annex-a"]), "부속서 A")

    def test_a_number_in_a_table_and_a_number_out_of_order_are_not_headings(self):
        self.assertEqual(self.by_id["sec-2-1"]["blocks"], ["The rules apply to goods. See the table:", "Goods", "3", "Steel"])
        self.assertIn("4.5. This line starts with a number that is not next in order.", self.by_id["sec-2-2"]["blocks"])

    def test_a_lost_title_is_borrowed_from_the_contents(self):
        self.assertEqual(self.by_id["sec-2-3"]["title"], "Borrowed title")
        self.assertEqual(self.by_id["sec-2-3"]["blocks"], ["the text under a heading whose title was lost starts in lower case."])

    def test_paragraphs_run_across_pages_and_footnotes_go_to_their_section(self):
        blocks = self.by_id["sec-1-1"]["blocks"]
        self.assertIn("Hydrogen is a simple good[1] and it stays simple across the page break because the sentence continues here with a lowercase word.", blocks)
        self.assertEqual(blocks[-1], "[1] Source: the test regulation.")
        self.assertEqual(blocks[2:4], ["• The first item of the list;", "• The second item of the list."])

    def test_the_cover_keeps_the_title_and_the_disclaimer(self):
        self.assertEqual(self.by_id["cover"]["blocks"][-1], "Disclaimer: This guidance document is not legally binding.")

    def test_questions_are_headings_and_list_items_are_not(self):
        found = guide_segment.parts(QUESTIONS)
        self.assertEqual([part["id"] for part in found], ["cover", "sec-1", "sec-1-1", "sec-1-2"])
        self.assertEqual(found[2]["title"], "What must importers do before they bring goods into the customs territory?")
        self.assertEqual(found[3]["blocks"][-1], "3. Once the payment is completed, the certificates are available.")


class PlanTest(unittest.TestCase):
    DOCUMENTS = [({"id": "a1", "group": "act"}, []), ({"id": "a2", "group": "act"}, []),
                 ({"id": "g1", "group": "guide", "turn": 2}, []), ({"id": "g2", "group": "guide", "turn": 1}, [])]

    def order(self, **settings):
        return [act["id"] for act, _ in plan.ordered(self.DOCUMENTS, settings)]

    def test_documents_come_in_the_order_of_the_plan(self):
        self.assertEqual(self.order(groups=["guide", "act"]), ["g2", "g1", "a1", "a2"])     # 갈래의 차례, 갈래 안에서는 turn
        self.assertEqual(self.order(groups=["guide", "act"], first=["a2", "g1"]), ["a2", "g1", "g2", "a1"])
        self.assertEqual(self.order(groups=["guide"]), ["g2", "g1"])
        self.assertEqual(self.order(groups=[], first=["a1"]), ["a1"])
        self.assertEqual(self.order(groups=[]), [])


class UnifyTest(unittest.TestCase):
    def test_glossary_words_get_the_preferred_spacing(self):
        from tools.laws import terms
        source = "Direct emissions from the production process are attributed."
        self.assertEqual(terms.unify(source, "생산 공정의 직접 배출량을 귀속한다."), "생산공정의 직접배출량을 귀속한다.")
        self.assertEqual(terms.unify(source, "생산공정의 직접배출량을 귀속한다."), "생산공정의 직접배출량을 귀속한다.")
        self.assertEqual(terms.unify("No such terms here.", "직접 배출량"), "직접 배출량")  # 원문에 그 낱말이 없으면 건드리지 않는다


class RepositoryTest(unittest.TestCase):
    """저장소에 받아 둔 문서로 본다."""

    def test_every_listed_document_is_found_and_cut_along_its_contents(self):
        self.assertEqual(guides.missing(), [])
        for document in guides.documents():
            text = pathlib.Path(document["path"]).read_text(encoding="utf-8")
            listed = {number for number in pdf_pages.read(text)["toc"]["numbers"] if "." in number}
            found = {part["label"] for part in guide_segment.parts(text) if part["kind"] == "section"}
            self.assertGreaterEqual(len(listed & found), 0.9 * len(listed), document["id"])
        self.assertEqual(laws_health.problems(today="2026-11-12"), [])

    def test_each_runner_takes_only_its_own_documents(self):
        groups = {document["id"]: document["group"] for document in corpus.documents()}
        for name, settings in plan.runners().items():
            picked, _ = todo.pick(3000, runner=name)
            allowed = set(settings.get("groups", []))
            self.assertTrue(all(groups[block["act"]] in allowed or block["act"] in settings.get("first", []) for block in picked), name)
            if not allowed and not settings.get("first"):
                self.assertEqual(picked, [], name)
        with self.assertRaises(KeyError):
            plan.runner("nobody")

    def test_site_data_carries_the_guides_and_their_own_search_file(self):
        folder = tempfile.mkdtemp()
        try:
            build.write(folder)
            index = json.loads((pathlib.Path(folder) / "laws/index.json").read_text(encoding="utf-8"))
            listed = [act for act in index["acts"] if act["group"] == "guide"]
            self.assertEqual([act["id"] for act in listed], [document["id"] for document in guides.documents()])
            self.assertTrue(all(act["sections"] and act["toc"] and act["official"] for act in listed))
            body = json.loads((pathlib.Path(folder) / f"laws/{listed[0]['id']}.json").read_text(encoding="utf-8"))
            self.assertEqual(body["parts"][0]["kind"], "cover")
            self.assertTrue(body["notice"].startswith("Disclaimer:"))
            rows = json.loads((pathlib.Path(folder) / "laws/search-guides.json").read_text(encoding="utf-8"))["rows"]
            self.assertTrue(rows and {row["a"] for row in rows} <= {act["id"] for act in listed})
            acts = json.loads((pathlib.Path(folder) / "laws/search.json").read_text(encoding="utf-8"))["rows"]
            self.assertFalse({row["a"] for row in acts} & {act["id"] for act in listed})
        finally:
            shutil.rmtree(folder)

    def test_progress_is_summed_for_each_group(self):
        self.assertTrue(status.summary(group="guide").startswith("가이던스 번역: 원문 "))
        self.assertTrue(status.summary().startswith("규정 번역: 원문 "))


class TrialTest(unittest.TestCase):
    SOURCE = "The declarant shall submit 3 reports by 31 May 2027."

    def setUp(self):
        self.key = store.key(self.SOURCE)
        self.known = {self.key: ("act", self.SOURCE)}

    def test_a_round_keeps_what_passes_and_remembers_the_first_rejection(self):
        record = trial.load("no-such-trial")
        count, rejected, _ = trial.take(record, {self.key: "신고인은 보고서를 제출한다."}, self.known, "model-a", "2026-11-12T15:00:00+09:00")
        self.assertEqual((count, [key for key, _ in rejected]), (0, [self.key]))
        count, rejected, _ = trial.take(record, {self.key: "신고인은 2027년 5월 31일까지 보고서 3건을 제출한다."}, self.known, "model-a", "2026-11-12T15:05:00+09:00")
        self.assertEqual((count, rejected), (1, []))
        self.assertEqual((len(record["rounds"]), list(record["firstRejected"]), record["model"], record["startedAt"]),
                         (2, [self.key], "model-a", "2026-11-12T15:00:00+09:00"))

    def test_the_next_batch_ignores_what_is_already_published(self):
        asked = {"name": "no-such-trial", "act": "32023R0956", "limit": 4000}
        picked, left = trial.next_batch(asked, trial.load("no-such-trial"))
        self.assertTrue(picked and all(block["act"] == "32023R0956" for block in picked))
        self.assertTrue(any(block["key"] in store.load_all() for block in picked))   # 이미 실린 문단도 다시 준다
        self.assertEqual(left["blocks"], 0)


class WordingTest(unittest.TestCase):
    """번역 실행들이 정해 두는 낱말."""

    def setUp(self):
        self.folder = tempfile.mkdtemp()
        self.kept, wording.SOURCE = wording.SOURCE, str(pathlib.Path(self.folder) / "terms.json")

    def tearDown(self):
        wording.SOURCE = self.kept
        shutil.rmtree(self.folder)

    def test_new_words_are_kept_and_known_or_odd_ones_are_skipped(self):
        entries = [{"en": "ladle furnace", "ko": "래들로"}, {"en": "installation", "ko": "설비"}, {"en": "kiln dust", "ko": "kiln dust"},
                   {"en": "Ladle Furnace", "ko": "레이들로"}]
        added, skipped = wording.add(entries, "guide-5e", "2026-11-12")
        self.assertEqual((added, skipped), (["ladle furnace"], ["installation", "kiln dust", "Ladle Furnace"]))  # 용어집에 있는 것, 국문이 아닌 것, 이미 적힌 것
        self.assertEqual(wording.load(), [{"en": "ladle furnace", "ko": "래들로", "from": "guide-5e", "added": "2026-11-12"}])

    def test_words_are_found_in_a_text_in_plural_too(self):
        wording.add([{"en": "ladle furnace", "ko": "래들로"}], "guide-5e", "2026-11-12")
        self.assertEqual(wording.found("The number of Ladle Furnaces in the plant."), [{"en": "ladle furnace", "ko": "래들로"}])
        self.assertEqual(wording.found("No such words here."), [])


if __name__ == "__main__":
    unittest.main()
