"""국문 정리를 검사하는 도구를 확인한다."""
import collections
import json
import pathlib
import tempfile
import unittest

from tools.check import dates, excerpt_check, fact_check, style_check, term_lookup


class DatesTest(unittest.TestCase):
    def test_formats(self):
        for text in ("28Sep2026", "28 September 2026", "September 28, 2026", "2026-09-28", "2026년 9월 28일", "28/09/2026", "28. September 2026", "2026/09/28 23:59:59", "2026.09.28",
                     "Monday 28th September 2026", "September 28th, 2026"):
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

    def test_decimal_comma_in_the_source_matches_a_decimal_point(self):
        source = "The CBAM factor shall be equal to 97,5 % in 2026 and 37,5% in 2032."
        self.assertTrue(fact_check.check("CBAM 계수는 2026년 97.5%, 2032년 37.5%입니다.", source)["ok"])
        result = fact_check.check("CBAM 계수는 2026년 97.4%입니다.", source)
        self.assertEqual(result["missingNumbers"], ["97.4"])

    def test_changed_number_and_date_fail(self):
        result = fact_check.check("2026년 9월 29일에 공개했다. 0.78%가 면제된다.", self.SOURCE)
        self.assertFalse(result["ok"])
        self.assertEqual(result["missingDates"], ["2026-09-29"])
        self.assertEqual(result["missingNumbers"], ["0.78"])


class ExcerptCheckTest(unittest.TestCase):
    SOURCE = "Latest developments\n30Sep2026\nWebinar follow-up: CBAM from policy to practice\nThe Commission  held the fourth webinar.\n"

    def test_short_date_line_is_fine_when_present(self):
        result = excerpt_check.check("30Sep2026\nWebinar follow-up: CBAM from policy to practice\nThe Commission held the fourth webinar.", self.SOURCE)
        self.assertTrue(result["ok"], result)

    def test_changed_letter_fails(self):
        result = excerpt_check.check("The Commission held the fifth webinar.", self.SOURCE)
        self.assertFalse(result["ok"])
        self.assertEqual(len(result["missing"]), 1)

    def test_only_tiny_fragments_fail(self):
        self.assertFalse(excerpt_check.check("30Sep2026", self.SOURCE)["ok"])
        self.assertFalse(excerpt_check.check("", self.SOURCE)["ok"])


class StyleCheckTest(unittest.TestCase):
    def test_polite_sentence_passes(self):
        hits = style_check.check("EU 집행위원회는 2026년 10월 5일에 가격을 게시했습니다. 15,000톤을 넘으면 제6조(1)이 적용됩니다.")
        self.assertEqual(hits, [])

    def test_plain_ending_is_hard(self):
        hits = style_check.check("EU 집행위원회는 가격을 게시했다. 대상은 수소다.")
        self.assertEqual([(hit["rule"], hit["hard"], hit["count"]) for hit in hits], [("plain-ending", True, 2)])

    def test_title_without_period_is_not_a_sentence(self):
        self.assertEqual(style_check.check("2026년 3분기 CBAM 인증서 가격 82.32유로\nEU 집행위원회가 가격을 게시했습니다."), [])

    def test_decimal_comma_is_hard(self):
        hits = style_check.check("가격은 82,32유로입니다.")
        self.assertEqual([(hit["rule"], hit["hard"]) for hit in hits], [("decimal-comma", True)])

    def test_citation_form(self):
        hits = style_check.check("제6조 제1항에 따릅니다.")
        self.assertEqual([hit["rule"] for hit in hits], ["citation"])



class TermLookupTest(unittest.TestCase):
    TERMS = {"terms": [
        {"no": 1, "en": ["surrender (of CBAM certificates)"], "abbr": [], "preferred": "제출", "allowed": [], "status": "confirmed"},
        {"no": 2, "en": ["ferro-manganese"], "abbr": ["FeMn"], "preferred": "페로망간", "allowed": [], "status": "partial"},
        {"no": 2, "en": ["ferro-chromium"], "abbr": ["FeCr"], "preferred": "페로크롬", "allowed": [], "status": "partial"},
    ]}

    def test_a_term_noted_with_a_bracket_is_found_without_it(self):
        with tempfile.TemporaryDirectory() as folder:
            path = pathlib.Path(folder, "glossary.json")
            path.write_text(json.dumps(self.TERMS, ensure_ascii=False), encoding="utf-8")
            found = term_lookup.lookup("Declarants shall surrender the certificates. FeMn is covered.", str(path))
        # 괄호 안의 풀이("of CBAM certificates")는 글에 나오지 않는다. 약어는 그 항목의 것만 맞는다(FeMn은 페로크롬이 아니다)
        self.assertEqual([(row["en"], row["ko"], row["status"]) for row in found], [("surrender", "제출", "확인"), ("FeMn", "페로망간", "부분 확인")])

    def test_entries_split_from_one_row_do_not_share_an_abbreviation(self):
        terms = json.loads(pathlib.Path(term_lookup.GLOSSARY).read_text(encoding="utf-8"))["terms"]
        owners = collections.defaultdict(set)
        for term in terms:
            for abbr in term.get("abbr", []):
                owners[(term.get("no"), abbr)].add(term["preferred"])
        self.assertEqual({key: sorted(names) for key, names in owners.items() if len(names) > 1}, {})
        # 흔한 낱말 하나만으로 된 표기는 엉뚱한 자리에 걸린다(review → 신고서 검토가 review process에 걸려 틀린 번역을 낳았다)
        by_english = {form: term["preferred"] for term in terms for form in term["en"]}
        self.assertNotIn("review", by_english)


if __name__ == "__main__":
    unittest.main()
