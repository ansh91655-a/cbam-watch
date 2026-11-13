"""안내 문서(PDF에서 뽑은 글): 쪽 읽기, 문단 묶기, 절 나누기, 문서 목록, 번역 실행의 갈래, 견주기 시험, 검수, 사이트 자료."""
import datetime
import json
import pathlib
import random
import shutil
import subprocess
import tempfile
import unittest
import unittest.mock

from tools.laws import build, corpus, guide_segment, guides, lock, pdf_blocks, pdf_pages, plan, review, spoil, status, store, todo, trial, verify, wording
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


# 부속서 번호가 로마 숫자이고, 제목이 따옴표로 시작하고, 표의 칸에 "Annex II"가 나오는 문서
ROMAN = "\f".join(["""A TEST GUIDANCE
""", """CONTENTS
1

FIRST CHAPTER

2

1.1

“Averaging” of data

2

ANNEX I - INTERNAL DOCUMENTS

3

ANNEX II – TEAMS

3
""", """1

FIRST CHAPTER

The chapter starts here with a full sentence that runs on.

1.1. “Averaging” of data
Averaging is explained in this section.
The table refers to

Annex II

Team rules

and the text goes on after the table cell.
""", """ANNEX I - INTERNAL DOCUMENTS
The documents are listed here.
""", """ANNEX II – TEAMS
The teams are described here.
"""])

# 번호 줄 둘이 잇달아 오고("2" / "2.1"), 제목 줄이 번호 줄의 앞으로 밀린("Chemicals sector" / "2.2") 문서
SHIFTED = "\f".join(["""A TEST DOCUMENT
""", """CONTENTS
1

OPENING

2

2

GOODS AND ROUTES

2

2.1

Foreword to the sections

2

2.2

Chemicals sector

3
""", """1

OPENING

The opening says what the document is about.

2
2.1

GOODS AND ROUTES
Foreword to the sections

The foreword explains the sections that follow in this chapter.

Chemicals sector

2.2

The textbox below points to the rules,
which are relevant for this sector.
"""])

# 차례가 번호의 단과 제목의 단으로 나뉜 문서(등록부 안내서의 꼴)
COLUMNS = "\f".join(["""A MANUAL
""", """Table of contents
1.
1.1
1.2
1.3
2.
2.1

INTRODUCTION ............................................ 3
Purpose ................................................. 3
Audience ................................................ 3
Structure................................................ 3
USING THE SYSTEM ........................................ 4
Access .................................................. 4

List of tables
Table 1: Documents ...................................... 3
""", """1 INTRODUCTION
1.1 PURPOSE
The purpose is to explain.

1.2

AUDIENCE

The audience includes:

1.3

•

Operators;

STRUCTURE

The document has two chapters.
""", """2 USING THE SYSTEM
2.1 ACCESS
Access is requested online.
"""])

# 차례가 없는 문서. 쪽 아래의 각주 번호("3")가 제목처럼 보인다
BARE = """Synopsis report on a test

1.

SUMMARY

The summary is short. It says what the report found in the answers.

2.

ANALYSIS

2.1 Co-ordinated responses
The position paper was attached without change by five other respondents and it was long.
More text follows here.

3

Union of Test Industries

The analysis ends here.
"""

