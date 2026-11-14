"""CBAM 해설서: 글의 검사(tools.publish.handbook)와, 실린 글(data/handbook.json)의 수치가 다른 참고 자료와 맞는지."""
import copy
import json
import pathlib
import re
import tempfile
import unittest

from tools.check import term_check
from tools.common.jsonio import read_json
from tools.publish import handbook, handbook_figures
from tools.run import reference_health

LAW_TEXT = "1. Embedded emissions in goods shall be calculated pursuant to the methods set out in Annex IV."
STORED_TEXT = "The excess emissions penalty shall be EUR 100 for each tonne of carbon dioxide equivalent emitted."


def section(**extra):
    base = {"id": "purpose", "title": "제도의 목적", "body": ["내재배출량은 부속서 IV의 방법으로 산정합니다."],
            "basis": [{"act": "32023R0956", "part": "art-7", "contains": ["Embedded emissions in goods shall be calculated"]}]}
    base.update(extra)
    return base


def book(*sections, **extra):
    body = {"asOf": "2026-11-14", "lead": "제도가 돌아가는 차례를 풀어 쓴 글입니다.",
            "chapters": [{"id": "overview", "title": "CBAM 한눈에 보기", "lead": "제도를 간추립니다.", "sections": list(sections) or [section()]}]}
    body.update(extra)
    return body


def blocking(body, **options):
    return [what for _, what in handbook.blocking(handbook.problems(body, **options))]


class FormatTest(unittest.TestCase):
    def test_a_plain_section_passes(self):
        self.assertEqual(handbook.problems(book()), [])

    def test_text_must_be_polite_and_titles_noun_phrases(self):
        self.assertTrue(any("표기" in what for what in blocking(book(section(body=["내재배출량은 부속서 IV의 방법으로 산정한다."])))))
        self.assertIn("제목은 명사로 끝나는 구로 적음", blocking(book(section(title="제도의 목적을 설명합니다"))))
        self.assertIn("문장이 마침표로 끝나지 않음", blocking(book(section(body=["내재배출량의 산정"]))))
        self.assertTrue(any("글이 김" in what for what in blocking(book(section(body=["가" * 430 + "입니다."])))))

    def test_shapes_of_the_optional_parts_are_checked(self):
        self.assertIn("문단은 1~5개여야 함", blocking(book(section(body=[]))))
        self.assertIn("표는 머리와 같은 칸 수의 줄들이어야 함", blocking(book(section(table={"head": ["가", "나"], "rows": [["하나"]]}))))
        self.assertIn("식은 {text, parts: [[말, 풀이]]} 꼴이어야 함", blocking(book(section(formula={"text": "가 = 나", "parts": [["가"]]}))))
        self.assertIn("용어 풀이에 ko, en, text가 있어야 함", blocking(book(section(terms=[{"ko": "기본값", "text": "풀이입니다."}]))))
        self.assertIn("근거 조문은 1~10개여야 함", blocking(book(section(basis=[]))))
        self.assertIn("근거 대목은 원문의 영문 그대로 20자 이상이어야 함", blocking(book(section(basis=[{"act": "32023R0956", "part": "art-7", "contains": ["Annex IV"]}]))))
        good = section(list=["첫째 항목입니다.", "둘째 항목입니다."], ordered=True, formula={"text": "가 = 나 × 다", "parts": [["나", "곱하는 값입니다."]]},
                       table={"head": ["연도", "값"], "rows": [["2026년", "97.5%"]]}, terms=[{"ko": "기본값", "en": "default value", "text": "2차 데이터로 정한 값입니다."}],
                       caveat="늦어도 2027년에 개정합니다.", see=[{"href": "#calc", "text": "인증서 비용 추정"}])
        self.assertEqual(handbook.problems(book(good)), [])

    def test_the_address_of_the_whole_book_is_not_a_chapter_name(self):
        body = book()
        body["chapters"][0]["id"] = "all"   # #handbook-all은 해설서 전체를 한 화면에 놓는 주소다
        self.assertIn("장의 id로 'all'은 쓰지 않음(해설서 전체를 한 화면에 놓는 주소다)", blocking(body))

    def test_a_sentence_that_points_at_the_list_sits_right_before_it(self):
        items = ["첫째 항목입니다.", "둘째 항목입니다."]
        apart = section(body=["신고서를 냅니다. 신고서에는 아래 내용이 들어갑니다.", "기록은 4년 동안 보관합니다."], list=items)
        self.assertEqual(blocking(book(apart)), ["목록을 가리키는 문장은 본문의 마지막 문단에 둠"])
        self.assertEqual(blocking(book(section(body=["법은 다음을 예로 듭니다.", "조사는 9개월 안에 마칩니다."], list=items))), ["목록을 가리키는 문장은 본문의 마지막 문단에 둠"])
        together = section(body=["기록은 4년 동안 보관합니다.", "신고서에는 아래 내용이 들어갑니다."], list=items)
        self.assertEqual(blocking(book(together)), [])
        early = section(body=["아래 네 가지 기준을 모두 갖추어야 합니다. 담보를 요구할 수 있습니다.", "잠정적으로 수입을 이어 갈 수 있습니다."], list=items)
        self.assertEqual(blocking(book(early)), ["목록을 가리키는 문장은 본문의 마지막 문단에 둠"])
        # 목록이 없는 절이나, 표와 절을 가리키는 말은 보지 않는다
        self.assertEqual(blocking(book(section(body=["세 값은 아래 절에서 설명합니다.", "식은 같은 꼴입니다."]))), [])
        self.assertEqual(blocking(book(section(body=["아래 표의 비율만큼 올립니다. 비료는 1%입니다.", "분기 말에는 더하지 않습니다."], list=items))), [])

    def test_the_same_term_is_explained_only_once(self):
        term = {"ko": "기본값", "en": "default value", "text": "2차 데이터로 정한 값입니다."}
        found = blocking(book(section(terms=[term]), section(id="again", terms=[dict(term)])))
        self.assertEqual(found, ["용어 '기본값'의 풀이가 겹침(overview.purpose에 이미 있음)"])

    def test_links_must_point_at_places_that_exist(self):
        def see(href):
            return blocking(book(section(see=[{"href": href, "text": "관련 화면"}])), rules={"cbam-regulation"})
        self.assertEqual(see("#calc-72081000"), [])
        self.assertEqual(see("#handbook-overview.purpose"), [])
        self.assertEqual(see("#rules-cbam-regulation"), [])
        self.assertEqual(see("#nowhere"), ["사이트에 없는 주소: #nowhere"])
        self.assertEqual(see("#handbook-missing"), ["해설서에 없는 곳: #handbook-missing"])
        self.assertEqual(see("#handbook-overview.missing"), ["해설서에 없는 곳: #handbook-overview.missing"])
        self.assertEqual(see("#rules-gone"), ["규제 화면에 없는 곳: #rules-gone"])
        # 규제의 목록을 넘기지 않으면(따로 돌리는 검사) 규제의 이름은 보지 않는다
        self.assertEqual(blocking(book(section(see=[{"href": "#rules-gone", "text": "규제"}]))), [])

    def test_a_source_outside_the_site_must_be_declared(self):
        outside = section(basis=[{"source": "ets-directive", "label": "제16조(3)", "contains": ["The excess emissions penalty shall be EUR 100"]}])
        self.assertEqual(blocking(book(outside)), ["sources에 없는 근거 문서: ets-directive"])
        self.assertEqual(blocking(book(outside, sources={"ets-directive": {"text": "EU 배출권거래제 지침", "url": "http://x.example", "path": "x.txt"}})),
                         ["ets-directive: text, url(https), path가 있어야 함"])


