"""문서의 두 판을 견주는 일(tools.laws.compare)과, 달라진 곳의 자료와 앞선 판의 문단을 옮기게 하는 숨은 문서(tools.laws.revisions)."""
import json
import pathlib
import tempfile
import unittest
import unittest.mock

from tools.laws import compare, corpus, revisions, store


def article(number, title, *blocks):
    return {"id": f"art-{number}", "kind": "article", "label": f"Article {number}", "title": title, "blocks": list(blocks)}


OLD = [
    {"id": "front", "kind": "front", "label": "", "title": "", "blocks": ["REGULATION (EU) 2023/956", "Having regard to the Treaty"]},
    {"id": "recitals", "kind": "recitals", "label": "Whereas", "title": "", "blocks": ["(1) A recital that the consolidated text does not carry."]},
    article(1, "Subject matter", "1. This Regulation establishes a mechanism.", "2. The mechanism complements the system."),
    article(6, "CBAM declaration", "1. By 31 May of each year, each declarant shall submit a declaration.", "2. The declaration shall contain the following information:"),
    article(7, "Calculation", "2. Embedded emissions in goods other than electricity shall be determined based on the actual emissions in accordance with the methods set out in Annex IV."),
    article(9, "Old article", "The whole of this article was deleted later."),
]
NEW = [
    {"id": "front", "kind": "front", "label": "", "title": "", "blocks": ["Consolidated TEXT", "This text is meant purely as a documentation tool"]},
    article(1, "Subject matter", "1. This Regulation establishes a mechanism.", "2. The mechanism complements the system."),
    article("2a", "De minimis exemption", "1. An importer shall be exempted below the threshold."),
    article(6, "CBAM declaration", "1. By 30 September of each year, each declarant shall submit a declaration.", "2. The declaration shall contain the following information:"),
    article(7, "Calculation", "2. Embedded emissions in goods other than electricity shall be determined:", "(a) based on the actual emissions; or", "(b) by reference to default values."),
]


class CompareTest(unittest.TestCase):
    def ops(self, old, new):
        found, same = compare.rows(old, new)
        return [(row["op"], (row["old"] or {}).get("text", "")[:24], (row["new"] or {}).get("text", "")[:24]) for row in found], same

    def test_only_the_paragraphs_that_differ_are_listed_in_order(self):
        found, same = self.ops(OLD, NEW)
        self.assertEqual(found, [
            ("added", "", "De minimis exemption"),
            ("added", "", "1. An importer shall be "),
            ("changed", "1. By 31 May of each yea", "1. By 30 September of ea"),
            ("changed", "2. Embedded emissions in", "2. Embedded emissions in"),   # 머리말과 목록으로 갈라진 문단은 같은 번호의 머리말과 짝짓는다
            ("removed", "Old article", ""),                                         # 짝이 없는 문단은 빠진 것을 먼저, 더해진 것을 나중에 적는다
            ("removed", "The whole of this articl", ""),
            ("added", "", "(a) based on the actual "),
            ("added", "", "(b) by reference to defa"),
        ])
        self.assertEqual(same, 6)   # 제1조의 이름과 두 문단, 제6조의 이름과 둘째 문단, 제7조의 이름. 머리와 전문은 세지 않는다
        self.assertEqual(compare.stats(compare.rows(OLD, NEW)[0]), {"changed": 2, "added": 4, "removed": 2})

    def test_the_front_matter_recitals_and_notes_are_not_compared(self):
        found, _ = compare.rows(OLD, NEW)
        self.assertFalse([row for row in found if "recital" in ((row["old"] or row["new"])["text"])])
        self.assertEqual({(row["old"] or row["new"])["part"] for row in found}, {"art-2a", "art-6", "art-7", "art-9"})

    def test_footnote_numbering_alone_is_not_a_change(self):
        old = [article(3, "Definitions", "(31) ‘operator’ means an operator as defined in Directive (EU) 2019/944 of the Council (1).", "See Article 5(1), (2) and (3).")]
        new = [article(3, "Definitions", "(31) “operator” means an operator as defined in Directive (EU) 2019/944 of the Council ( 7 ).", "See Article 5(1), (2) and (4).")]
        found, same = self.ops(old, new)
        self.assertEqual(found, [("changed", "See Article 5(1), (2) an", "See Article 5(1), (2) an")])   # 조문을 가리키는 번호가 바뀐 것은 달라진 것이다
        self.assertEqual(same, 2)
        # PDF 문서의 각주 표시([3])와 통합본끼리의 각주 표시도 번호만 다르면 같은 문단이다
        self.assertEqual(self.ops([article(1, "", "Text with a note[3].", "[3] The note.")], [article(1, "", "Text with a note[4].", "[4] The note.")])[0], [])
        self.assertEqual(self.ops([article(1, "", "Text ( 2 ).")], [article(1, "", "Text ( 9 ).")])[0], [])

    def test_a_line_broken_differently_is_not_a_change(self):
        old = [{"id": "annex-i", "kind": "annex", "label": "ANNEX I", "title": "", "blocks": ["CN code", "72 –", "Iron and steel", "7208", "Flat-rolled products", "(1) Directive (EU) 2019/944 (OJ L 158, 14.6.2019, p. 125)."]}]
        new = [{"id": "annex-i", "kind": "annex", "label": "ANNEX I", "title": "", "blocks": ["CN code", "72 – Iron and steel", "7208", "Flat-rolled products of iron", "7210 –"]}]
        found, same = self.ops(old, new)
        # 두 줄이 한 줄로 이어진 것, 수와 기호뿐인 줄이 더해진 것, 관보를 인용하는 각주가 빠진 것은 싣지 않는다
        self.assertEqual(found, [("changed", "Flat-rolled products", "Flat-rolled products of ")])
        self.assertEqual(same, 3)

    def test_a_rewritten_passage_is_not_paired_at_random(self):
        old = [article(1, "", *[f"Old sentence number {index} about apples and pears." for index in range(70)])]
        new = [article(1, "", *[f"Entirely new wording {index} on steel mills." for index in range(70)])]
        found, _ = compare.rows(old, new)
        self.assertEqual(compare.stats(found), {"changed": 0, "added": 70, "removed": 70})