LOOSE = """Privacy statement

1. Introduction
The Commission is committed to protect your personal data and to respect your privacy at all times.

2. Why do we process your data?
2.1. Controllership
The Commission acts as controller.

2.2. Purpose of the processing operation:
The purpose is the management of the registry.
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

    def test_footnotes_whose_numbers_come_after_their_text_are_read_too(self):
        lines = ["Questions on CBAM1 and electricity are answered here in a long line of text.", "The code (UCC-DA)2 applies.", "",
                 "Regulation (EU) 2023/956, as amended.", "2", "Delegated Regulation (EU) 2015/2446.", "1"]
        body, notes, following = pdf_pages.take_notes(lines, 1)
        self.assertEqual(notes, [(1, "Regulation (EU) 2023/956, as amended."), (2, "Delegated Regulation (EU) 2015/2446.")])
        self.assertEqual(body, ["Questions on CBAM[1] and electricity are answered here in a long line of text.", "The code (UCC-DA)[2] applies."])
        self.assertEqual(following, 3)

    def test_a_mark_stuck_to_an_act_number_is_cut_off_the_number(self):
        lines = ["See Article 321 of Regulation (EU) 2015/24474) and the code UCC3) for the rule in a long line.", "",
                 "Regulation (EU) No 952/2013.", "4", "Implementing Regulation (EU) 2015/2447.", "3"]
        body, notes, _ = pdf_pages.take_notes(lines, 3)
        self.assertEqual([number for number, _ in notes], [3, 4])
        self.assertEqual(body, ["See Article 321 of Regulation (EU) 2015/2447[4]) and the code UCC[3]) for the rule in a long line."])

    def test_a_footnote_right_under_a_sentence_that_runs_on_is_still_a_footnote(self):
        lines = ["See the “O3CI” Module2 of the registry and write the plan, i.e. the", "2", "", "O3CI = Operators of 3rd country Installations", "",
                 "3", "", "A second note."]
        body, notes, following = pdf_pages.take_notes(lines, 2)
        self.assertEqual(notes, [(2, "O3CI = Operators of 3rd country Installations"), (3, "A second note.")])
        self.assertEqual(body, ["See the “O3CI” Module[2] of the registry and write the plan, i.e. the"])
        self.assertEqual(following, 4)
        table = ["The table has these rows and the text goes on to the next page with the", "2", "", "Steel"]
        self.assertEqual(pdf_pages.take_notes(table, 2), (table, [], 2))  # 본문에 그 번호가 붙은 자리가 없으면 각주가 아니다

    def test_a_section_number_is_not_marked_when_the_note_sits_on_a_word(self):
        lines = ["• Annex II, Section D – Electricity, sub-sections D.1 to D.2", "Note: The proposal1 of 17 December 2025 changes the rules.", "", "1", "", "Proposal for a Regulation."]
        body, notes, _ = pdf_pages.take_notes(lines, 1)
        self.assertEqual(notes, [(1, "Proposal for a Regulation.")])
        self.assertEqual(body, ["• Annex II, Section D – Electricity, sub-sections D.1 to D.2", "Note: The proposal[1] of 17 December 2025 changes the rules."])
        self.assertIsNone(pdf_pages._reference(7).search("sub-section B.7. Requirements for determining emissions"))

    def test_a_page_that_only_ends_with_a_number_keeps_its_text(self):
        lines = ["1.4. A heading on this page", "The text of the page ends with a table.", "", "1.5. Another heading", "Its text.", "1"]
        self.assertEqual(pdf_pages.take_notes(lines, 1), (lines, [], 1))  # 제목이 든 구역은 각주가 아니다

    def test_a_footer_caught_in_the_middle_of_a_page_is_dropped_too(self):
        goods = ["cement", "steel", "aluminium", "hydrogen", "fertilisers", "electricity", "iron", "clinker"]
        pages = [["Manual of the portal", f"This page is about {name}.", "Manual footer – version 3.00 EN", f"Page {number + 1} / 8"] for number, name in enumerate(goods)]
        pages[2] = pages[2][:3] + ["A note under the footer.", pages[2][3]]
        self.assertEqual(pdf_pages.strip_repeated(pages)[2], ["This page is about aluminium.", "A note under the footer."])
        self.assertEqual(pdf_pages.strip_repeated(pages)[5], ["This page is about electricity."])

    def test_a_line_that_is_only_an_arrow_is_dropped(self):
        self.assertEqual(pdf_pages.split("A LEAFLET\n>\n\nWhat is it?"), [["A LEAFLET", "", "What is it?"]])

    def test_a_contents_page_in_two_columns_is_paired_in_order(self):
        toc = pdf_pages.read(COLUMNS)["toc"]
        self.assertEqual(toc["titles"]["1.3"], ["Structure"])
        self.assertEqual(toc["titles"]["2"], ["USING THE SYSTEM"])
        self.assertEqual(toc["paired"], {"1", "1.1", "1.2", "1.3", "2", "2.1"})
        self.assertEqual(pdf_pages.toc_columns(["1.", "1.1", "Only one title ..... 3"]), {})  # 수가 맞지 않으면 짝짓지 않는다

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


class OutlineTest(unittest.TestCase):
    """문서마다 다른 꼴: 로마 숫자 부속서, 자리가 밀린 제목, 단이 나뉜 차례, 차례가 없는 문서, 제목을 찾지 않는 문서."""

    def test_annexes_with_roman_numbers_are_cut_and_a_table_cell_is_not(self):
        found = guide_segment.parts(ROMAN)
        self.assertEqual([part["id"] for part in found], ["cover", "sec-1", "sec-1-1", "annex-i", "annex-ii"])
        self.assertEqual([part["title"] for part in found[2:]], ["“Averaging” of data", "INTERNAL DOCUMENTS", "TEAMS"])
        self.assertIn("Annex II", found[2]["blocks"])
        self.assertEqual(guide_segment.label_ko(found[4]), "부속서 II")

    def test_two_number_lines_in_a_row_and_a_title_above_its_number_are_put_right(self):
        found = {part["id"]: part for part in guide_segment.parts(SHIFTED)}
        self.assertEqual(list(found), ["cover", "sec-1", "sec-2", "sec-2-1", "sec-2-2"])
        self.assertEqual([found[key]["title"] for key in ("sec-2", "sec-2-1", "sec-2-2")], ["GOODS AND ROUTES", "Foreword to the sections", "Chemicals sector"])
        self.assertEqual(found["sec-2-1"]["blocks"], ["The foreword explains the sections that follow in this chapter."])
        self.assertEqual(found["sec-2-2"]["blocks"], ["The textbox below points to the rules, which are relevant for this sector."])

    def test_a_title_lost_among_list_items_is_taken_from_the_paired_contents(self):
        found = {part["id"]: part for part in guide_segment.parts(COLUMNS)}
        self.assertEqual(list(found), ["cover", "sec-1", "sec-1-1", "sec-1-2", "sec-1-3", "sec-2", "sec-2-1"])
        self.assertEqual(found["sec-1-3"]["title"], "Structure")
        self.assertEqual(found["sec-1-3"]["blocks"], ["• Operators;", "The document has two chapters."])  # 본문에 따로 적힌 제목 줄은 지운다

    def test_without_contents_a_footnote_number_is_not_a_heading(self):
        found = guide_segment.parts(BARE)
        self.assertEqual([part["id"] for part in found], ["cover", "sec-1", "sec-2", "sec-2-1"])
        self.assertEqual(found[3]["title"], "Co-ordinated responses")
        self.assertEqual(found[3]["blocks"][-3:], ["3", "Union of Test Industries", "The analysis ends here."])

    def test_a_document_can_be_kept_whole_or_read_loosely(self):
        whole = guide_segment.parts(BARE, "none")
        self.assertEqual([(part["id"], part["kind"], part["label"], part["title"]) for part in whole], [(guide_segment.BODY_ID, "section", "본문", "")])
        self.assertEqual(whole[0]["blocks"][0], "Synopsis report on a test")
        self.assertEqual(guide_segment.label_ko(whole[0]), "본문")
        self.assertEqual([part["id"] for part in guide_segment.parts(LOOSE)], ["cover"])
        loose = guide_segment.parts(LOOSE, "loose")
        self.assertEqual([part["id"] for part in loose], ["cover", "sec-1", "sec-2", "sec-2-1", "sec-2-2"])
        self.assertEqual(loose[4]["title"], "Purpose of the processing operation")
        with self.assertRaises(ValueError):
            guide_segment.parts(BARE, "sometimes")


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

    def test_the_earlier_version_of_a_document_follows_it_when_it_comes_first(self):
        documents = self.DOCUMENTS + [({"id": "a2-was-20230516", "group": "act", "turn": 900, "hidden": True, "of": "a2"}, [])]
        order = lambda **settings: [act["id"] for act, _ in plan.ordered(documents, settings)]
        self.assertEqual(order(groups=["guide", "act"], first=["a2", "g1"]), ["a2", "a2-was-20230516", "g1", "g2", "a1"])  # 먼저 옮기는 문서의 앞선 판은 그 바로 뒤
        self.assertEqual(order(groups=["guide", "act"]), ["g2", "g1", "a1", "a2", "a2-was-20230516"])                       # 그 밖에는 갈래의 맨 뒤(turn)
        self.assertEqual(order(groups=[], first=["a1"]), ["a1"])


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
            self.assertIn(document["group"], guides.GROUPS, document["id"])
            found = corpus.read(document)
            self.assertTrue(found, document["id"])
            if document["outline"] == "none":
                self.assertEqual([part["id"] for part in found], [guide_segment.BODY_ID], document["id"])
                continue
            text = pathlib.Path(document["path"]).read_text(encoding="utf-8")
            listed = {number for number in pdf_pages.read(text)["toc"]["numbers"] if "." in number}
            cut = {part["label"] for part in found if part["kind"] == "section"}
            self.assertGreaterEqual(len(listed & cut), 0.9 * len(listed), document["id"])
            self.assertFalse([part["title"] for part in found if len(part["title"]) > guide_segment.TITLE_MAX and not part["title"].endswith("?")], document["id"])
        self.assertEqual(len({document["id"] for document in guides.documents()}), len(guides.documents()))
        self.assertEqual(laws_health._outline_problems(), [])  # 검사에 걸려 남은 문단 같은 운영의 일은 여기서 보지 않는다(실행 확인과 보고가 알린다)

    def test_each_runner_takes_only_its_own_documents(self):
        # 앞선 판에만 있는 문단을 담은 숨은 문서(…-was-…)도 본디 문서의 갈래를 따라 그 실행이 옮긴다
        groups = {document["id"]: document["group"] for document, _ in corpus.everything(history=True)[0]}
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
            listed = [act for act in index["acts"] if act["group"] != "act"]
            self.assertEqual([act["id"] for act in listed], [document["id"] for document in guides.documents()])
            self.assertEqual({act["group"] for act in listed}, set(guides.GROUPS))
            self.assertTrue(all(act["sections"] and act["toc"] and act["official"] for act in listed))
            self.assertTrue(any(act["remark"] for act in listed))  # 전환기간용 자료 같은 알림이 실린다
            body = json.loads((pathlib.Path(folder) / f"laws/{listed[0]['id']}.json").read_text(encoding="utf-8"))
            self.assertEqual(body["parts"][0]["kind"], "cover")
            self.assertTrue(body["notice"].startswith("Disclaimer:"))
            self.assertNotIn("checked", body)  # 검수 표시는 사이트에 싣지 않는다
            rows = json.loads((pathlib.Path(folder) / "laws/search-guides.json").read_text(encoding="utf-8"))["rows"]
            self.assertTrue(rows and {row["a"] for row in rows} <= {act["id"] for act in listed})
            acts = json.loads((pathlib.Path(folder) / "laws/search.json").read_text(encoding="utf-8"))["rows"]
            self.assertFalse({row["a"] for row in acts} & {act["id"] for act in listed})
        finally:
            shutil.rmtree(folder)

    def test_progress_is_summed_for_each_group(self):
        self.assertTrue(status.summary(group="guide").startswith("가이던스 번역: 원문 "))
        self.assertTrue(status.summary(group="manual").startswith("등록부 안내서 번역: 원문 "))
        self.assertTrue(status.summary(group="paper").startswith("보고서·안내 자료 번역: 원문 "))
        self.assertTrue(status.summary().startswith("규정 번역: 원문 "))
        self.assertEqual(set(status.NAMES), {"act", *guides.GROUPS})
        self.assertTrue(status.whole().startswith("전체: 서로 다른 문단 "))


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


class ReviewTest(unittest.TestCase):
    """표본 검토: 번역 자료와 검토 기록을 임시 폴더에 두고 본다."""

    def setUp(self):
        self.folder = tempfile.mkdtemp()
        self.kept = (store.FOLDER, review.LOG)
        store.FOLDER, review.LOG = self.folder, str(pathlib.Path(self.folder) / "reviews.log.json")
        document = guides.documents()[0]
        self.act = document["id"]
        self.text = next(text for part in corpus.read(document) for text in part["blocks"] if len(text) >= review.MIN_CHARS)
        self.key = store.key(self.text)
        store.save(self.act, {self.key: "시험용 번역"}, "2026-11-10")

    def tearDown(self):
        store.FOLDER, review.LOG = self.kept
        shutil.rmtree(self.folder)

    def test_the_sample_comes_from_documents_translated_lately(self):
        self.assertEqual(review.sample(5, day="2026-11-12"), [{"key": self.key, "act": self.act, "part": review.sample(5, day="2026-11-12")[0]["part"],
                                                              "source": self.text, "korean": "시험용 번역"}])
        self.assertEqual(review.sample(5, day="2026-12-12"), [])  # 번역이 더해진 지 오래된 문서는 뽑지 않는다

    def test_a_dropped_translation_is_gone_and_its_reason_follows_the_paragraph(self):
        self.assertEqual(review.drop(self.key, "의무가 권고로 옮겨짐", "2026-11-16"), [self.act])
        self.assertEqual(store.load(self.act), {})
        self.assertEqual(review.remarks(), {self.key: "의무가 권고로 옮겨짐"})
        picked, left = todo.pick(10**6, self.act)
        self.assertEqual(todo.answer([block for block in picked if block["key"] == self.key], left)["remarks"], {self.key: "의무가 권고로 옮겨짐"})
        self.assertEqual(review.drop("000000000000", "없는 열쇠"), [])


class FinishTest(unittest.TestCase):
    def test_sentence_endings_get_one_shape(self):
        from tools.laws import finish
        self.assertEqual(finish.finish("‘기본값’이란 제품의 내재배출량을 나타내는 값을 말한다"), "‘기본값’이란 제품의 내재배출량을 나타내는 값을 말한다.")
        self.assertEqual(finish.finish("기준은 다음과 같다:"), "기준은 다음과 같다.")
        self.assertEqual(finish.finish("다음을 포함하여야 한다; "), "다음을 포함하여야 한다.")
        for kept in ("이미 마침표가 있다.", "(a) 대륙붕에서 생산된 전력", "예:", "CBAM 인증서의 제출", "언제부터 적용되는가?"):
            self.assertEqual(finish.finish(kept), kept)

    def test_endings_are_set_when_a_translation_is_stored(self):
        from tools.laws import apply
        source = "The declarant shall submit 3 reports by 31 May 2027;"
        accepted, rejected, _ = apply.sort({store.key(source): "신고인은 2027년 5월 31일까지 보고서 3건을 제출하여야 한다"}, {store.key(source): ("act", source)})
        self.assertEqual((accepted, rejected), ({"act": {store.key(source): "신고인은 2027년 5월 31일까지 보고서 3건을 제출하여야 한다."}}, []))


class CheckedTest(unittest.TestCase):
    """번역 자료의 검수 표시."""

    def setUp(self):
        self.folder, self.kept = tempfile.mkdtemp(), store.FOLDER
        store.FOLDER = self.folder

    def tearDown(self):
        store.FOLDER = self.kept
        shutil.rmtree(self.folder)

    def test_marks_stay_until_the_translation_changes(self):
        store.save("x", {"a": "가", "b": "나"}, "2026-11-10")
        self.assertEqual(store.mark("x", ["a", "none"]), 1)
        self.assertEqual(store.load_checked("x"), {"a"})
        self.assertEqual(json.loads(pathlib.Path(store.path_of("x")).read_text(encoding="utf-8"))["updated"], "2026-11-10")  # 검수는 번역이 더해진 날을 바꾸지 않는다
        store.save("x", {"a": "가", "b": "다", "c": "라"}, "2026-11-12")
        self.assertEqual(store.load_checked("x"), {"a"})
        store.save("x", {"a": "가를 고침", "b": "다"}, "2026-11-13")
        self.assertEqual(store.load_checked("x"), set())  # 번역이 바뀐 문단은 다시 견줘 보게 한다
        self.assertEqual(store.checked_all(), set())


class SpoilTest(unittest.TestCase):
    def test_a_translation_is_changed_into_something_wrong(self):
        text = "운영자는 매년 배출량 보고서를 제출하여야 한다. 관할당국은 이를 검토할 수 있다."
        found = spoil.choices(text)
        self.assertIn(("운영자는 매년 배출량 보고서를 제출할 수 있다. 관할당국은 이를 검토할 수 있다.", "flip"), found)
        self.assertIn(("운영자는 매년 배출량 보고서를 제출하여야 한다.", "omission"), found)
        self.assertTrue(all(changed != text for changed, _ in found))
        self.assertIn(spoil.spoil(text, random.Random(1)), found)
        self.assertIn(("이 규정은 전력의 수입에는 적용된다는 점에 유의하여야 하는 경우가 있다.", "negation"),
                      spoil.choices("이 규정은 전력의 수입에는 적용되지 않는다는 점에 유의하여야 하는 경우가 있다."))

    def test_short_lines_are_left_alone(self):
        self.assertIsNone(spoil.spoil("제3장 정의", random.Random(1)))


class VerifyTest(unittest.TestCase):
    """검수: 번역 자료와 기록을 임시 폴더에 두고 본다. 원문은 저장소의 문서에서 가져온다."""
    KOREAN = "이 문단은 시험용 번역이며 운영자는 해마다 보고서를 제출하여야 한다. 관할당국은 그 보고서를 검토할 수 있다."

    def setUp(self):
        self.folder = tempfile.mkdtemp()
        self.kept = (store.FOLDER, review.LOG, verify.LOG, verify.WORK)
        store.FOLDER, review.LOG = self.folder, str(pathlib.Path(self.folder) / "reviews.log.json")
        verify.LOG, verify.WORK = str(pathlib.Path(self.folder) / "checks.log.json"), str(pathlib.Path(self.folder) / "work.json")
        document = next(document for document in guides.documents() if document["id"] == "guide-5b")
        self.act = document["id"]
        texts = []
        for part in corpus.read(document):
            for text in corpus.texts(part):
                if len(text) >= 80 and store.key(text) not in {store.key(other) for other in texts}:
                    texts.append(text)
        self.texts = texts[:24]
        self.keys = [store.key(text) for text in self.texts]
        store.save(self.act, {block_key: self.KOREAN for block_key in self.keys}, "2026-11-10")

    def tearDown(self):
        store.FOLDER, review.LOG, verify.LOG, verify.WORK = self.kept
        shutil.rmtree(self.folder)

    def batch(self):
        picked, work, left = verify.batch(10**6, seed="test")
        self.assertEqual((len(picked), left), (24, {"blocks": 0, "chars": 0}))
        return picked, work

    def test_a_batch_hides_a_few_spoiled_translations(self):
        self.assertEqual([block["key"] for block in verify.pending()], self.keys)
        picked, work = self.batch()
        self.assertEqual(len(work["canaries"]), verify.CANARY_MIN)
        self.assertEqual(sorted(work["keys"] + list(work["canaries"])), sorted(self.keys))
        for block in picked:
            self.assertEqual(block["korean"] != self.KOREAN, block["key"] in work["canaries"])
        self.assertEqual(store.load(self.act), {block_key: self.KOREAN for block_key in self.keys})  # 바꾼 번역은 번역 자료에 들어가지 않는다
        small, work, _ = verify.batch(len(self.texts[0]) + 1, seed="test")
        self.assertEqual((len(small), work["canaries"]), (1, {}))  # 작은 묶음에는 섞지 않는다

    def test_caught_canaries_let_the_marks_and_the_drops_through(self):
        _, work = self.batch()
        wrong = {**{block_key: "뜻이 뒤집힘" for block_key in work["canaries"]}, work["keys"][0]: "빠진 문장이 있음", "ffffffffffff": "모르는 열쇠"}
        done = verify.settle(wrong, work, "2026-11-12")
        self.assertEqual((done["outcome"], done["checked"], done["dropped"], done["caught"], done["unknown"]), ("applied", 20, 1, 3, ["ffffffffffff"]))
        self.assertEqual(store.load_checked(self.act), set(work["keys"][1:]))
        self.assertNotIn(work["keys"][0], store.load(self.act))
        self.assertEqual(review.remarks(), {work["keys"][0]: "빠진 문장이 있음"})
        self.assertEqual(sorted(block["key"] for block in verify.pending()), sorted(work["canaries"]))  # 바꿔 보였던 문단은 다음에 제 번역으로 다시 읽는다
        self.assertEqual(verify.progress()["checked"], 20)
        self.assertTrue(verify.summary().startswith("검수: 옮긴 문단 23개 가운데 20개(87%)를 원문과 견줌, 일부러 바꾼 번역 3개 가운데 3개를 잡음"))

    def test_missed_canaries_throw_the_batch_away(self):
        _, work = self.batch()
        done = verify.settle({work["keys"][0]: "틀림"}, work, "2026-11-12")
        self.assertEqual((done["outcome"], done["checked"], done["dropped"]), ("discarded", 0, 0))
        self.assertEqual(store.load_checked(self.act), set())
        self.assertEqual(len(store.load(self.act)), 24)
        self.assertEqual(json.loads(pathlib.Path(verify.LOG).read_text(encoding="utf-8"))["days"][0]["discarded"], 1)

    def test_a_batch_called_wrong_too_often_is_held_back(self):
        _, work = self.batch()
        wrong = {block_key: "틀림" for block_key in list(work["canaries"]) + work["keys"][:10]}
        done = verify.settle(wrong, work, "2026-11-12")
        self.assertEqual((done["outcome"], done["dropped"]), ("held", 0))
        self.assertEqual(len(store.load(self.act)), 24)

    def test_a_paragraph_dropped_twice_is_left_for_a_person(self):
        _, work = self.batch()
        stubborn = work["keys"][0]
        pathlib.Path(review.LOG).write_text(json.dumps({"reviews": [{"day": "2026-11-10", "key": stubborn, "act": self.act, "why": "하나"},
                                                                    {"day": "2026-11-11", "key": stubborn, "act": self.act, "why": "둘"}]}, ensure_ascii=False), encoding="utf-8")
        done = verify.settle({**{block_key: "뒤집힘" for block_key in work["canaries"]}, stubborn: "또 틀림"}, work, "2026-11-12")
        self.assertEqual((done["outcome"], done["dropped"], done["disputed"], done["checked"]), ("applied", 0, 1, 21))
        self.assertIn(stubborn, store.load(self.act))
        self.assertEqual(json.loads(pathlib.Path(verify.LOG).read_text(encoding="utf-8"))["disputed"], [{"day": "2026-11-12", "key": stubborn, "why": "또 틀림"}])


@unittest.skipUnless(shutil.which("git"), "git이 없으면 자물쇠는 시험하지 않는다")
class LockTest(unittest.TestCase):
    """번역 실행의 자물쇠: 저장소 하나(origin)를 두 실행(a, b)이 받아 놓고 잡고 푼다."""

    def setUp(self):
        self.base = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.base, ignore_errors=True)
        self.git(self.base, "init", "-q", "--bare", "-b", "main", "origin.git")
        self.git(self.base, "clone", "-q", "origin.git", "a")
        (self.base / "a" / "data" / "laws-ko").mkdir(parents=True)
        (self.base / "a" / "data" / "laws-ko" / "x.json").write_text("{}\n", encoding="utf-8")
        self.git(self.base / "a", "add", "-A")
        self.git(self.base / "a", "commit", "-q", "-m", "처음", env_date="2026-11-12T10:00:00+09:00")
        self.git(self.base / "a", "push", "-q", "origin", "HEAD:main")
        self.git(self.base, "clone", "-q", "origin.git", "b")
        self.a, self.b = str(self.base / "a"), str(self.base / "b")
        self.noon = datetime.datetime(2026, 11, 12, 12, 0, tzinfo=lock.KST)

    def git(self, where, *args, env_date=None):
        env = None
        if env_date:
            import os
            env = {**os.environ, "GIT_AUTHOR_DATE": env_date, "GIT_COMMITTER_DATE": env_date}
        return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.com", *args], cwd=where, capture_output=True, text=True, check=True, env=env)

    def later(self, minutes):
        return self.noon + datetime.timedelta(minutes=minutes)

    def test_only_one_run_holds_the_lock_and_only_its_holder_releases_it(self):
        self.assertEqual(lock.take("run-a", self.a, at=self.noon), ("taken", ""))
        self.assertEqual(lock.take("run-b", self.b, at=self.later(5)), ("busy", "run-a"))   # 받아 보니 a가 잡고 있다
        self.assertEqual(lock.release("run-b", self.b), "not-mine")                          # 남의 것은 풀지 않는다
        self.assertEqual(lock.read(self.b)["run"], "run-a")
        self.assertEqual(lock.release("run-a", self.a), "released")
        self.assertEqual(lock.take("run-b", self.b, at=self.later(6)), ("taken", ""))        # 풀린 뒤에는 바로 잡는다
        self.assertEqual(lock.read(self.b), {"run": "run-b", "since": "2026-11-12T12:06:00+09:00"})

    def test_a_lock_left_by_a_stopped_run_is_taken_over(self):
        lock.take("run-a", self.a, at=self.noon)
        self.assertEqual(lock.take("run-b", self.b, at=self.later(lock.STALE_MINUTES - 1))[0], "busy")
        self.assertEqual(lock.take("run-b", self.b, at=self.later(lock.STALE_MINUTES + 1)), ("taken", ""))
        self.assertEqual(lock.release("run-a", self.a), "not-mine")                          # 넘겨받은 뒤에 옛 실행이 풀려 해도 그대로다
        self.assertEqual(lock.holder({"run": "x", "since": "엉뚱한 값"}, self.noon), "")
        self.assertEqual(lock.holder(None, self.noon), "")

    def test_an_old_lock_still_counts_while_translations_keep_arriving(self):
        lock.take("run-a", self.a, at=self.noon)
        old = self.later(lock.STALE_MINUTES + 3)
        self.assertEqual(lock.holder(lock.read(self.a), old, last_work=old.timestamp() - 60), "run-a")   # 1분 전에 번역이 올라왔다
        self.assertEqual(lock.holder(lock.read(self.a), old, last_work=old.timestamp() - lock.QUIET_SECONDS - 1), "")

    def test_when_two_runs_take_at_once_the_first_push_wins(self):
        # a가 자물쇠를 커밋하고 올리기 직전에 b가 먼저 잡는다. a의 올리기는 거절되고, a는 받아 보고 물러선다.
        seen = []
        def cut_in():
            if not seen:
                seen.append(lock.take("run-b", self.b, at=self.noon))
        self.assertEqual(lock.take("run-a", self.a, at=self.noon, between=cut_in), ("busy", "run-b"))
        self.assertEqual(seen, [("taken", "")])
        self.assertEqual(self.git(self.a, "status", "--porcelain").stdout, "")               # a에는 자기 자물쇠 커밋이 남지 않는다
        self.assertEqual(lock.read(self.a)["run"], "run-b")

    def translate(self, where, text, when):
        """번역 묶음 하나를 올린 것처럼 번역 파일을 고쳐 올린다."""
        (pathlib.Path(where) / "data" / "laws-ko" / "x.json").write_text(text, encoding="utf-8")
        self.git(where, "commit", "-q", "-am", "번역", env_date=when)
        self.git(where, "push", "-q", "origin", "HEAD:main")

    def stamp(self, where):
        self.git(where, "pull", "-q", "--rebase", "origin", "main")
        path = pathlib.Path(where) / lock.STAMP
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None

    def test_releasing_marks_the_site_for_redeploy_only_when_translations_arrived(self):
        # 번역은 묶음마다 올라오지만 사이트는 실행이 끝날 때 한 번 다시 싣는다: 풀 때 표를 고치고, 배포가 그 파일을 본다
        lock.take("run-a", self.a, at=self.noon)
        self.translate(self.a, '{"a": 1}\n', "2026-11-12T12:03:00+09:00")
        self.assertEqual(lock.release("run-a", self.a, at=self.later(9)), "released")
        self.assertEqual(self.stamp(self.b), {"run": "run-a", "at": "2026-11-12T12:09:00+09:00"})
        self.assertIsNone(lock.read(self.b))
        # 옮긴 것 없이 끝난 실행은 표를 건드리지 않는다(사이트를 다시 실을 까닭이 없다)
        lock.take("run-b", self.b, at=self.later(15))
        self.assertEqual(lock.release("run-b", self.b, at=self.later(16)), "released")
        self.assertEqual(self.stamp(self.a)["run"], "run-a")
        # 풀지 못하고 멈춘 실행이 올려 둔 번역은, 넘겨받은 실행이 풀 때 표에 담긴다
        lock.take("run-c", self.a, at=self.later(30))
        self.translate(self.a, '{"a": 2}\n', "2026-11-12T12:33:00+09:00")
        self.assertEqual(lock.take("run-d", self.b, at=self.later(30 + lock.STALE_MINUTES + 1)), ("taken", ""))
        self.assertEqual(lock.release("run-d", self.b, at=self.later(50)), "released")
        self.assertEqual(self.stamp(self.a), {"run": "run-d", "at": "2026-11-12T12:50:00+09:00"})

    def test_taking_and_releasing_leave_other_changes_alone(self):
        # 실행이 올리지 않고 남긴 변경(걸려서 둔 묶음 따위)이 있어도 잡고 풀 수 있고, 그 변경은 커밋에 섞이지 않는다
        lock.take("run-a", self.a, at=self.noon)
        self.translate(self.a, '{"a": 1}\n', "2026-11-12T12:03:00+09:00")
        left = pathlib.Path(self.a) / "data" / "laws-ko" / "x.json"
        left.write_text('{"a": "올리지 않은 것"}\n', encoding="utf-8")
        self.git(self.a, "add", "-A")                                                          # 담기까지 해 둔 변경
        self.assertEqual(lock.release("run-a", self.a, at=self.later(9)), "released")
        self.assertIn("올리지 않은 것", left.read_text(encoding="utf-8"))                        # 그대로 남아 있고
        self.git(self.b, "pull", "-q", "--rebase", "origin", "main")
        self.assertEqual((pathlib.Path(self.b) / "data" / "laws-ko" / "x.json").read_text(encoding="utf-8"), '{"a": 1}\n')  # 올라가지 않았다
        self.assertEqual(lock.take("run-a2", self.a, at=self.later(20)), ("taken", ""))
        self.git(self.b, "pull", "-q", "--rebase", "origin", "main")
        self.assertEqual((pathlib.Path(self.b) / "data" / "laws-ko" / "x.json").read_text(encoding="utf-8"), '{"a": 1}\n')

    def test_the_site_is_redeployed_when_a_run_ends_not_at_every_batch(self):
        # 배포와 화면 점검은 번역 묶음(data/laws-ko)마다 돌지 않고, 실행이 끝났다는 표(stamps)가 바뀌면 돈다
        for name in ("pages.yml", "sitecheck.yml"):
            text = pathlib.Path(".github/workflows", name).read_text(encoding="utf-8")
            paths = [line.split('"')[1] for line in text.split("jobs:")[0].splitlines() if line.strip().startswith('- "')]
            self.assertIn("!" + lock.SHOWN + "/**", paths, name)
            self.assertLess(paths.index("data/**"), paths.index("!" + lock.SHOWN + "/**"), f"{name}: 빼는 줄은 넣는 줄 뒤에 있어야 듣는다")
            self.assertIn(lock.STAMP.split("/")[0] + "/**", paths, name)
        # 번역 파일의 꼴을 보는 자동 시험은 묶음마다 그대로 돈다
        self.assertIn('"' + lock.SHOWN + '/**"', pathlib.Path(".github/workflows/tests.yml").read_text(encoding="utf-8"))

    def test_a_run_with_nothing_to_do_does_not_take_the_lock(self):
        # 번역이 다 끝난 뒤의 실행이 빈 커밋 한 쌍(시작, 끝)을 남기지 않게 한다
        before = self.git(self.a, "rev-parse", "HEAD").stdout
        self.assertEqual(lock.take("run-a", self.a, at=self.noon, work=lambda: False), ("idle", ""))
        self.assertIsNone(lock.read(self.a))
        self.assertEqual(self.git(self.a, "rev-parse", "HEAD").stdout, before)
        self.assertEqual(lock.take("run-a", self.a, at=self.noon, work=lambda: True), ("taken", ""))
        # 다른 실행이 도는 중이면 할 일을 묻기 전에 물러선다
        self.assertEqual(lock.take("run-b", self.b, at=self.later(1), work=lambda: False), ("busy", "run-a"))
        # 할 일: 옮길 문단, 검수할 문단, 청해 둔 견주기 시험 가운데 하나라도 있으면 있다
        with unittest.mock.patch.object(todo, "pick", return_value=([], {})), unittest.mock.patch.object(verify, "pending", return_value=[]):
            self.assertEqual(lock.anything_left(), pathlib.Path("trials/request.json").exists())
        with unittest.mock.patch.object(todo, "pick", return_value=([], {})), unittest.mock.patch.object(verify, "pending", return_value=[{"key": "aaa"}]):
            self.assertTrue(lock.anything_left())
        with unittest.mock.patch.object(todo, "pick", return_value=([{"key": "aaa"}], {})), unittest.mock.patch.object(verify, "pending", return_value=[]):
            self.assertTrue(lock.anything_left())

    def test_a_run_takes_the_lock_only_for_its_own_work(self):
        # 번역과 검수는 다른 예약 작업이 한다: 번역하는 실행은 검수할 것만 남았을 때, 검수하는 실행은 옮길 것만 남았을 때 잡지 않는다
        trial = pathlib.Path("trials/request.json").exists()
        with unittest.mock.patch.object(todo, "pick", return_value=([], {})), unittest.mock.patch.object(verify, "pending", return_value=[{"key": "aaa"}]):
            self.assertEqual(lock.anything_left("translate"), trial)
            self.assertTrue(lock.anything_left("verify"))
        with unittest.mock.patch.object(todo, "pick", return_value=([{"key": "aaa"}], {})), unittest.mock.patch.object(verify, "pending", return_value=[]):
            self.assertTrue(lock.anything_left("translate"))
            self.assertFalse(lock.anything_left("verify"))

    def test_the_lock_file_is_outside_every_workflow_path(self):
        # 자물쇠만 바뀐 커밋이 검사나 배포를 돌리면 안 된다: 자동 실행들의 paths에 걸리지 않는 곳이어야 한다
        folder = lock.PATH.split("/")[0]
        for workflow in pathlib.Path(".github/workflows").glob("*.yml"):
            text = workflow.read_text(encoding="utf-8")
            self.assertNotIn(f'"{folder}/', text, workflow.name)
            if "push:" in text:
                self.assertIn("paths:", text, f"{workflow.name}: 경로를 가리지 않는 push 실행이 있으면 자물쇠 커밋마다 돈다")


if __name__ == "__main__":
    unittest.main()