FIGURES = {
    "flow": {"kind": "flow", "title": "수입에서 신고까지의 차례", "numbered": True, "links": ["다음"],
             "steps": [{"title": "수입", "text": "제품을 들여옴", "tag": "수입자"}, {"title": "신고"}]},
    "timeline": {"kind": "timeline", "title": "첫 해의 일정", "note": "칸의 간격은 기간의 길이와 비례하지 않습니다.",
                 "bands": [{"label": "2027년", "text": "첫 신고", "marks": [{"date": "2027-02-01", "edge": "부터", "label": "인증서 판매"},
                                                                         {"when": "2027년 각 분기 말", "label": "인증서 보유"}]}]},
    "tiles": {"kind": "tiles", "title": "대상 부문", "items": [{"icon": "steel", "title": "철강", "text": "이산화탄소", "href": "#calc"}, {"title": "비료"}]},
    "matrix": {"kind": "matrix", "title": "산정에 넣는 배출량", "cols": ["직접배출량", "간접배출량"], "yes": "넣음", "no": "넣지 않음",
               "rows": [{"title": "시멘트", "cells": [True, True]}, {"title": "철강", "text": "제72류", "cells": [True, False]}]},
    "lanes": {"kind": "lanes", "title": "두 쪽이 하는 일", "handover": "사업자의 자료",
              "lanes": [{"title": "생산자", "items": ["배출량을 산정"]}, {"title": "수입자", "items": ["신고서를 제출", "인증서를 제출"]}]},
    "equation": {"kind": "equation", "title": "인증서 수의 틀", "terms": [{"label": "인증서 수"}, {"label": "내재배출량", "text": "제품 1톤당"}, {"label": "수입량"}], "ops": ["=", "×"]},
    "bars": {"kind": "bars", "title": "연도별 마크업", "unit": "%", "groups": ["2026년", "2027년"], "series": [{"name": "철강", "values": [10, 20]}, {"name": "비료", "values": [1, 1]}]},
    "split": {"kind": "split", "title": "내재배출량의 몫", "unit": "tCO2e", "whole": {"label": "내재배출량", "value": 2.33},
              "parts": [{"label": "무상할당량", "value": 1.336}, {"label": "제출할 인증서", "value": 0.994}]},
    "factor": {"kind": "factor", "title": "CBAM 계수의 연도별 값", "path": "current"},
}


