"""EU 조약 조문과 절차 문서 받아 두기(tools.archive.primary): 긴 문서에서 남길 곳, 번호를 풀어 쓴 주소, 다른 문서를 받았을 때."""
import unittest
from unittest import mock

from tools.archive import crawl, primary


class PrimaryTest(unittest.TestCase):
    def test_a_long_document_keeps_only_the_named_part(self):
        lines = ["PART VII INSTITUTIONAL PROVISIONS .......... 22", "PART VIII FINANCIAL MECHANISM .......... 28", "PART VI COOPERATION", "a",
                 "PART VII INSTITUTIONAL PROVISIONS CHAPTER 1 THE STRUCTURE", "Article 92", "PART VIII FINANCIAL MECHANISM", "b"]
        start, end = primary.PART["eea-agreement"]
        self.assertEqual(primary.cut(lines, start, end), ["PART VII INSTITUTIONAL PROVISIONS CHAPTER 1 THE STRUCTURE", "Article 92"])   # 차례의 줄은 건너뛴다
        self.assertEqual(primary.cut(lines, "PART VIII FINANCIAL MECHANISM", "PART IX"), lines[1:])   # 끝을 알리는 줄이 없으면 글의 끝까지
        self.assertEqual(primary.cut(lines, "PART X", "PART XI"), [])

    def test_a_part_whose_heading_also_stands_in_the_contents_starts_at_the_last_one(self):
        lines = ["Article 49 Calculation of time-limits", "Article 53 Procedures", "TITLE II", "Article 49", "Calculation of time-limits", "Article 51",
                 "extended on account of distance by a single period of 10 days", "Article 53", "Procedures"]
        start, end, which = primary.PART["cjeu-rules"]
        self.assertEqual(primary.cut(lines, start, end, which), lines[3:7])
        self.assertEqual(primary.cut(lines, start, end), lines[:1])   # 첫 줄에서 시작하면 차례의 한 줄만 남는다

    def test_a_cut_without_the_expected_words_falls_back_to_the_whole_text(self):
        saved = {}
        body = ["Article 49 Calculation of time-limits", "Article 53 Procedures", "single period of 10 days"]   # 본문의 제목 줄이 없는 글
        with mock.patch.object(primary, "TARGETS", [("cjeu-rules", "32012Q0929(01)", "절차규칙", "single period of 10 days")]), \
                mock.patch.object(primary, "read", side_effect=lambda celex: (body, "https://example.org/rules", "")), \
                mock.patch.object(primary, "save_text", side_effect=lambda name, kept: saved.update({name: kept}) or name), \
                mock.patch.object(primary, "save_index"):
            self.assertEqual(primary.crawl()["stored"], 1)
        self.assertEqual(saved["eu-primary/cjeu-rules.txt"][-3:], body)
        self.assertFalse(any(line.startswith("[남긴 곳]") for line in saved["eu-primary/cjeu-rules.txt"]))

    def test_a_number_with_brackets_is_also_asked_in_its_escaped_form(self):
        asked = []

        def parts(code):
            asked.append(code)
            return ([("", "https://example.org/doc", ["delegated acts"])], "") if "%28" in code else ([], "404")

        with mock.patch.object(primary.fulltext, "celex_parts", side_effect=parts):
            self.assertEqual(primary.read("32016Q0512(01)"), (["delegated acts"], "https://example.org/doc", ""))
            self.assertEqual(primary.read("12016E294")[2], "404")
        self.assertEqual(asked, ["32016Q0512(01)", "32016Q0512%2801%29", "12016E294"])

    def test_a_text_without_the_expected_words_is_not_stored(self):
        saved = {}
        texts = {"12016E294": ["Article 294", "first reading"], "12016M016": ["some other document"]}
        with mock.patch.object(primary, "TARGETS", [("tfeu-294", "12016E294", "통상입법절차", "first reading"), ("teu-16", "12016M016", "이사회", "qualified majority")]), \
                mock.patch.object(primary, "read", side_effect=lambda celex: (texts[celex], "https://example.org/" + celex, "")), \
                mock.patch.object(primary, "save_text", side_effect=lambda name, kept: saved.update({name: kept}) or name), \
                mock.patch.object(primary, "save_index") as index:
            result = primary.crawl()
        self.assertEqual(result["stored"], 1)
        self.assertIn("teu-16 12016M016", result["failures"][0])
        self.assertEqual(saved["eu-primary/tfeu-294.txt"][-2:], ["Article 294", "first reading"])
        self.assertEqual(index.call_args.args[1][0]["url"], "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:12016E294")

    def test_the_step_runs_only_when_named(self):
        self.assertIn("eu-primary", [name for name, _ in crawl.STEPS])
        names = [name for name, _, _, _ in primary.TARGETS]
        self.assertEqual(len(names), len(set(names)))
        self.assertTrue(set(primary.PART) <= set(names))


if __name__ == "__main__":
    unittest.main()
