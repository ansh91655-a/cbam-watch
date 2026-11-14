"""글 속 용어 풀이의 자료 만들기(tools/publish/gloss.py)."""
import pathlib
import tempfile
import unittest

from tools.common.jsonio import read_json
from tools.publish import gloss, handbook

RULES = {"skipAbbr": ["CBAM", "CA", "BM"], "skipKo": ["제출"]}
GLOSSARY = {"terms": [
    {"en": "Carbon Border Adjustment Mechanism", "abbr": "CBAM", "ko": "탄소국경조정제도", "note": "EU로 수입되는 제품에 탄소비용을 물리는 제도"},
    {"en": "competent authority", "abbr": "CA", "ko": "관할당국", "note": "회원국이 지정한 당국"},
    {"en": "Combined Nomenclature", "abbr": "CN", "ko": "통합품목분류표", "note": "EU의 8단위 품목분류"},
    {"en": "cross-sectoral correction factor", "abbr": "CSCF", "ko": "부문 간 보정계수", "note": "무상할당을 같은 비율로 줄이는 계수"},
    {"en": "carbon capture and storage / utilisation", "abbr": "CCS / CCU(S)", "ko": "탄소 포집·저장", "note": "CO₂를 포집해 저장하거나 활용하는 기술"},
    {"en": "perfluorocarbons", "abbr": "PFCs", "ko": "과불화탄소", "note": "알루미늄 생산에서 나오는 온실가스"},
    {"en": "CO2 equivalent", "abbr": "CO₂e", "ko": "이산화탄소 상당량", "note": "온실가스를 CO₂로 환산한 양"},
    {"en": "embedded emissions", "abbr": "", "ko": "내재배출량", "note": "용어집의 풀이"},
    {"en": "safeguard", "abbr": "", "ko": "세이프가드", "note": "약어가 없는 용어집의 말"},
]}
BOOK = {"terms": [
    {"ko": "CN 코드", "en": "CN code", "abbr": "CN", "text": "통합품목분류표에 따른 품목 코드입니다.", "chapter": "scope", "section": "goods-cn"},
    {"ko": "관할당국", "en": "competent authority", "text": "회원국마다 지정한 당국입니다.", "chapter": "roles", "section": "authorities"},
    {"ko": "제출", "en": "surrender", "text": "인증서를 상계하는 것입니다.", "chapter": "cycle", "section": "surrender"},
    {"ko": "내재배출량", "en": "embedded emissions", "text": "직접배출량과 간접배출량을 합친 것입니다.", "chapter": "embedded", "section": "definitions"},
    {"ko": "부문 간 보정계수", "en": "cross-sectoral correction factor", "abbr": "CSCF", "text": "무상할당을 같은 비율로 줄이는 계수입니다.", "chapter": "certificates", "section": "cscf"},
    {"ko": "CBAM 벤치마크", "en": "CBAM benchmark", "abbr": "BM", "text": "무상할당 조정에 쓰는 기준값입니다.", "chapter": "certificates", "section": "benchmark"},
]}


# 다른 제도를 다루는 장(scope가 "uk")의 용어: 그 범위의 글에만 쓴다
UK_BOOK = {"terms": BOOK["terms"] + [
    {"ko": "회계기간", "en": "accounting period", "text": "영국 CBAM의 세액을 계산하는 단위 기간입니다.", "chapter": "uk", "section": "returns", "scope": "uk"},
    {"ko": "관할당국", "en": "competent authority", "abbr": "CA", "text": "영국에서는 국세청입니다.", "chapter": "uk", "section": "overview", "scope": "uk"},
]}
REGULATIONS = {"regulations": [
    {"id": "uk-cbam", "group": "uk", "related": {"sources": ["hmrc-cbam", "uk-legislation"], "words": ["영국 CBAM"]}},
    {"id": "linking", "group": "eu-external", "related": {"sources": ["uk-legislation", "eur-lex"]}},
    {"id": "base", "group": "eu-law", "related": {"sources": ["eur-lex"]}},
    {"id": "plain", "group": "eu-acts"},
]}
ITEMS = [
    {"id": "b-hmrc", "sourceCode": "hmrc-cbam", "title": "영국 국세청 안내"},
    {"id": "a-hmrc", "sourceCode": "hmrc-cbam", "title": "영국 CBAM 고시"},
    {"id": "gone", "sourceCode": "hmrc-cbam", "title": "내린 소식", "withdrawn": True},
    {"id": "act", "sourceCode": "uk-legislation", "title": "영국 법령"},
    {"id": "press", "sourceCode": "press", "title": "영국 CBAM을 다룬 국내 보도"},
    {"id": "eu", "sourceCode": "eur-lex", "title": "관보"},
]