def figure_problems(figure, **options):
    return blocking(book(section(figure=figure)), **options)


class FigureTest(unittest.TestCase):
    """절의 그림(figure): 꼴은 tools/publish/handbook_figures.py가 본다."""

    def test_every_kind_has_a_shape_that_passes(self):
        self.assertEqual(set(FIGURES), set(handbook_figures.KINDS))
        for kind, figure in FIGURES.items():
            self.assertEqual(handbook.problems(book(section(figure=figure))), [], kind)

    def test_a_figure_needs_a_known_kind_and_a_title(self):
        self.assertIn("그림의 종류를 모름: 'pie'", figure_problems({"kind": "pie", "title": "몫"}))
        self.assertIn("그림의 꼴이 다름", figure_problems(["flow"]))
        self.assertIn("title이 빔", figure_problems({**FIGURES["factor"], "title": ""}))
        self.assertTrue(any(what.startswith("title이 너무 김") for what in figure_problems({**FIGURES["factor"], "title": "가" * 41})))

    def test_the_parts_of_each_kind_must_fit_together(self):
        changed = lambda kind, **parts: figure_problems({**FIGURES[kind], **parts})
        self.assertIn("steps은 2~7개여야 함", changed("flow", steps=[{"title": "수입"}]))
        self.assertIn("links는 steps보다 하나 적어야 함", changed("flow", links=["다음", "그다음"]))
        self.assertTrue(any(what.startswith("links 1이 너무 김") for what in changed("flow", links=["길게 적은 화살표의 말"])))
        mark = {"date": "2027-02-01", "when": "2027년", "label": "인증서 판매"}
        self.assertIn("bands 1의 marks 1에는 date와 when 가운데 하나만 적음", changed("timeline", bands=[{"label": "2027년", "marks": [mark]}]))
        self.assertIn("bands 1의 marks 1의 date는 2027-02-01 꼴이어야 함", changed("timeline", bands=[{"label": "2027년", "marks": [{"date": "2027년 2월", "label": "판매"}]}]))
        self.assertIn("bands 1의 marks 1의 edge는 '부터'나 '까지'여야 함", changed("timeline", bands=[{"label": "2027년", "marks": [{"date": "2027-02-01", "edge": "쯤", "label": "판매"}]}]))
        self.assertIn("marks가 하나도 없음", changed("timeline", bands=[{"label": "2027년", "marks": []}]))
        self.assertIn("items 1의 href는 사이트 안의 주소(#…)여야 함", changed("tiles", items=[{"title": "철강", "href": "https://example.org/"}, {"title": "비료"}]))
        self.assertIn("rows 1의 cells는 cols와 같은 수의 true·false여야 함", changed("matrix", rows=[{"title": "시멘트", "cells": [True]}, {"title": "철강", "cells": [True, False]}]))
        self.assertIn("lanes은 2~2개여야 함", changed("lanes", lanes=[{"title": "생산자", "items": ["배출량을 산정"]}]))
        self.assertTrue(any(what.startswith("ops는 terms보다 하나 적어야 하고") for what in changed("equation", ops=["="])))
        self.assertIn("ops에는 = 가 하나 있어야 함", changed("equation", ops=["×", "×"]))
        self.assertIn("series 1의 values는 groups와 같은 수의 0 이상인 수여야 함", changed("bars", series=[{"name": "철강", "values": [10]}]))
        self.assertIn("parts의 합이 whole과 다름", changed("split", parts=[{"label": "무상할당량", "value": 1.3}, {"label": "제출할 인증서", "value": 0.994}]))
        self.assertIn("path에 data/factor.json의 경로 이름을 적음", changed("factor", path=""))

    def test_a_figure_can_be_placed_before_the_last_paragraphs(self):
        # after: 그림 앞에 오는 문단의 수. 목록을 가리키는 마지막 문단이 목록과 떨어지지 않게 그림을 앞으로 올릴 때 쓴다
        wrong = "after는 그림 앞에 오는 문단의 수로, 1부터 문단 수보다 하나 적은 수까지 적음"
        three = ["첫 문단입니다.", "둘째 문단입니다.", "셋째 문단입니다."]
        placed = lambda after: [what for _, what in handbook.problems(book(section(body=three, figure={**FIGURES["tiles"], "after": after})))]
        self.assertEqual(placed(1), [])
        self.assertEqual(placed(2), [])
        for after in (0, 3, 4, "1", True, 1.5):
            self.assertIn(wrong, placed(after), after)
        self.assertEqual(handbook.public(book(section(body=three, figure={**FIGURES["tiles"], "after": 2})))["chapters"][0]["sections"][0]["figure"]["after"], 2)

    def test_the_words_and_links_of_a_figure_are_checked_like_the_text(self):
        # 그림의 글도 용어집이 쓰지 말라는 표기를 쓰지 않고, 그림에서 가는 주소도 실제로 있는 곳이어야 한다
        terms = term_check.load()
        self.assertEqual(figure_problems(FIGURES["bars"], term_index=terms), [])
        self.assertTrue(any(what.startswith("용어: '가산율'") for what in figure_problems({**FIGURES["bars"], "title": "연도별 가산율"}, term_index=terms)))
        self.assertIn("사이트에 없는 주소: #nowhere", figure_problems({**FIGURES["tiles"], "items": [{"title": "철강", "href": "#nowhere"}, {"title": "비료"}]}))

    def test_a_figure_reaches_the_site_as_it_is(self):
        body = book(section(figure=FIGURES["flow"]))
        self.assertEqual(handbook.public(body)["chapters"][0]["sections"][0]["figure"], FIGURES["flow"])


