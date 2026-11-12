"""규정 원문: 법령 글 나누기, 번역의 열쇠와 검사, 영문 병기, 사이트 자료 만들기, 전체 규정에서 찾기."""
import json
import pathlib
import shutil
import subprocess
import tempfile
import unittest

from tools.laws import apply, build, catalog, check, corpus, gloss, segment, store, terms, todo

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
        failed = [(key, check.problems(known[key][1], text)["hard"]) for key, text in store.load_all().items() if key in known and check.problems(known[key][1], text)["hard"]]
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
