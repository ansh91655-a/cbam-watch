"""규정 원문: 법령 글 나누기, 번역의 열쇠와 검사, 영문 병기, 사이트 자료 만들기, 전체 규정에서 찾기."""
import contextlib
import io
import json
import pathlib
import shutil
import subprocess
import tempfile
import unittest
import unittest.mock

from tools.laws import apply, build, catalog, check, corpus, gloss, held, segment, status, store, terms, todo
from tools.run import laws_health

ACT = """[주소] https://example.org/act
[무엇] 시험용 법령

L_2099.000101.fmx.xml
COMMISSION IMPLEMENTING REGULATION (EU) 2099/1234
of 1 March 2099
laying down rules for a test
THE EUROPEAN COMMISSION,
Whereas:
(1)
The first recital explains why.
(2)
The second recital.
HAS ADOPTED THIS REGULATION:
CHAPTER I
GENERAL PROVISIONS
Article 1
Subject matter
1.
This Regulation lays down rules.
2.
It applies to goods:
(a)
listed in Annex I;
(b)
imported from 1 January 2100.
Article 2
The following article is inserted:
‘Article 2a
Quoted title
1. Quoted paragraph.’
Article 3
Entry into force
This Regulation shall enter into force on the third day.
Done at Brussels, 1 March 2099.
For the Commission
(1) OJ L 1, 1.1.2099, p. 1.
ANNEX I
List of things
▼M1
First row
►M1 Second row ◄
( 2 ) A note at the very end.
"""


class SegmentTest(unittest.TestCase):
    def setUp(self):
        self.parts = segment.parts(ACT)
        self.by_id = {part["id"]: part for part in self.parts}

    def test_the_act_is_cut_into_its_parts_in_order(self):
        self.assertEqual([part["id"] for part in self.parts], ["front", "recitals", "div-1", "art-1", "art-2", "art-3", "closing", "annex-i", "notes"])
        self.assertEqual([part["kind"] for part in self.parts][:4], ["front", "recitals", "division", "article"])

    def test_saved_headers_file_names_and_amendment_marks_are_left_out(self):
        self.assertEqual(self.by_id["front"]["blocks"][0], "COMMISSION IMPLEMENTING REGULATION (EU) 2099/1234")
        self.assertEqual(self.by_id["annex-i"]["blocks"], ["First row", "Second row"])

    def test_a_number_on_its_own_line_joins_the_next_line(self):
        self.assertEqual(self.by_id["recitals"]["blocks"][:2], ["(1) The first recital explains why.", "(2) The second recital."])
        self.assertEqual(self.by_id["art-1"]["blocks"], ["1. This Regulation lays down rules.", "2. It applies to goods:", "(a) listed in Annex I;", "(b) imported from 1 January 2100."])

    def test_titles_are_told_from_sentences(self):
        self.assertEqual((self.by_id["art-1"]["title"], self.by_id["div-1"]["title"], self.by_id["annex-i"]["title"]), ("Subject matter", "GENERAL PROVISIONS", "List of things"))
        self.assertEqual(self.by_id["art-2"]["title"], "")  # 쌍점으로 끝나는 줄은 조의 이름이 아니라 본문이다
        self.assertEqual(self.by_id["art-2"]["blocks"][0], "The following article is inserted:")

    def test_an_article_quoted_inside_an_amending_article_is_not_a_new_article(self):
        self.assertNotIn("art-2a", self.by_id)
        self.assertIn("‘Article 2a", self.by_id["art-2"]["blocks"])

    def test_footnotes_are_gathered_from_the_signature_and_the_very_end(self):
        self.assertEqual(self.by_id["notes"]["blocks"], ["(1) OJ L 1, 1.1.2099, p. 1.", "( 2 ) A note at the very end."])
        self.assertEqual(self.by_id["closing"]["blocks"], ["Done at Brussels, 1 March 2099.", "For the Commission"])

    def test_korean_names_of_parts(self):
        self.assertEqual([segment.label_ko(part) for part in self.parts], ["제목과 근거", "전문", "제1장", "제1조", "제2조", "제3조", "맺음", "부속서 I", "각주"])
        self.assertEqual(segment.label_ko({"kind": "article", "label": "Article 10a"}), "제10a조")
        self.assertEqual((segment.roman("XIV"), segment.roman("Mi")), (14, 0))


