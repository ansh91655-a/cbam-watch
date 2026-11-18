"""EU 조약 조문과 절차 문서 받아 두기(tools.archive.primary): 긴 문서에서 남길 곳, 번호를 풀어 쓴 주소, 다른 문서를 받았을 때."""
import unittest
from unittest import mock

from tools.archive import crawl, primary


class PrimaryTest(unittest.TestCase):
    def test_a_long_document_keeps_only_the_named_part(self):
        lines = ["PART VI", "a", "PART VII", "INSTITUTIONAL PROVISIONS", "Article 92", "PART VIII", "b"]
        self.assertEqual(primary.cut(lines, "PART VII", "PART VIII"), ["PART VII", "INSTITUTIONAL PROVISIONS", "Article 92"])
        self.assertEqual(primary.cut(lines, "PART VIII", "PART IX"), ["PART VIII", "b"])   # 끝을 알리는 줄이 없으면 글의 끝까지
        self.assertEqual(primary.cut(lines, "PART X", "PART XI"), [])

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
