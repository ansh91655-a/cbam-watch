"""화면에 적는 출처의 이름(tools/publish/source_names.py, sources/labels.json)과 원문 대장의 국문 이름(tools/publish/derive.py)."""
import json
import pathlib
import re
import tempfile
import unittest

from tools.publish import derive, source_names

HANGUL = re.compile(r"[가-힣]")
# 영문 그대로 적는 이름: 고유한 이름이라 옮기지 않는다
PROPER = {"EUR-Lex", "KPMG", "CarbonChain"}


class NamesTest(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        root = pathlib.Path(self.folder.name)
        self.registry = str(root / "registry.json")
        self.labels = str(root / "labels.json")
        pathlib.Path(self.registry).write_text(json.dumps({"sources": [
            {"code": "ec-news", "name": "EC CBAM Communication and News"}, {"code": "keco", "name": "한국환경공단 CBAM 헬프데스크"},
            {"code": "a", "name": "Shared name"}, {"code": "b", "name": "Shared name"}]}), encoding="utf-8")
        pathlib.Path(self.labels).write_text(json.dumps({"labels": {"ec-news": "EU 집행위원회 CBAM 소식", "a": "가", "b": "나", "op": "EU 관보(EUR-Lex)"}}), encoding="utf-8")

    def tearDown(self):
        self.folder.cleanup()

    def test_items_are_renamed_by_the_code_of_their_source(self):
        table = source_names.labels(self.labels)
        items = [{"id": 1, "sourceCode": "ec-news", "sourceName": "EC CBAM Communication and News"}, {"id": 2, "sourceCode": "keco", "sourceName": "한국환경공단 CBAM 헬프데스크"}, {"id": 3}]
        renamed = source_names.rename_items(items, table)
        self.assertEqual([item.get("sourceName") for item in renamed], ["EU 집행위원회 CBAM 소식", "한국환경공단 CBAM 헬프데스크", None])
        self.assertEqual(items[0]["sourceName"], "EC CBAM Communication and News")   # 받은 목록은 그대로 둔다

    def test_rows_without_a_code_are_renamed_by_their_old_name(self):
        table = source_names.labels(self.labels)
        items = [{"sourceCode": "op", "sourceName": "EUR-Lex (Official Journal of the EU)"}]   # 쓸 때의 이름이 대장과 다른 소식
        names = source_names.by_name(table, items, self.registry)
        self.assertEqual(names, {"EC CBAM Communication and News": "EU 집행위원회 CBAM 소식", "EUR-Lex (Official Journal of the EU)": "EU 관보(EUR-Lex)"})   # 두 출처가 함께 쓰는 이름은 바꾸지 않는다
        rows = source_names.rename_rows([{"sourceName": "EC CBAM Communication and News"}, {"sourceName": "Shared name"}, {"title": "이름이 없는 줄"}], names)
        self.assertEqual(rows, [{"sourceName": "EU 집행위원회 CBAM 소식"}, {"sourceName": "Shared name"}, {"title": "이름이 없는 줄"}])

    def test_the_price_source_is_renamed_by_its_code(self):
        table = source_names.labels(self.labels)
        self.assertEqual(source_names.rename_source({"code": "ec-news", "name": "x", "url": "u"}, table), {"code": "ec-news", "name": "EU 집행위원회 CBAM 소식", "url": "u"})
        self.assertEqual(source_names.rename_source({"code": "none", "name": "x"}, table), {"code": "none", "name": "x"})
        self.assertIsNone(source_names.rename_source(None, table))


class RepositoryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = json.loads(pathlib.Path("sources/registry.json").read_text(encoding="utf-8"))["sources"]
        cls.labels = source_names.labels()
        cls.items = json.loads(pathlib.Path("data/items.json").read_text(encoding="utf-8"))["items"]

    def test_every_label_names_a_source_and_is_written_in_korean_or_is_a_proper_name(self):
        codes = {source["code"] for source in self.registry} | {item.get("sourceCode") for item in self.items}   # 대장에서 뺀 출처의 소식도 남아 있다
        self.assertLessEqual(set(self.labels), codes)
        for code, label in self.labels.items():
            self.assertTrue(label.strip() and len(label) <= 40, code)
        plain = sorted(label for label in self.labels.values() if not HANGUL.search(label))
        self.assertEqual(plain, ["Carbon Pulse", "Carbon Trust"])                      # 국문이 아닌 이름은 매체의 이름뿐이다

    def test_a_source_with_an_english_name_has_a_label(self):
        """대장에 영문 이름의 출처를 더하면 sources/labels.json에 화면용 이름을 적는다."""
        missing = [source["code"] for source in self.registry if not HANGUL.search(source["name"]) and source["code"] not in self.labels and source["name"] not in PROPER]
        self.assertEqual(missing, [])

    def test_the_news_shows_no_working_name(self):
        shown = {item.get("sourceName", "") for item in source_names.rename_items(self.items, self.labels) if not item.get("withdrawn")}
        english = sorted(name for name in shown if name and not HANGUL.search(name) and name not in PROPER | set(self.labels.values()))
        self.assertEqual(english, [])

    def test_the_site_build_renames_before_anything_reads_the_names(self):
        build = pathlib.Path("tools/publish/build_site.py").read_text(encoding="utf-8")
        renamed = build.index("source_names.rename_items(")
        for later in ("regulations.public(rules", "derive.events(", "derive.public_items(", "feed.news("):
            self.assertLess(renamed, build.index(later), later)

    def test_translated_documents_carry_their_korean_name_in_the_register(self):
        korean = derive.translated()
        self.assertGreaterEqual(len(korean), 20)
        for doc_id, found in korean.items():
            self.assertRegex(doc_id, r"^[0-9a-f-]{36}$")
            self.assertTrue(HANGUL.search(found["name"]) and found["id"], doc_id)
        body, _ = derive.documents()
        with_name = [row for row in body["documents"] if row.get("ko")]
        self.assertGreaterEqual(len(with_name), 20)
        for row in with_name:
            self.assertEqual((row["ko"], row["law"]), (korean[row["id"]]["name"], korean[row["id"]]["id"]))
        for page in body["pages"].values():                                            # 문서가 걸린 화면의 이름도 국문으로 적는다
            self.assertTrue(HANGUL.search(page["name"]), page["name"])
        view = pathlib.Path("site/js/views/docs.js").read_text(encoding="utf-8")
        self.assertIn('doc.ko ? h("span", { class: "doc-ko", text: doc.ko })', view)
        self.assertIn('doc.law ? h("a", { href: `#law-${doc.law}`, text: "원문과 국문 번역 보기" })', view)


if __name__ == "__main__":
    unittest.main()