class CheckTest(unittest.TestCase):
    def test_keys_ignore_spacing_and_follow_the_text(self):
        self.assertEqual(store.key("Subject  matter"), store.key(" Subject matter\n"))
        self.assertNotEqual(store.key("Subject matter"), store.key("Scope"))
        self.assertEqual(len(store.key("Scope")), 12)

    def test_lines_without_words_need_no_translation(self):
        self.assertFalse(check.needs("2523 10 00"))
        self.assertFalse(check.needs("—"))
        self.assertTrue(check.needs("2523 10 00 – Cement clinkers"))

    def test_numbers_of_the_source_must_survive(self):
        source = "By 31 May 2027, the fee shall be EUR 1 000 under Article 5(2)."
        self.assertEqual(check.problems(source, "2027년 5월 31일까지 수수료는 제5조(2)에 따라 1,000유로로 한다.")["hard"], [])
        self.assertIn("원문의 수가 빠짐: 2027", check.problems(source, "5월 31일까지 수수료는 제5조(2)에 따라 1,000유로로 한다.")["hard"])
        self.assertEqual(check.problems(source, "2027년 5월 31일까지 수수료는 제5조(2)에 따라 1,000유로로 한다.")["soft"], [])  # 달 이름에서 온 5는 원문에 없는 수가 아니다
        self.assertIn("원문에 없는 수: 90", check.problems(source, "2027년 5월 31일까지 90일 안에 제5조(2)에 따라 1,000유로를 낸다.")["soft"])

    def test_untranslated_text_empty_text_and_lost_annex_numbers_are_stopped(self):
        self.assertEqual(check.problems("The rules apply.", "")["hard"], ["번역이 비어 있음"])
        self.assertIn("국문으로 옮기지 않음", check.problems("The rules apply.", "The rules apply.")["hard"])
        self.assertEqual(check.problems("Ursula VON DER LEYEN", "Ursula VON DER LEYEN")["hard"], [])  # 이름만 있는 줄은 그대로 두어도 된다
        self.assertIn("부속서·장의 번호가 빠짐: IV", check.problems("as set out in Annex IV", "부속서 4에 정한 대로")["hard"])
        self.assertEqual(check.problems("as set out in Annex IV", "부속서 IV에 정한 대로")["hard"], [])

    def test_core_terms_must_use_the_glossary_wording(self):
        source = "The embedded emissions shall be verified."
        self.assertEqual(check.problems(source, "내재배출량은 검증을 받는다.")["hard"], [])
        self.assertTrue(any(why.startswith("용어집의 표기가 없음: embedded emissions") for why in check.problems(source, "내포된 배출은 검증을 받는다.")["hard"]))
        # 더 긴 낱말에 든 낱말은 따로 요구하지 않는다(economic operator의 operator)
        self.assertEqual([entry["show"] for entry in terms.found("an economic operator") if entry["show"] == "operator"], [])

    def test_words_inside_web_addresses_are_not_text_to_translate(self):
        # 주소만 적은 각주는 옮기지 않고 그대로 싣는다. 주소 밖에 글이 있으면 옮긴다
        self.assertFalse(check.needs("[13] https://european-accreditation.org/national-accreditation-bodies-for-eu-cbam/"))
        self.assertFalse(check.needs("www.example.org/installation-operators"))
        self.assertTrue(check.needs("See https://example.org/guidance for details."))
        # 주소 안의 낱말은 용어집과 견주지 않는다. 주소 밖의 낱말은 그대로 견준다
        address = "https://example.org/cbam#module-for-non-eu-installation-operators-o3ci"
        self.assertEqual(check.problems(f"For registering, please see: {address}", f"등록 방법은 다음을 참고한다: {address}")["hard"], [])
        outside = check.problems(f"The operator of the installation registers at {address}", f"운영자가 다음에서 등록한다: {address}")["hard"]
        self.assertTrue(any(why.startswith("용어집의 표기가 없음") for why in outside))
        # 주소 안의 수는 번역에 그대로 남아 있어야 한다(주소를 빠뜨리거나 고쳐 적지 않게)
        self.assertIn("원문의 수가 빠짐: 2026", check.problems("See https://example.org/news-2026 for details.", "자세한 내용은 주소를 참고한다.")["hard"])

    def test_a_term_left_in_english_as_a_screen_name_needs_no_korean_wording(self):
        # 등록부 안내서는 화면에 적힌 이름을 원문대로 둔다. 그 자리에 든 용어에는 국문 표기를 요구하지 않는다
        source = "Type of Actor: this field must display “Third country Operator”"
        self.assertEqual(check.problems(source, "행위자 유형: 이 칸에는 “Third country Operator”가 표시되어야 한다.")["hard"], [])
        self.assertEqual(check.problems("User role: Admin Operator or Simple Operator", "사용자 역할: Admin Operator 또는 Simple Operator")["hard"], [])
        # 영문으로 두지도 않고 용어집의 표기도 쓰지 않으면 그대로 막는다
        self.assertTrue(any(why.startswith("용어집의 표기가 없음: operator") for why in check.problems("The operator registers.", "운영자가 등록한다.")["hard"]))
        # 용어를 영문으로 두더라도 글을 옮기지 않은 것은 막는다
        self.assertIn("국문으로 옮기지 않음", check.problems("The operator registers.", "The operator registers.")["hard"])

    def test_a_core_term_used_in_another_sense_is_noted_not_stopped(self):
        # installation of wind turbines의 installation은 사업장이 아니라 설치다(sources/translation.json의 senses)
        source = "No upstream emissions related to the production and installation of wind turbines are considered."
        found = check.problems(source, "풍력 터빈의 생산 및 설치와 관련된 업스트림 배출량은 고려하지 않는다.")
        self.assertEqual(found["hard"], [])
        self.assertIn("용어집의 뜻(사업장)이 아닌 다른 뜻으로 옮김: installation → 설치", found["soft"])
        # 적어 둔 뜻이 아닌 낱말로 옮기면 그대로 막는다
        self.assertTrue(any(why.startswith("용어집의 표기가 없음: installation") for why in check.problems(source, "풍력 터빈의 생산 및 시설과 관련된 배출량은 고려하지 않는다.")["hard"]))
        # 용어집의 표기를 쓴 번역에는 아무 말도 하지 않는다
        self.assertEqual(check.problems("The installation is located in Korea.", "사업장은 한국에 있다."), {"hard": [], "soft": []})

    def test_lines_with_nothing_to_translate_may_stay_as_they_are(self):
        # 식과, 화면에 뜨는 번호 붙은 알림 글은 원문대로 두어도 막지 않는다. 수는 그대로 견준다
        for line in ("E = eec + el + ep + etd + eu – esca – eccs – eccr", "EFheat,default = 62,3 t CO2e / TJ",
                     "• VAL748 The attribute [Type of Person] has invalid value [Physical Person], please check the onboarding manual for more details."):
            self.assertEqual(check.problems(line, line)["hard"], [], line)
        self.assertIn("원문의 수가 빠짐: 3, 62", check.problems("EFheat,default = 62,3 t CO2e / TJ", "EFheat,default = t CO2e / TJ")["hard"])
        # 등호가 있어도 글이 이어지는 줄, 번호 없이 영문으로 남긴 글은 그대로 막는다
        self.assertIn("국문으로 옮기지 않음", check.problems("where x = the number of installations", "where x = the number of installations")["hard"])
        self.assertIn("국문으로 옮기지 않음", check.problems("The attribute has an invalid value.", "The attribute has an invalid value.")["hard"])

    def test_footnote_marks_must_be_kept_and_numbers_must_not_be_split(self):
        # 각주 표시는 원문을 읽을 때 갈라 둔다(Equation 55[16]). 번역에도 그 표시가 있어야 한다
        source = "The parameters are given in the Equation 55[16] as follows:"
        self.assertEqual(check.problems(source, "매개변수는 다음과 같이 식 55[16]에 주어져 있다."), {"hard": [], "soft": []})
        self.assertIn("각주 표시가 빠짐: [16]", check.problems(source, "매개변수는 다음과 같이 식 55(16)에 주어져 있다.")["hard"])
        self.assertIn("각주 표시가 빠짐: [16]", check.problems(source, "매개변수는 다음과 같이 식 55 16에 주어져 있다.")["hard"])
        # 표시가 두 번 나오면 번역에도 두 번 있어야 한다
        self.assertIn("각주 표시가 빠짐: [2]", check.problems("The act[2] and the rule[2] apply.", "그 법[2]과 그 규칙이 적용된다.")["hard"])
        # 번역이 수를 제멋대로 가르면 수가 빠진 것이다(2551 → 255[1])
        wrong = check.problems("Regulation (EU) 2025/2551) ([4]) applies.", "규정 (EU) 2025/255[1])([4])이 적용된다.")
        self.assertIn("원문의 수가 빠짐: 2551", wrong["hard"])

    def test_a_wording_the_glossary_avoids_is_let_through_where_the_source_means_it(self):
        # 용어집은 accuracy를 '정밀도'로 옮기지 말라고 하지만, precision은 정밀도다. the CBAM rules는 CBAM 규정(Regulation)이 아니다
        source = "It will depend on the accuracy and precision of the measurement equipment used."
        found = check.problems(source, "이는 사용한 측정 장비의 정확도와 정밀도에 따라 달라진다.")
        self.assertEqual(found["hard"], [])
        self.assertIn("용어집이 쓰지 않는 표기 '정밀도'를 원문의 precision의 뜻으로 씀", found["soft"])
        self.assertIn("용어: '정밀도' 대신 '정확도'", check.problems("It will depend on the accuracy of the equipment.", "이는 장비의 정밀도에 따라 달라진다.")["hard"])
        self.assertEqual(check.problems("determined in line with the CBAM rules outlined above", "위에 설명한 CBAM 규칙에 따라 정한")["hard"], [])
        self.assertIn("용어: 'CBAM 규칙' 대신 'CBAM 규정'", check.problems("determined in line with the CBAM Regulation", "CBAM 규칙에 따라 정한")["hard"])

    def test_a_term_negated_with_non_is_not_asked_for(self):
        # non-material misstatement는 용어집의 material misstatement(중요한 오류)를 부정한 말이다
        self.assertEqual(check.problems("The verification report contains non-material misstatements", "검증보고서에 중요하지 않은 오류가 들어 있다.")["hard"], [])
        self.assertTrue(any(why.startswith("용어집의 표기가 없음: material misstatement") for why in check.problems("The report contains material misstatements.", "보고서에 큰 잘못이 들어 있다.")["hard"]))
        # 부정한 것과 그대로인 것이 함께 나오면 그대로 요구한다
        both = check.problems("Non-material misstatements may jointly become material misstatements.", "중요하지 않은 잘못이 모여 큰 잘못이 될 수 있다.")["hard"]
        self.assertTrue(any(why.startswith("용어집의 표기가 없음: material misstatement") for why in both))
        # 용어집에 non-으로 시작하는 낱말이 따로 있으면 그것으로 본다. 부정된 자리에 든 짧은 낱말은 따로 요구하지 않는다
        self.assertIn("non-eu country", [form for entry in terms.found("goods from non-EU countries") for form in entry["en"]])
        self.assertNotIn("goods", [entry["show"] for entry in terms.found("imports of non-CBAM goods")])

    def test_site_names_mail_addresses_and_file_names_are_not_text_to_translate(self):
        self.assertFalse(check.needs("• example.com"))
        self.assertFalse(check.needs("helpdesk@example.eu"))
        self.assertEqual(check.problems("CBAM_O3CI_Data_Ele ments.xlsx", "CBAM_O3CI_Data_Ele ments.xlsx")["hard"], [])
        self.assertTrue(check.needs("1.Introduction"))          # 번호 뒤에 붙은 제목은 주소가 아니다
        self.assertTrue(check.needs("See section 4.3.The operator registers."))

    def test_screen_names_in_quotes_may_stay_in_a_registry_manual_only(self):
        for line in ("“Start Request for change”.", "• \"Accept deregistration\", \"Decide to deregister\", \"Decide not to deregister\"", "▪ “Please explain emissions factor calculation” (an..256)."):
            self.assertEqual(check.problems(line, line, screen=True)["hard"], [], line)
            self.assertIn("국문으로 옮기지 않음", check.problems(line, line)["hard"], line)   # 법령과 가이던스에서는 따옴표 안의 글도 옮긴다
        # 따옴표 밖에 글이 있으면 안내서에서도 막는다
        self.assertIn("국문으로 옮기지 않음", check.problems("Click on “Start Request for change” to begin.", "Click on “Start Request for change” to begin.", screen=True)["hard"])

    def test_a_paragraph_set_aside_as_an_exception_is_noted_not_stopped(self):
        source = "(a) prevent any unauthorised person from having access to installations used for the processing of data;"
        korean = "(a) 권한 없는 자가 데이터 처리에 사용되는 설비에 접근하지 못하게 한다"
        self.assertTrue(any(why.startswith("용어집의 표기가 없음: installation") for why in check.problems(source, korean)["hard"]))
        found = check.problems(source, korean, excused=True)
        self.assertEqual(found["hard"], [])
        self.assertTrue(found["soft"][0].startswith("예외로 둔 문단: 용어집의 표기가 없음: installation"))
        # 예외로 둔 문단이라도 수가 빠진 것은 막는다
        self.assertIn("원문의 수가 빠짐: 5", check.problems("Article 5 applies to installations.", "이 조는 설비에 적용한다.", excused=True)["hard"])
        # 예외는 열쇠로 적은 문단에만 듣는다(sources/translation.json의 excused)
        self.assertEqual(apply.judge("없는열쇠", "32023R1773", source, korean)["hard"], check.problems(source, korean)["hard"])
        self.assertEqual(apply.judge("bbe39ebe2c13", "32023R1773", source, korean)["hard"], [])

    def test_translations_are_sorted_into_accepted_and_rejected(self):
        known = {"aaa": ("32099R0001", "Annex IV applies from 2030."), "bbb": ("32099R0001", "Scope")}
        accepted, rejected, noted = apply.sort({"aaa": "부속서 IV는 2030년부터 적용한다.", "bbb": "", "zzz": "없는 열쇠"}, known)
        self.assertEqual(accepted, {"32099R0001": {"aaa": "부속서 IV는 2030년부터 적용한다."}})
        self.assertEqual(sorted(key for key, _ in rejected), ["bbb", "zzz"])


