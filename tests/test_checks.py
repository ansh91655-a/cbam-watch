"""국문 정리를 검사하는 도구를 확인한다."""
import unittest

from tools.check import dates, fact_check, style_check


class DatesTest(unittest.TestCase):
    def test_formats(self):
        for text in ("28Sep2026", "28 September 2026", "September 28, 2026", "2026-09-28", "2026년 9월 28일", "28/09/2026", "28. September 2026"):
            found, _ = dates.find(text)
            self.assertEqual(found, {(2026, 9, 28)}, text)

    def test_not_a_date(self):
        found, _ = dates.find("규정(EU) 2023/956과 50톤 기준")
        self.assertEqual(found, set())


class FactCheckTest(unittest.TestCase):
    SOURCE = "28Sep2026 New resources. The 50-tonne threshold would exempt 0.87% of embedded emissions. Regulation (EU) 2025/2621. Price 82.32 on 5 October 2026. 1,234 declarants."

    def test_same_facts_in_other_notation_pass(self):
        result = fact_check.check("2026년 9월 28일에 공개했다. 50톤 기준으로 0.87%가 면제된다. 이행규정(EU) 2025/2621. 2026년 10월 5일 가격 82.32유로. 신고인 1,234명.", self.SOURCE)
        self.assertTrue(result["ok"], result)

    def test_changed_number_and_date_fail(self):
        result = fact_check.check("2026년 9월 29일에 공개했다. 0.78%가 면제된다.", self.SOURCE)
        self.assertFalse(result["ok"])
        self.assertEqual(result["missingDates"], ["2026-09-29"])
        self.assertEqual(result["missingNumbers"], ["0.78"])


class StyleCheckTest(unittest.TestCase):
    def test_plain_sentence_passes(self):
        hits = style_check.check("EU 집행위원회는 2026년 10월 5일에 가격을 게시했다. 15,000톤을 넘으면 제6조(1)이 적용된다.")
        self.assertEqual(hits, [])

    def test_decimal_comma_is_hard(self):
        hits = style_check.check("가격은 82,32유로다.")
        self.assertEqual([(hit["rule"], hit["hard"]) for hit in hits], [("decimal-comma", True)])

    def test_citation_form(self):
        hits = style_check.check("제6조 제1항에 따른다.")
        self.assertEqual([hit["rule"] for hit in hits], ["citation"])


if __name__ == "__main__":
    unittest.main()