class AbbreviationsTest(unittest.TestCase):
    def test_the_forms_to_look_for_are_read_from_the_abbreviation_cell(self):
        self.assertEqual(gloss.abbreviations("CSCF"), ["CSCF"])
        self.assertEqual(gloss.abbreviations("EU ETS"), ["EU ETS"])
        self.assertEqual(gloss.abbreviations("CCS / CCU(S)"), ["CCS", "CCU", "CCUS"])   # 괄호 안의 글자가 붙은 꼴과 안 붙은 꼴
        self.assertEqual(gloss.abbreviations("FeSi / SiMn"), ["FeSi", "SiMn"])
        self.assertEqual(gloss.abbreviations("PFCs"), ["PFC"])                          # 복수형은 단수형으로(글에서는 s가 붙은 꼴도 찾는다)
        self.assertEqual(gloss.abbreviations("UN/LOCODE"), ["UN/LOCODE"])
        self.assertEqual(gloss.abbreviations("CO₂e"), [])                               # 아래 첨자가 든 것은 글에서 그 꼴로 나오지 않는다
        self.assertEqual(gloss.abbreviations(""), [])


class BuildTest(unittest.TestCase):
    def setUp(self):
        self.body, self.problems = gloss.build(RULES, GLOSSARY, BOOK)
        self.terms = {term["ko"]: term for term in self.body["terms"]}

    def test_handbook_terms_come_first_and_carry_the_way_to_their_section(self):
        self.assertEqual(self.problems, [])
        one = self.terms["내재배출량"]
        self.assertEqual((one["forms"], one["text"], one["read"]), (["내재배출량"], "직접배출량과 간접배출량을 합친 것입니다.", "#handbook-embedded.definitions"))
        # 해설서의 용어와 용어집의 약어가 같은 말이면 한 용어로 묶는다(국문 표기와 약어를 모두 찾는다)
        self.assertEqual(self.terms["부문 간 보정계수"]["forms"], ["부문 간 보정계수", "CSCF"])
        # 같은 약어가 두 용어에 걸리면 해설서의 용어가 가진다. 표기를 하나도 갖지 못한 용어는 싣지 않는다
        self.assertEqual(self.terms["CN 코드"]["forms"], ["CN 코드", "CN"])
        self.assertNotIn("통합품목분류표", self.terms)

    def test_glossary_abbreviations_are_added_with_the_glossary_note(self):
        self.assertEqual((self.terms["탄소 포집·저장"]["forms"], self.terms["탄소 포집·저장"]["read"]), (["CCS", "CCU", "CCUS"], ""))
        self.assertEqual((self.terms["과불화탄소"]["forms"], self.terms["과불화탄소"]["text"]), (["PFC"], "알루미늄 생산에서 나오는 온실가스"))
        self.assertNotIn("세이프가드", self.terms)           # 약어가 없고 해설서가 풀이하지 않은 용어집의 말은 표시하지 않는다
        self.assertNotIn("이산화탄소 상당량", self.terms)     # 글에서 찾을 표기가 없는 약어

    def test_the_skip_lists_drop_forms_but_not_the_other_form_of_the_same_term(self):
        self.assertNotIn("탄소국경조정제도", self.terms)                      # 글마다 나오는 약어
        self.assertEqual(self.terms["관할당국"]["forms"], ["관할당국"])        # 약어 CA는 빼고 국문 표기는 남긴다
        self.assertEqual(self.terms["CBAM 벤치마크"]["forms"], ["CBAM 벤치마크"])
        self.assertNotIn("제출", self.terms)                                   # 일상어로도 쓰는 말

    def test_a_stale_skip_list_is_reported(self):
        _, found = gloss.build({"skipAbbr": ["CBAM", "ZZZ"], "skipKo": ["제출", "없는 말"]}, GLOSSARY, BOOK)
        self.assertEqual(found, [("빼는 약어", "용어집과 해설서에 없는 약어: ZZZ"), ("빼는 국문 표기", "해설서가 풀이하지 않는 말: 없는 말")])

    def test_nothing_is_written_when_there_is_a_problem(self):
        with tempfile.TemporaryDirectory() as folder:
            count, found = gloss.write(folder, {"terms": []}, {"terms": []})   # 저장소의 자료가 빼라고 한 말이 이 빈 자료에는 없다
            self.assertEqual(count, 0)
            self.assertTrue(found)
            self.assertFalse((pathlib.Path(folder) / "gloss.json").exists())