class GlossTest(unittest.TestCase):
    def test_the_first_use_of_a_core_term_in_a_part_gets_its_english(self):
        blocks = [["The embedded emissions of goods are declared.", "제품의 내재배출량을 신고한다."],
                  ["Embedded emissions are verified.", "내재배출량은 검증을 받는다."],
                  ["A table of numbers", "숫자 표"], ["12", "12"], ["Not yet translated", ""]]
        done = gloss.annotate(blocks)
        self.assertIn("내재배출량(embedded emissions)", done[0][1])
        self.assertNotIn("(emissions)", done[0][1])  # 더 긴 낱말의 일부인 자리에는 붙이지 않는다
        self.assertEqual(done[1][1], "내재배출량은 검증을 받는다.")  # 같은 조각에서는 한 번만
        self.assertEqual([row[1] for row in done[2:]], ["숫자 표", "12", ""])
        self.assertEqual(blocks[0][1], "제품의 내재배출량을 신고한다.")  # 넘겨받은 값은 건드리지 않는다

    def test_no_english_is_added_when_the_source_does_not_use_the_term(self):
        self.assertEqual(gloss.annotate([["The amount is declared.", "내재배출량을 신고한다."]])[0][1], "내재배출량을 신고한다.")


class RepositoryTest(unittest.TestCase):
    """저장소에 받아 둔 법령과 번역으로 본다."""

    def test_the_catalogue_starts_with_the_cbam_regulation_and_knows_the_rules(self):
        acts = catalog.acts()
        self.assertGreaterEqual(len(acts), 10)
        self.assertEqual((acts[0]["id"], acts[0]["rule"]), ("32023R0956", "cbam-regulation"))
        self.assertTrue(acts[0]["consolidated"])
        self.assertEqual(acts[-1]["id"], "32023R1773")  # 전환기간이 끝난 법령은 맨 뒤
        self.assertEqual(catalog.official("32025R2548", ["COMMISSION IMPLEMENTING REGULATION (EU) 2025/2548"]), "Commission Implementing Regulation (EU) 2025/2548")

    def test_every_stored_translation_still_passes_the_checks(self):
        known = apply.sources()
        failed = [(key, apply.judge(key, *known[key], text)["hard"]) for key, text in store.load_all().items() if key in known and apply.judge(key, *known[key], text)["hard"]]
        self.assertEqual(failed, [])

    def test_site_data_is_built_with_contents_translations_and_search_rows(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertGreaterEqual(build.write(folder), 10)
            index = json.loads((pathlib.Path(folder) / "laws/index.json").read_text(encoding="utf-8"))["acts"]
            base = json.loads((pathlib.Path(folder) / "laws/32023R0956.json").read_text(encoding="utf-8"))
            rows = json.loads((pathlib.Path(folder) / "laws/search.json").read_text(encoding="utf-8"))["rows"]
        self.assertEqual(index[0]["id"], "32023R0956")
        self.assertGreaterEqual(index[0]["articles"], 36)
        self.assertTrue(all(entry["id"] and entry["ko"] for entry in index[0]["toc"]))
        first = next(part for part in base["parts"] if part["id"] == "art-1")
        self.assertEqual((first["ko"], first["title"]), ("제1조", "Subject matter"))
        self.assertTrue(all(len(block) == 2 for part in base["parts"] for block in part["blocks"]))
        self.assertTrue(any(row["a"] == "32023R0956" and row["p"] == "art-22" and "surrender" in row["x"] for row in rows))
        self.assertFalse(any(row["p"] in ("front", "closing", "notes") for row in rows))

    def test_the_next_batch_follows_the_order_of_the_text_and_skips_what_is_done(self):
        picked, left = todo.pick(limit=3000, act_id=catalog.BASE_CELEX, memory={})  # 어느 실행이 맡든 한 문서 안의 차례는 같다
        self.assertTrue(picked)
        again, _ = todo.pick(limit=3000, act_id=catalog.BASE_CELEX, memory={picked[0]["key"]: "옮긴 문단"})
        self.assertNotIn(picked[0]["key"], [block["key"] for block in again])
        self.assertEqual(again[0]["key"], picked[1]["key"])
        self.assertLessEqual(sum(len(block["text"]) for block in picked[:-1]), 3000)
        acts, _ = corpus.everything()
        order = [store.key(text) for _, parts in acts for part in parts for text in corpus.texts(part)]
        places = [order.index(block["key"]) for block in picked]
        self.assertEqual(places, sorted(places))

    def test_signatures_and_footnotes_come_after_everything_else(self):
        parts = next(found for act, found in corpus.everything()[0] if act["id"] == catalog.BASE_CELEX)
        body = {store.key(text): "옮긴 문단" for part in parts if part["kind"] not in todo.SKIPPED for text in corpus.texts(part)}
        first, _ = todo.pick(limit=3000, act_id=catalog.BASE_CELEX, memory={})
        self.assertFalse({block["part"] for block in first} & {"closing", "notes"})
        last, _ = todo.pick(limit=10**6, act_id=catalog.BASE_CELEX, memory=body)
        self.assertTrue(last and {block["part"] for block in last} <= {"closing", "notes"})


class HoldTest(unittest.TestCase):
    """검사에 거듭 걸리는 문단이 줄의 앞을 막지 않게 한다(그런 문단이 쌓여 묶음을 채우면 번역이 나아가지 못한다)."""

    def test_rejections_are_counted_and_cleared_when_the_translation_gets_in(self):
        with tempfile.TemporaryDirectory() as folder, unittest.mock.patch.object(store, "FOLDER", folder):
            store.save("act-1", {"aaa": "옮긴 문단"}, day="2026-11-01", checked={"aaa"})
            self.assertEqual(store.hold("act-1", "bbb", "국문으로  옮기지 않음"), 1)
            self.assertEqual(store.hold("act-1", "bbb", "원문의 수가 빠짐: 3"), 2)
            self.assertEqual(store.hold("act-2", "ccc", "번역이 비어 있음"), 1)  # 아직 번역이 없는 문서
            self.assertEqual(store.held_all(), {"bbb": {"tries": 2, "why": "원문의 수가 빠짐: 3"}, "ccc": {"tries": 1, "why": "번역이 비어 있음"}})
            body = json.loads(pathlib.Path(folder, "act-1.json").read_text(encoding="utf-8"))
            self.assertEqual((body["updated"], body["blocks"], body["checked"]), ("2026-11-01", {"aaa": "옮긴 문단"}, ["aaa"]))  # 번역, 검수 기록, 날은 그대로
            self.assertNotIn("updated", json.loads(pathlib.Path(folder, "act-2.json").read_text(encoding="utf-8")))  # 옮긴 적 없는 문서에 날을 적지 않는다
            self.assertEqual(store.load_all(), {"aaa": "옮긴 문단"})
            store.save("act-1", {"aaa": "옮긴 문단", "bbb": "이제 들어간 문단"})
            self.assertEqual(sorted(store.held_all()), ["ccc"])  # 번역이 들어가면 빠진다
            self.assertEqual(store.load_checked("act-1"), {"aaa"})

    def test_apply_notes_each_rejection_but_not_a_dry_run(self):
        picked, _ = todo.pick(limit=500, act_id=catalog.BASE_CELEX, memory={})
        key = picked[0]["key"]
        with tempfile.TemporaryDirectory() as folder, tempfile.TemporaryDirectory() as inbox, unittest.mock.patch.object(store, "FOLDER", folder):
            source = pathlib.Path(inbox, "ko.json")
            source.write_text(json.dumps({"blocks": {key: " ", "없는열쇠": "원문에 없는 문단"}}, ensure_ascii=False), encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(apply.main([str(source), "--dry"]), 1)
                self.assertEqual(store.held_all(), {})
                self.assertEqual(apply.main([str(source)]), 1)
                self.assertEqual(apply.main([str(source)]), 1)
            self.assertEqual(store.held_all(), {key: {"tries": 2, "why": "번역이 비어 있음"}})  # 원문에 없는 열쇠는 적을 곳이 없다

    def test_held_paragraphs_are_listed_and_given_out_again_after_a_reset(self):
        picked, _ = todo.pick(limit=500, act_id=catalog.BASE_CELEX, memory={})
        key = picked[0]["key"]
        with tempfile.TemporaryDirectory() as folder, unittest.mock.patch.object(store, "FOLDER", folder):
            store.save("act-1", {"aaa": "옮긴 문단"}, day="2026-11-01")
            for _ in range(store.GIVE_UP):
                store.hold("act-1", key, "용어집의 표기가 없음: installation → 사업장")
            store.hold("act-1", "없는열쇠", "지금의 문서에 없는 문단")
            store.hold("act-2", "bbb", "원문의 수가 빠짐: 3")
            listed = held.rows()
            self.assertEqual([(row["key"], row["act"], row["tries"]) for row in listed], [(key, catalog.BASE_CELEX, store.GIVE_UP)])  # 지금의 문서에 있는 것만
            self.assertEqual(listed[0]["text"], picked[0]["text"])
            self.assertEqual(held.reset([key]), 1)
            self.assertEqual(sorted(store.held_all()), ["bbb", "없는열쇠"])
            self.assertEqual(store.load("act-1"), {"aaa": "옮긴 문단"})  # 번역은 그대로
            self.assertEqual(held.reset(), 2)
            self.assertEqual(store.held_all(), {})
            self.assertNotIn("held", json.loads(pathlib.Path(folder, "act-1.json").read_text(encoding="utf-8")))

    def test_paragraphs_that_keep_failing_go_to_the_back_of_the_queue(self):
        first, _ = todo.pick(limit=3000, act_id=catalog.BASE_CELEX, memory={})
        stuck = first[0]["key"]
        tried = lambda count: {stuck: {"tries": count, "why": "원문의 수가 빠짐: 3"}}
        # 두 번 걸린 문단은 아직 제자리에서 나온다(한 실행이 세 번까지 넣어 본다)
        same, _ = todo.pick(limit=3000, act_id=catalog.BASE_CELEX, memory={}, held=tried(store.HOLD_AFTER - 1))
        self.assertEqual(same[0]["key"], stuck)
        # 세 번 걸리면 뒤로 돌린다: 그 자리를 다음 문단이 채우고, 남은 분량에 따로 센다
        moved, left = todo.pick(limit=3000, act_id=catalog.BASE_CELEX, memory={}, held=tried(store.HOLD_AFTER))
        self.assertNotIn(stuck, [block["key"] for block in moved])
        self.assertEqual((moved[0]["key"], left["held"]), (first[1]["key"], 1))
        # 조각을 가리켜 달라고 하면 가리지 않는다
        asked, _ = todo.pick(limit=3000, act_id=catalog.BASE_CELEX, part_id=first[0]["part"], memory={}, held=tried(store.GIVE_UP))
        self.assertEqual(asked[0]["key"], stuck)
        # 다른 문단을 모두 옮긴 뒤에 한 번 더 나오고, 그때도 걸려 여섯 번이 되면 더 나오지 않는다
        parts = next(found for act, found in corpus.everything()[0] if act["id"] == catalog.BASE_CELEX)
        rest = {store.key(text): "옮긴 문단" for part in parts for text in corpus.texts(part) if store.key(text) != stuck}
        last, left = todo.pick(limit=3000, act_id=catalog.BASE_CELEX, memory=rest, held=tried(store.HOLD_AFTER))
        self.assertEqual(([block["key"] for block in last], left["held"]), ([stuck], 0))
        none, left = todo.pick(limit=3000, act_id=catalog.BASE_CELEX, memory=rest, held=tried(store.GIVE_UP))
        self.assertEqual((none, left["held"]), ([], 1))

    def test_the_reason_goes_back_to_the_translator_and_what_is_set_aside_is_shown(self):
        picked, left = todo.pick(limit=500, act_id=catalog.BASE_CELEX, memory={})
        key = picked[0]["key"]
        once = {key: {"tries": 1, "why": "원문의 수가 빠짐: 3"}, "없는열쇠": {"tries": 9, "why": "지금의 문서에 없는 문단"}}
        with unittest.mock.patch.object(store, "held_all", return_value=once):
            self.assertEqual(todo.answer(picked, left)["remarks"][key], "앞에서 검사에 걸림: 원문의 수가 빠짐: 3")
            self.assertEqual(status.held({key}, {}), {})  # 아직 뒤로 돌리지 않은 문단
        late = {key: {"tries": store.GIVE_UP, "why": "원문의 수가 빠짐: 3"}, "없는열쇠": {"tries": 9, "why": "지금의 문서에 없는 문단"}}
        with unittest.mock.patch.object(store, "held_all", return_value=late):
            self.assertEqual(sorted(status.held({key}, {})), [key])
            self.assertEqual(status.held({key}, {key: "옮긴 문단"}), {})  # 번역이 들어간 문단은 세지 않는다
        with unittest.mock.patch.object(status, "held", return_value={key: late[key]}):
            self.assertEqual(laws_health._held_problems(), [f"번역: 검사에 거듭 걸려 싣지 못한 문단 1개: {key}(원문의 수가 빠짐: 3)"])
        with unittest.mock.patch.object(status, "held", return_value={}):
            self.assertEqual(laws_health._held_problems(), [])


ENGINE = """
import { find, makeIndex, marks, parse, split } from './site/js/laws/engine.js';
const index = makeIndex([{ en: 'embedded emissions', ko: '내재배출량', abbr: '', alt: '', article: 'CBAM 규정 제7조(7)·제8조(3)' },
  { en: 'surrender (of CBAM certificates)', ko: '제출', abbr: '', alt: '' }, { en: 'EU Emissions Trading System', ko: 'EU 배출권거래제', abbr: 'EU ETS', alt: '' }]);
const rows = [
  { a: '32023R0956', p: 'art-7', n: '제7조', t: 'Calculation of embedded emissions', k: '내재배출량의 산정', x: 'Embedded emissions in goods shall be calculated.\\nSecond line.', y: '' },
  { a: '32023R0956', p: 'art-22', n: '제22조', t: 'Surrender of CBAM certificates', k: 'CBAM 인증서의 제출', x: 'The declarant shall surrender certificates by 30 September.', y: '신고인은 9월 30일까지 인증서를 제출한다.' },
  { a: '32023R1773', p: 'art-3', n: '제3조', t: 'Reporting obligations', k: '', x: 'Embedded emissions are reported.', y: '' },
  { a: '32025R2548', p: 'recitals', n: '전문', t: '', k: '', x: 'Nothing relevant here.', y: '' }];
const asked = parse('내재배출량은 어디에서 정하나요?', index);
const found = find(rows, asked, { limit: 5 });
const dated = find(rows, parse('인증서는 언제까지 제출하나요', index), { limit: 5 });
console.log(JSON.stringify({ labels: asked.groups.map((group) => group.label), order: found.map((hit) => hit.row.a + '.' + hit.row.p), first: found[0].snippet,
  dated: dated[0].row.p, datedLang: dated[0].snippet.lang, abbr: parse('eu ets', index).groups.map((group) => group.label), none: find(rows, parse('어디에 있나요', index)).length,
  marks: marks(asked), pieces: split('Embedded emissions in goods', ['embedded emissions']), quoted: parse('"30 September"', index).groups[0].en }));
"""


@unittest.skipUnless(shutil.which("node"), "node가 없으면 화면의 찾기는 시험하지 않는다")
class EngineTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        done = subprocess.run(["node", "--input-type=module", "-e", ENGINE], capture_output=True, text=True, check=True)
        cls.seen = json.loads(done.stdout)

    def test_a_korean_question_finds_the_article_through_the_glossary(self):
        self.assertEqual(self.seen["labels"], ["내재배출량", "정하나요"][:1] + self.seen["labels"][1:])
        self.assertEqual(self.seen["order"][0], "32023R0956.art-7")  # 조의 이름에 나오고 용어집이 가리키는 조가 맨 앞
        self.assertLess(self.seen["order"].index("32023R0956.art-7"), self.seen["order"].index("32023R1773.art-3"))  # 전환기간 법령은 뒤로
        self.assertEqual(self.seen["first"], {"text": "Embedded emissions in goods shall be calculated.", "lang": "en"})

    def test_translated_articles_answer_in_korean_and_question_words_are_dropped(self):
        self.assertEqual((self.seen["dated"], self.seen["datedLang"]), ("art-22", "ko"))
        self.assertEqual(self.seen["none"], 0)  # 물음말만 있는 질문에는 찾을 낱말이 없다
        self.assertEqual(self.seen["abbr"], ["EU 배출권거래제"])

    def test_marks_and_exact_phrases(self):
        self.assertIn("embedded emissions", self.seen["marks"])
        self.assertEqual(self.seen["pieces"], [["Embedded emissions", True], [" in goods", False]])
        self.assertEqual(self.seen["quoted"], ["30 september"])


if __name__ == "__main__":
    unittest.main()