class RevisionsTest(unittest.TestCase):
    ACT = {"id": "32023R0956", "celex": "32023R0956", "name": "CBAM 규정", "group": "act", "format": "act", "consolidated": "2025-10-20", "path": "now.txt", "url": "", "rule": ""}
    BEFORE = {"tag": "20230516", "date": "2023-05-16", "label": "2023-05-16 관보에 실린 처음 글", "path": "old.txt", "url": "https://example.eu/old"}

    def setUp(self):
        patches = [unittest.mock.patch.object(revisions, "chain", return_value=[self.BEFORE]),
                   unittest.mock.patch.object(corpus, "read", side_effect=lambda act: OLD if act["path"] == "old.txt" else NEW)]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)

    def test_paragraphs_only_in_the_earlier_version_become_a_hidden_document(self):
        (act, parts), = revisions.history([(self.ACT, NEW)])
        self.assertEqual((act["id"], act["hidden"], act["group"], act["of"]), ("32023R0956-was-20230516", True, "act", "32023R0956"))
        self.assertGreaterEqual(act["turn"], 900)   # 같은 갈래의 문서를 모두 옮긴 뒤에 옮긴다
        self.assertEqual([(part["id"], part["title"], len(part["blocks"])) for part in parts], [("art-6", "", 1), ("art-7", "", 1), ("art-9", "Old article", 1)])
        self.assertTrue(parts[0]["blocks"][0].startswith("1. By 31 May"))
        self.assertEqual(revisions.history([(act, parts)]), [])   # 숨은 문서의 숨은 문서는 만들지 않는다

    def test_the_public_data_groups_the_rows_by_part_and_keeps_deleted_parts_in_place(self):
        memory = {store.key("1. By 31 May of each year, each declarant shall submit a declaration."): "1. 매년 5월 31일까지 신고인은 신고서를 제출하여야 한다.",
                  store.key("1. By 30 September of each year, each declarant shall submit a declaration."): "1. 매년 9월 30일까지 신고인은 신고서를 제출하여야 한다.",
                  store.key("CBAM declaration"): "CBAM 신고서"}
        body = revisions.public(self.ACT, NEW, memory)
        newest = body["revisions"][0]
        self.assertEqual((newest["from"]["label"], newest["to"]["label"], newest["to"]["date"]), ("2023-05-16 관보에 실린 처음 글", "2025-10-20 통합본", "2025-10-20"))
        self.assertEqual(newest["stats"], {"changed": 2, "added": 4, "removed": 2, "same": 6, "parts": 4})
        self.assertEqual([(part["id"], part["gone"]) for part in newest["parts"]], [("art-2a", False), ("art-6", False), ("art-7", False), ("art-9", True)])
        declaration = newest["parts"][1]
        self.assertEqual((declaration["ko"], declaration["titleKo"]), ("제6조", "CBAM 신고서"))
        row = declaration["rows"][0]
        self.assertEqual((row["op"], row["at"]), ("changed", 1))   # 지금의 글에서 그 조의 첫 문단
        self.assertEqual(row["old"][1], "1. 매년 5월 31일까지 신고인은 신고서를 제출하여야 한다.")
        self.assertEqual(row["new"][1], "1. 매년 9월 30일까지 신고인은 신고서를 제출하여야 한다.")
        self.assertEqual(newest["parts"][0]["rows"][0], {"op": "added", "new": ["De minimis exemption", ""], "at": 0})   # 이름은 0번째
        self.assertEqual(revisions.brief(body), {"rows": 8, "from": "2023-05-16 관보에 실린 처음 글", "to": "2025-10-20 통합본", "date": "2025-10-20"})

    def test_a_document_without_changes_gets_no_file(self):
        with unittest.mock.patch.object(corpus, "read", return_value=NEW), tempfile.TemporaryDirectory() as folder:
            self.assertEqual(revisions.write(folder, [(self.ACT, NEW)], {}), {})
            self.assertFalse((pathlib.Path(folder) / "changes").exists())
        with tempfile.TemporaryDirectory() as folder:
            found = revisions.write(folder, [(self.ACT, NEW), ({**self.ACT, "id": "empty"}, [])], {})
            self.assertEqual(list(found), ["32023R0956"])
            written = json.loads((pathlib.Path(folder) / "changes" / "32023R0956.json").read_text(encoding="utf-8"))
            self.assertEqual(written["name"], "CBAM 규정")