class ScopeTest(unittest.TestCase):
    """범위가 있는 용어(영국 CBAM의 장): 같은 낱말이라도 제도마다 뜻이 달라, 그 범위의 글에만 쓰고 그 범위의 글에는 다른 용어를 쓰지 않는다."""

    def setUp(self):
        self.body, self.problems = gloss.build(RULES, GLOSSARY, UK_BOOK, REGULATIONS, ITEMS)
        self.scoped = [term for term in self.body["terms"] if term.get("scope")]
        self.plain = [term for term in self.body["terms"] if not term.get("scope")]

    def test_scoped_terms_are_kept_apart_from_the_others(self):
        self.assertEqual(self.problems, [])
        self.assertEqual([(term["ko"], term["scope"], term["read"]) for term in self.scoped],
                         [("회계기간", "uk", "#handbook-uk.returns"), ("관할당국", "uk", "#handbook-uk.overview")])
        # 범위가 없는 용어는 범위가 있는 용어가 더해져도 그대로다(같은 영문 표기의 용어가 두 범위에 따로 있다)
        alone, _ = gloss.build(RULES, GLOSSARY, BOOK)
        self.assertEqual(self.plain, alone["terms"])
        self.assertNotIn("scopes", alone)

    def test_a_form_is_owned_within_its_scope_and_glossary_abbreviations_stay_outside(self):
        by_ko = {term["ko"]: term for term in self.scoped}
        self.assertEqual(by_ko["관할당국"]["forms"], ["관할당국"])   # 범위가 없는 '관할당국'이 이미 가진 표기지만, 범위마다 임자를 따로 가린다. 빼기로 한 약어(CA)는 여기서도 뺀다
        self.assertEqual(by_ko["관할당국"]["text"], "영국에서는 국세청입니다.")
        self.assertFalse([term for term in self.scoped if term["ko"] in ("과불화탄소", "탄소 포집·저장")])   # 용어집의 약어는 범위가 없는 글에만 쓴다

    def test_the_items_of_a_scope_come_from_the_sources_of_its_rule_group(self):
        # 그 이름의 규제 묶음에 속한 규제의 출처에서 온 소식. 다른 묶음의 규제도 출처로 삼는 곳(uk-legislation)과 낱말로만 이어진 소식(press), 내린 소식은 뺀다
        self.assertEqual(self.body["scopes"], {"uk": ["a-hmrc", "b-hmrc"]})
        self.assertEqual(gloss.scope_items(["uk", "kr"], REGULATIONS, ITEMS), {"uk": ["a-hmrc", "b-hmrc"], "kr": []})
        self.assertEqual(gloss.scope_items(["uk"], None, None), {"uk": []})
        without, _ = gloss.build(RULES, GLOSSARY, UK_BOOK)   # 규제 자료가 없으면 범위는 있고 소식은 없다
        self.assertEqual(without["scopes"], {"uk": []})


class RepositoryTest(unittest.TestCase):
    def test_the_stored_rules_fit_the_stored_glossary_and_handbook(self):
        book = handbook.public(read_json(handbook.SOURCE, {}))
        body, found = gloss.build(read_json(gloss.SOURCE, {}), read_json("data/terms.json", {}), book,
                                  read_json("data/regulations.json", {}), read_json("data/items.json", {}).get("items", []))
        self.assertEqual(found, [])
        scoped = [term for term in body["terms"] if term.get("scope")]
        terms = [term for term in body["terms"] if not term.get("scope")]
        # 영국 CBAM의 장이 풀이한 용어는 그 범위에만 있고, 그 범위의 소식은 영국의 출처에서 온 것들이다(일정 화면의 첫 소식 '영국 CBAM, 2027년 1월 1일 시행'도 그 하나다)
        self.assertEqual({term["scope"] for term in scoped}, {"uk"})
        self.assertGreaterEqual(len(scoped), 12)
        self.assertTrue(all(term["read"].startswith("#handbook-uk.") for term in scoped))
        self.assertEqual(sorted(body["scopes"]), ["uk"])
        self.assertIn("seed-uk-cbam", body["scopes"]["uk"])
        self.assertGreaterEqual(len(body["scopes"]["uk"]), 10)
        self.assertGreaterEqual(len(terms), 80)
        forms = [form.replace(" ", "") for term in terms for form in term["forms"]]
        self.assertEqual(len(forms), len(set(forms)))                       # 표기 하나는 한 용어의 것이다
        self.assertFalse({"CBAM", "EU", "제출", "사업자"} & set(forms))       # 글마다 나오는 말과 일상어는 표시하지 않는다
        for term in terms:
            self.assertTrue(term["text"] and term["ko"], term)
            if term["read"]:
                self.assertRegex(term["read"], r"^#handbook-[a-z-]+\.[a-z-]+$")
        by_form = {form: term for term in terms for form in term["forms"]}
        self.assertEqual(by_form["CSCF"]["read"], "#handbook-certificates.cscf")   # 사용자가 물은 그 약어


if __name__ == "__main__":
    unittest.main()
