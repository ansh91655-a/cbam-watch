"""관보에 실리기 전의 법령 글을 받아 다듬는 일(tools/archive/pending.py)과 규정 원문 목록에 싣는 일(tools/laws/catalog.py)."""
import json
import os
import pathlib
import tempfile
import unittest

from tools.archive import pending
from tools.laws import catalog, segment

RAW = [
    "IMMC.C%282026%298367.ENG.xhtml.PART-2026-1191202V1.docx",
    "EXPLANATORY MEMORANDUM",
    "1.CONTEXT OF THE DELEGATED ACT",
    "COMMISSION DELEGATED REGULATION (EU) …/...",
    "of 25.11.2026",
    "Whereas:",
    "(1)Since 1 January 2026, the mechanism applies.",
    "Article 1",
    "Definitions",
    "1.A user shall enter a purchase request.",
    "(a)the identification number;",
    "(iii)the fee of 0.05 euro;",
    "(EU) 2023/956 is not a paragraph number.",
    "2. Already spaced.",
]


class Tidy(unittest.TestCase):
    def test_memorandum_and_file_name_are_left_out(self):
        lines, skipped = pending.tidy(RAW)
        self.assertEqual(lines[0], "COMMISSION DELEGATED REGULATION (EU) …/...")
        self.assertEqual(skipped, 2)   # 파일 이름을 뺀 뒤, 법령의 머리 앞에 있던 줄 수

    def test_glued_paragraph_numbers_get_a_space(self):
        lines, _ = pending.tidy(RAW)
        for needed in ("(1) Since 1 January 2026, the mechanism applies.", "1. A user shall enter a purchase request.", "(a) the identification number;", "(iii) the fee of 0.05 euro;"):
            self.assertIn(needed, lines)
        self.assertIn("(EU) 2023/956 is not a paragraph number.", lines)   # 대문자 괄호는 문단 번호가 아니다
        self.assertIn("2. Already spaced.", lines)

    def test_text_without_a_memorandum_is_kept_whole(self):
        lines, skipped = pending.tidy(RAW[3:])
        self.assertEqual((len(lines), skipped), (len(RAW) - 3, 0))

    def test_tidied_text_splits_into_recitals_and_articles(self):
        lines, _ = pending.tidy(RAW)
        kinds = [part["kind"] for part in segment.parts("\n".join(["[주소] https://example.eu", ""] + lines))]
        self.assertIn("recitals", kinds)
        self.assertIn("article", kinds)

    def test_address_escapes_the_brackets_of_the_document_number(self):
        self.assertEqual(pending.address_of("C(2026)8367"), "http://publications.europa.eu/resource/pi_com/C%282026%298367")


class Listed(unittest.TestCase):
    def setUp(self):
        self.before = os.getcwd()
        self.folder = tempfile.TemporaryDirectory()
        os.chdir(self.folder.name)
        pathlib.Path("collected/archive/pages/eu-pending").mkdir(parents=True)
        pathlib.Path("collected/archive/pages/eu-pending/a.txt").write_text("x", encoding="utf-8")
        entries = [
            {"name": "sale-adopted", "reference": "C(2026) 8367 final", "state": "adopted", "title": "표본 판매·환매 위임규정(채택본)", "rule": "dr-sale", "date": "2026-11-25",
             "url": "https://example.eu/a", "textPath": "collected/archive/pages/eu-pending/a.txt"},
            {"name": "decl-draft", "reference": "Ares(2026)1", "state": "draft", "title": "표본 신고서 이행규정(안)", "rule": "ir-decl", "date": "2026-11-19",
             "url": "https://example.eu/b", "textPath": "collected/archive/pages/eu-pending/a.txt"},
            {"name": "unknown-state", "state": "withdrawn", "title": "모르는 상태", "textPath": "collected/archive/pages/eu-pending/a.txt"},
            {"name": "no-text", "state": "draft", "title": "글이 없는 것"},
        ]
        pathlib.Path("collected/archive/eu-pending.json").write_text(json.dumps({"entries": entries}, ensure_ascii=False), encoding="utf-8")

    def tearDown(self):
        os.chdir(self.before)
        self.folder.cleanup()

    def test_pending_acts_are_listed_with_a_remark_and_no_celex(self):
        found = catalog.pending()
        self.assertEqual([act["id"] for act in found], ["sale-adopted", "decl-draft"])
        adopted, draft = found
        self.assertEqual((adopted["celex"], adopted["rule"], adopted["consolidated"]), ("", "dr-sale", ""))
        self.assertIn("2026년 11월 25일에 채택", adopted["remark"])
        self.assertIn("관보에 실리지 않아", adopted["remark"])
        self.assertIn("Delegated Regulation", adopted["official"])
        self.assertIn("C(2026) 8367 final", adopted["official"])
        self.assertIn("의견수렴 중인 초안", draft["remark"])
        self.assertIn("Implementing Regulation", draft["official"])

    def test_pending_acts_come_after_the_acts_in_force(self):
        ids = [act["id"] for act in catalog.acts()]
        self.assertEqual(ids, ["sale-adopted", "decl-draft"])   # 이 표본에는 시행 중인 법령의 목록이 없다
        self.assertTrue(all(act["group"] == "act" and act["format"] == "act" for act in catalog.acts()))


if __name__ == "__main__":
    unittest.main()