class ChainTest(unittest.TestCase):
    """앞선 판을 어디에서 찾는가: 법령은 남겨 둔 글에서, 집행위원회 문서는 원문 대장의 지난 판에서."""

    def test_an_act_takes_the_kept_versions_older_than_the_text_in_use(self):
        with tempfile.TemporaryDirectory() as folder:
            texts = {code: pathlib.Path(folder) / f"{code}.txt" for code in ("32023R0956", "02023R0956-20251020", "02023R0956-20270301")}
            for path in texts.values():
                path.write_text("Article 1\n", encoding="utf-8")
            kept = [{"act": "32023R0956", "code": "32023R0956", "kind": "adopted", "date": "2023-05-16", "textPath": str(texts["32023R0956"])},
                    {"act": "32023R0956", "code": "02023R0956-20251020", "kind": "consolidated", "date": "2025-10-20", "textPath": str(texts["02023R0956-20251020"])},
                    {"act": "32023R0956", "code": "02023R0956-20270301", "kind": "consolidated", "date": "2027-03-01", "textPath": str(texts["02023R0956-20270301"])},
                    {"act": "32025R2547", "code": "32025R2547", "kind": "adopted", "date": "2025-12-10", "textPath": str(texts["32023R0956"])},
                    {"act": "32023R0956", "code": "gone", "kind": "consolidated", "date": "2024-01-01", "textPath": str(pathlib.Path(folder) / "없는 파일.txt")}]
            act = {"id": "32023R0956", "celex": "32023R0956", "group": "act", "consolidated": "2027-03-01"}
            with unittest.mock.patch.object(revisions.earlier, "entries", return_value=kept):
                found = revisions.chain(act)
            self.assertEqual([(row["tag"], row["label"]) for row in found], [("20230516", "2023-05-16 관보에 실린 처음 글"), ("20251020", "2025-10-20 통합본")])
            self.assertEqual(revisions.current(act)["label"], "2027-03-01 통합본")

    def test_a_document_takes_its_earlier_versions_and_those_of_the_file_it_replaced(self):
        with tempfile.TemporaryDirectory() as folder:
            def text(name):
                path = pathlib.Path(folder) / name
                path.write_text("1 Introduction\n", encoding="utf-8")
                return str(path)
            state = {"docs": {
                "old": {"id": "old", "url": "https://example.eu/old", "versions": [{"date": "2026-03-01", "text": text("a.txt")}, {"date": "2026-06-01", "text": text("b.txt")}]},
                "new": {"id": "new", "url": "https://example.eu/new", "replaces": "old",
                        "versions": [{"date": "2026-11-10", "text": text("c.txt")}, {"date": "2026-11-10", "text": ""}, {"date": "2027-01-05", "text": text("d.txt")}]},
            }}
            act = {"id": "guide-3", "group": "guide", "path": state["docs"]["new"]["versions"][-1]["text"], "received": "2027-01-05"}
            with unittest.mock.patch.object(revisions, "read_json", return_value=state):
                found = revisions.chain(act)
            self.assertEqual([(row["tag"], row["label"], row["url"]) for row in found], [
                ("20260301", "2026-03-01에 받은 판", "https://example.eu/old"), ("20260601", "2026-06-01에 받은 판", "https://example.eu/old"),
                ("20261110", "2026-11-10에 받은 판", "https://example.eu/new")])   # 글을 받아 두지 못한 판은 건너뛴다
            self.assertEqual(revisions.current(act)["label"], "2027-01-05에 받은 판")
            with unittest.mock.patch.object(revisions, "read_json", return_value={"docs": {}}):
                self.assertEqual(revisions.chain(act), [])


if __name__ == "__main__":
    unittest.main()
