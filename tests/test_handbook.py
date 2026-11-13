"""CBAM 해설서: 글의 검사(tools.publish.handbook)와, 실린 글(data/handbook.json)의 수치가 다른 참고 자료와 맞는지."""
import copy
import json
import pathlib
import re
import tempfile
import unittest

from tools.check import term_check
from tools.common.jsonio import read_json
from tools.publish import handbook
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
        self.assertEqual(shown["basis"][1], {"label": "EU 배출권거래제 지침 2003/87/EC 제16조(3)", "url": "https://eur-lex.example/ets"})
        self.assertTrue(shown["ordered"])
        self.assertEqual(public["terms"], [{"ko": "기본값", "en": "default value", "text": "2차 데이터로 정한 값입니다.", "chapter": "overview", "section": "purpose"}])
        text = json.dumps(public, ensure_ascii=False)
        for hidden in ("contains", "sources", str(self.stored), "Embedded emissions in goods"):
            self.assertNotIn(hidden, text)


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
        self.assertEqual(len(self.book["chapters"]), 12)

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