class EvidenceTest(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        root = pathlib.Path(self.folder.name)
        self.laws = root / "laws"
        self.laws.mkdir()
        index = {"acts": [{"id": "32023R0956", "name": "CBAM 규정", "short": "CBAM 규정", "toc": [{"id": "art-7", "kind": "article", "ko": "제7조", "titleKo": "내재배출량의 산정"}]}]}
        (self.laws / "index.json").write_text(json.dumps(index, ensure_ascii=False), encoding="utf-8")
        (self.laws / "32023R0956.json").write_text(json.dumps({"parts": [{"id": "art-7", "blocks": [[LAW_TEXT, "국문"]]}]}, ensure_ascii=False), encoding="utf-8")
        self.stored = root / "directive.txt"
        self.stored.write_text(f"Article 16\n3.   {STORED_TEXT}\n", encoding="utf-8")
        self.sources = {"ets-directive": {"text": "EU 배출권거래제 지침 2003/87/EC", "url": "https://eur-lex.example/ets", "path": str(self.stored)}}

    def found(self, body):
        return handbook.problems(body, laws_dir=self.laws)

    def test_a_phrase_found_in_the_part_is_no_problem(self):
        self.assertEqual(self.found(book()), [])

    def test_a_phrase_that_left_the_law_is_drift_and_does_not_block(self):
        gone = book(section(basis=[{"act": "32023R0956", "part": "art-7", "contains": ["Embedded emissions shall be estimated loosely"]}]))
        found = self.found(gone)
        self.assertEqual(len(found), 1)
        self.assertTrue(found[0][1].startswith("근거 어긋남: 32023R0956 art-7에 없는 대목"))
        self.assertEqual(handbook.blocking(found), [])
        for basis, what in (({"act": "32099R0001", "part": "art-1"}, "규정 원문에 없는 문서 32099R0001"), ({"act": "32023R0956", "part": "art-99"}, "32023R0956에 없는 조각 art-99")):
            body = book(section(basis=[{**basis, "contains": ["Embedded emissions in goods shall be calculated"]}]))
            self.assertEqual([row[1] for row in self.found(body)], [f"근거 어긋남: {what}"])

    def test_spacing_differences_are_not_drift(self):
        spaced = book(section(basis=[{"act": "32023R0956", "part": "art-7", "contains": ["Embedded  emissions in goods\nshall be calculated"]}]))
        self.assertEqual(self.found(spaced), [])

    def test_stored_texts_are_checked_even_without_the_law_data(self):
        def outside(phrase):
            return book(section(basis=[{"source": "ets-directive", "label": "제16조(3)", "contains": [phrase]}]), sources=self.sources)
        self.assertEqual(handbook.problems(outside("The excess emissions penalty shall be EUR 100")), [])
        drift = handbook.problems(outside("The excess emissions penalty shall be EUR 200"))
        self.assertEqual(len(drift), 1)
        self.assertTrue(drift[0][1].startswith("근거 어긋남: ets-directive에 없는 대목"), drift)
        self.assertEqual(handbook.blocking(drift), [])
        lost = copy.deepcopy(self.sources)
        lost["ets-directive"]["path"] = str(self.stored) + ".none"
        body = book(section(basis=[{"source": "ets-directive", "contains": ["The excess emissions penalty shall be EUR 100"]}]), sources=lost)
        self.assertTrue(handbook.problems(body)[0][1].startswith("근거 어긋남: 받아 둔 글을 읽지 못함"))

    def test_the_public_shape_drops_the_phrases_and_names_the_basis(self):
        body = book(section(terms=[{"ko": "기본값", "en": "default value", "text": "2차 데이터로 정한 값입니다."}], list=["첫째입니다."], ordered=True,
                            basis=[{"act": "32023R0956", "part": "art-7", "contains": ["Embedded emissions in goods shall be calculated"]},
                                   {"source": "ets-directive", "label": "제16조(3)", "contains": ["The excess emissions penalty shall be EUR 100"]}]), sources=self.sources)
        public = handbook.public(body, handbook.known_laws(read_json(self.laws / "index.json", None)))
        shown = public["chapters"][0]["sections"][0]
        self.assertEqual(shown["basis"][0]["act"], "32023R0956")
        self.assertIn("제7조", shown["basis"][0]["label"])
        self.assertEqual(shown["basis"][1], {"label": "EU 배출권거래제 지침 2003/87/EC", "url": "https://eur-lex.example/ets", "parts": ["제16조(3)"]})
        self.assertTrue(shown["ordered"])
        self.assertEqual(public["terms"], [{"ko": "기본값", "en": "default value", "text": "2차 데이터로 정한 값입니다.", "chapter": "overview", "section": "purpose"}])
        text = json.dumps(public, ensure_ascii=False)
        for hidden in ("contains", "sources", str(self.stored), "Embedded emissions in goods"):
            self.assertNotIn(hidden, text)


    def test_bases_on_one_outside_document_share_a_line(self):
        # 바깥 문서는 주소가 하나다: 조마다 링크를 두지 않고 문서마다 한 줄에 모은다. 짧은 이름(short)이 있으면 그것을 이름으로, 온전한 이름은 name으로 싣는다
        sources = {**self.sources, "ets-directive": {**self.sources["ets-directive"], "short": "배출권거래제 지침"}}
        body = book(section(basis=[{"source": "ets-directive", "label": "제16조(3)", "contains": ["The excess emissions penalty shall be EUR 100"]},
                                   {"act": "32023R0956", "part": "art-7", "contains": ["Embedded emissions in goods shall be calculated"]},
                                   {"source": "ets-directive", "label": "제16조(4)", "contains": ["for each tonne of carbon dioxide equivalent emitted"]}]), sources=sources)
        self.assertEqual(handbook.problems(body), [])
        shown = handbook.public(body, handbook.known_laws(read_json(self.laws / "index.json", None)))["chapters"][0]["sections"][0]["basis"]
        self.assertEqual(shown[0], {"label": "배출권거래제 지침", "name": "EU 배출권거래제 지침 2003/87/EC", "url": "https://eur-lex.example/ets", "parts": ["제16조(3)", "제16조(4)"]})
        self.assertEqual([row.get("act") for row in shown], [None, "32023R0956"])
        long = {**sources, "ets-directive": {**sources["ets-directive"], "short": "가" * 41}}
        self.assertIn("ets-directive: short는 40자까지의 짧은 이름이어야 함", blocking(book(sources=long)))

    def test_a_scoped_chapter_marks_itself_and_its_terms(self):
        # 다른 제도를 다루는 장(scope): 장과 그 장의 용어 풀이에 범위가 실린다(글 속 용어 풀이가 범위를 가린다)
        body = book(section(terms=[{"ko": "회계기간", "en": "accounting period", "text": "세액을 계산하는 단위 기간입니다."}]))
        body["chapters"][0]["scope"] = "uk"
        self.assertEqual(handbook.problems(body), [])
        public = handbook.public(body)
        self.assertEqual(public["chapters"][0]["scope"], "uk")
        self.assertEqual(public["terms"][0]["scope"], "uk")
        self.assertNotIn("scope", handbook.public(book())["chapters"][0])
        body["chapters"][0]["scope"] = "United Kingdom"
        self.assertTrue(any(what.startswith("scope는") for what in blocking(body)))


class StoredBookTest(unittest.TestCase):
    """실린 글(data/handbook.json)."""

    @classmethod
    def setUpClass(cls):
        cls.book = read_json(handbook.SOURCE, None)
        cls.sections = {f"{chapter['id']}.{one['id']}": one for chapter in cls.book["chapters"] for one in chapter["sections"]}

    def text(self, key):
        one = self.sections[key]
        cells = [cell for row in (one.get("table") or {}).get("rows", []) for cell in row]
        return " ".join(one["body"] + one.get("list", []) + cells + [one.get("caveat", "")])

    def test_it_has_no_problems(self):
        rules = {rule["id"] for rule in read_json("data/regulations.json", {}).get("regulations", [])}
        # 사이트의 규정 원문에 댄 근거는 사이트를 만들 때 본다(여기에서는 꼴과, 받아 둔 글에 댄 근거)
        self.assertEqual(handbook.problems(self.book, term_check.load(), rules=rules), [])
        self.assertEqual(len(self.book["chapters"]), 13)

    def test_the_united_kingdom_chapter_stands_on_stored_british_law(self):
        # 영국 CBAM의 장: 근거는 모두 받아 둔 영국 법령의 글이고(사이트의 규정 원문에 없는 문서), 용어 풀이는 그 장의 범위에서만 쓴다
        chapter = self.book["chapters"][-1]
        self.assertEqual((chapter["id"], chapter.get("scope")), ("uk", "uk"))
        self.assertEqual([one.get("scope") for one in self.book["chapters"][:-1]], [None] * 12)
        used = {basis.get("source") for one in chapter["sections"] for basis in one["basis"]}
        self.assertNotIn(None, used)
        for name in used:
            source = self.book["sources"][name]
            self.assertTrue(source["path"].startswith("collected/archive/pages/uk-legislation/") and source["url"].startswith("https://www.legislation.gov.uk/"), name)
            self.assertTrue(source.get("short"), name)
        # 날짜가 일정 화면의 영국 의무와 같다: 2027년에 등록 의무가 생긴 사람의 등록 기한, 첫 세 회계기간의 신고와 납부 기한
        duties = {duty["id"]: duty["date"] for duty in read_json("data/duties.json", {})["duties"] if duty.get("scheme") == "uk"}
        self.assertIn("2028년 1월 31일까지", self.text("uk.registration"))
        self.assertEqual(duties["uk-registration-deadline"], "2028-01-31")
        rows = dict(self.sections["uk.returns"]["table"]["rows"])
        for period, duty in (("2027년 1월 1일~2027년 12월 31일", "uk-first-return"), ("2028년 1월 1일~2028년 3월 31일", "uk-return-2028-q1"), ("2028년 4월 1일~2028년 6월 30일", "uk-return-2028-q2")):
            year, month, day = (int(part) for part in duties[duty].split("-"))
            self.assertEqual(rows[period], f"{year}년 {month}월 {day}일이 끝날 때까지", period)

    def test_every_basis_points_at_a_law_part_or_a_declared_source(self):
        for key, one in self.sections.items():
            for basis in one["basis"]:
                self.assertTrue(basis.get("source") in self.book["sources"] if basis.get("source") else re.fullmatch(r"[0-9A-Za-z-]+", basis["act"]) and basis.get("part"), key)

    def test_the_factor_table_is_the_one_the_estimate_uses(self):
        current = next(path for path in read_json("data/factor.json", {})["paths"] if path["key"] == "current")
        rows = dict(self.sections["certificates.factor"]["table"]["rows"])
        for year in range(2026, 2034):
            self.assertEqual(float(rows[f"{year}년"].rstrip("%")), current["values"][str(year)], year)
        self.assertEqual(current["values"]["2034"], 0)
        self.assertIn("2034년부터", rows)

    def test_the_markups_and_the_correction_factor_are_the_ones_the_estimate_uses(self):
        terms = read_json("data/calc.json", {})
        rows = {row[0]: row[1:] for row in self.sections["defaults.markup"]["table"]["rows"]}
        by_sector = {tuple(group["sectors"]): group["values"] for group in terms["markups"]}
        self.assertEqual(rows["시멘트, 철강, 알루미늄, 수소"], [f"{by_sector[('cement', 'steel', 'aluminium', 'hydrogen')][year]}%" for year in ("2026", "2027", "2028")])
        self.assertEqual(set(rows["비료"]), {f"{by_sector[('fertilisers',)]['2026']}%"})
        self.assertEqual({terms["cscf"]["values"][str(year)] for year in range(2026, 2031)}, {100})
        self.assertIn("해마다 100%로 정했습니다", self.text("certificates.cscf"))

    def test_the_worked_example_follows_the_stored_tables(self):
        goods = read_json("data/calc-goods.json", {})
        good = next(one for one in goods["goods"] if one["code"] == "72081000")
        choice = good["defaults"][0]
        row = goods["rows"][choice["row"]]
        self.assertEqual((row["origin"], row["shown"], choice["route"]), ("kr", "7208", "C"))
        terms = read_json("data/calc.json", {})
        markup = next(group for group in terms["markups"] if "steel" in group["sectors"])["values"]["2026"]
        factor = next(path for path in read_json("data/factor.json", {})["paths"] if path["key"] == "current")["values"]["2026"]
        cscf = terms["cscf"]["values"]["2026"]
        embedded = row["total"] * (1 + markup / 100)
        allocation = choice["benchmark"][0] * factor / 100 * cscf / 100
        text = self.text("certificates.example")
        for piece in (f"{row['total']:.3f}", f"{choice['benchmark'][0]:.3f}", f"{markup}%", f"{factor}%", f"{cscf}%", f"{embedded:.3f}", f"{allocation:.3f}",
                      f"{embedded - allocation:.3f}", f"{(embedded - allocation) * 100:.1f}", "(C)", "7208 10 00"):
            self.assertIn(piece, text, piece)
        self.assertEqual(self.sections["certificates.example"]["see"][0]["href"], "#calc-72081000")


class StoredFiguresTest(unittest.TestCase):
    """실린 글의 그림: 그림은 그 절의 글을 한눈에 보이게 한 것이므로, 글에 없는 수나 날짜를 그림에만 적지 않는다."""

    NUMBER = re.compile(r"\d+(?:[.,]\d+)*")

    @classmethod
    def setUpClass(cls):
        cls.book = read_json(handbook.SOURCE, None)
        cls.sections = {f"{chapter['id']}.{one['id']}": one for chapter in cls.book["chapters"] for one in chapter["sections"]}
        cls.figures = {key: one["figure"] for key, one in cls.sections.items() if one.get("figure")}

    def text(self, key):
        """절에 적힌 모든 글: 제목, 문단, 목록, 표, 식과 풀이, 용어 풀이, 단서."""
        one = self.sections[key]
        table = one.get("table") or {}
        formula = one.get("formula") or {}
        pieces = [one["title"], *one["body"], *one.get("list", []), *table.get("head", []), *(cell for row in table.get("rows", []) for cell in row),
                  formula.get("text", ""), *(word for pair in formula.get("parts", []) for word in pair),
                  *(word for term in one.get("terms", []) for word in (term["ko"], term["text"])), one.get("caveat", "")]
        return " ".join(pieces)

    def test_the_book_has_figures_of_several_kinds(self):
        self.assertGreaterEqual(len(self.figures), 23)
        self.assertGreaterEqual(len({figure["kind"] for figure in self.figures.values()}), 7)

    def test_a_figure_shows_no_number_the_section_does_not_state(self):
        for key, figure in self.figures.items():
            stated = set(self.NUMBER.findall(self.text(key)))
            # CBAM 계수의 그림은 적용하지 않는 해를 0으로 그렸다고 밝힌다(그 말의 0은 그림을 두고 한 말이다)
            allowed = {"0"} if figure["kind"] == "factor" else set()
            for text in handbook_figures.texts(figure):
                for number in self.NUMBER.findall(text):
                    self.assertIn(number, stated | allowed, f"{key}: {text}")

    def test_the_dates_of_a_timeline_are_stated_in_the_section(self):
        seen = 0
        for key, figure in self.figures.items():
            if figure["kind"] != "timeline":
                continue
            text = self.text(key)
            for band in figure["bands"]:
                for mark in band["marks"]:
                    if mark.get("date"):
                        year, month, day = (int(part) for part in mark["date"].split("-"))
                        self.assertIn(f"{year}년 {month}월 {day}일{mark.get('edge', '')}", text, f"{key}: {mark['label']}")
                    else:
                        self.assertIn(mark["when"], text, f"{key}: {mark['label']}")
                    seen += 1
        self.assertGreaterEqual(seen, 10)

    def test_the_coming_dates_of_a_timeline_are_duties_on_the_calendar(self):
        # 앞으로 올 날짜(2027년부터)는 일정 화면의 의무에도 있는 날짜다
        duties = {duty["date"] for duty in read_json("data/duties.json", {})["duties"]}
        for key, figure in self.figures.items():
            for band in figure.get("bands", []):
                for mark in band["marks"]:
                    if mark.get("date", "") >= "2027-01-01":
                        self.assertIn(mark["date"], duties, f"{key}: {mark['label']}")

    def test_the_markup_bars_are_the_ones_the_estimate_uses(self):
        figure = self.figures["defaults.markup"]
        self.assertEqual((figure["kind"], figure["unit"], figure["groups"]), ("bars", "%", ["2026년", "2027년", "2028년부터"]))
        by_sector = {tuple(group["sectors"]): group["values"] for group in read_json("data/calc.json", {})["markups"]}
        heavy, light = figure["series"]
        self.assertEqual((heavy["name"], heavy["values"]), ("시멘트, 철강, 알루미늄, 수소", [by_sector[("cement", "steel", "aluminium", "hydrogen")][year] for year in ("2026", "2027", "2028")]))
        self.assertEqual((light["name"], light["values"]), ("비료", [by_sector[("fertilisers",)]["2026"]] * 3))

    def test_the_split_is_the_worked_example(self):
        figure = self.figures["certificates.example"]
        goods = read_json("data/calc-goods.json", {})
        choice = next(one for one in goods["goods"] if one["code"] == "72081000")["defaults"][0]
        terms = read_json("data/calc.json", {})
        markup = next(group for group in terms["markups"] if "steel" in group["sectors"])["values"]["2026"]
        factor = next(path for path in read_json("data/factor.json", {})["paths"] if path["key"] == "current")["values"]["2026"]
        embedded = goods["rows"][choice["row"]]["total"] * (1 + markup / 100)
        allocation = choice["benchmark"][0] * factor / 100 * terms["cscf"]["values"]["2026"] / 100
        self.assertEqual(figure["unit"], "tCO2e")
        self.assertEqual(figure["whole"]["value"], round(embedded, 3))
        self.assertEqual([part["value"] for part in figure["parts"]], [round(allocation, 3), round(embedded - allocation, 3)])
        self.assertIn(f"마크업 {markup}%", figure["whole"]["label"])

    def test_the_factor_figure_draws_a_stored_path(self):
        paths = {path["key"] for path in read_json("data/factor.json", {})["paths"]}
        drawn = [figure["path"] for figure in self.figures.values() if figure["kind"] == "factor"]
        self.assertEqual(drawn, ["current"])
        self.assertLessEqual(set(drawn), paths)

    def test_the_sector_tiles_are_the_six_sectors_of_the_site(self):
        sectors = read_json("sources/sectors.json", {})["sectors"]
        tiles = self.figures["overview.sectors"]["items"]
        self.assertEqual(len(tiles), 6)
        self.assertEqual({tile["href"] for tile in tiles}, {f"#sector-{sector['key']}" for sector in sectors})
        self.assertEqual({tile["icon"] for tile in tiles}, {sector["key"] for sector in sectors})

    def test_the_matrix_agrees_with_the_item_list_on_indirect_emissions(self):
        # 품목 목록(data/cn.json)이 '직접배출량만'이라고 적은 품목과 그림이 같아야 한다. 철강 부문에서는 철광석 응결체(2601 12 00)만 간접배출량도 넣는다
        figure = self.figures["scope.direct-only"]
        rows = {row["title"]: row for row in figure["rows"]}
        self.assertEqual(figure["cols"], ["직접배출량", "간접배출량"])
        names = {"cement": "시멘트", "fertilisers": "비료", "steel": "철강", "aluminium": "알루미늄", "chemicals": "수소", "electricity": "전력"}
        both, direct = {}, {}
        for good in read_json("data/cn.json", {})["current"]:
            (direct if good["directOnly"] else both).setdefault(good["sector"], []).append(good)
        self.assertEqual(set(both) | set(direct), set(names))
        for sector, name in names.items():
            self.assertEqual(rows[name]["cells"], [True, sector not in direct], name)
        mixed = [good for sector in set(both) & set(direct) for good in both[sector]]
        self.assertEqual([good["codes"] for good in mixed], [["26011200"]])
        self.assertEqual((rows["철광석 응결체"]["text"], rows["철광석 응결체"]["cells"]), ("2601 12 00", [True, True]))
        self.assertEqual(len(rows), len(names) + len(mixed))


class HealthTest(unittest.TestCase):
    def test_drift_in_the_handbook_reaches_the_daily_report(self):
        body = read_json(handbook.SOURCE, None)
        self.assertEqual(reference_health.handbook_lines(body), [])
        changed = copy.deepcopy(body)
        changed["chapters"][10]["sections"][0]["basis"][-1]["contains"] = ["The excess emissions penalty shall be EUR 999 for each tonne"]
        lines = reference_health.handbook_lines(changed)
        self.assertEqual(len(lines), 1)
        self.assertTrue(lines[0].startswith("해설서: penalties.late-surrender: 근거 어긋남: ets-directive에 없는 대목"))


if __name__ == "__main__":
    unittest.main()
