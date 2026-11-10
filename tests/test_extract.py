"""출처 화면에서 항목을 찾는 규칙을 확인한다. 저장소 맨 위에서 `python3 -m unittest discover -s tests -t .`로 돌린다."""
import unittest

from tools.collect import extract

NEWS = """
<html><body>
<h2>Latest developments</h2>
<div><p>22Oct2026</p><p>New guidance on electricity imports</p><p>The Commission has published a guidance.</p></div>
<div><p>30Sep2026</p><p>How do CBAM certificates work?</p><p>Download the latest factsheet</p></div>
<h2>Frequently asked questions</h2>
<div><p>CBAM - Questions and Answers</p><p>15 October 2026</p><p>English</p><p>Download (604.21 KB - PDF)</p>
<a href="/document/download/013fa763-5dce-4726-a204-69fec04d5ce2_en?filename=CBAM_Questions%20and%20Answers.pdf">Download the questions</a></div>
<a href="/carbon-border-adjustment-mechanism/cbam-registry_en">CBAM Registry page</a>
</body></html>
"""

PROCEDURE = """
<html><body>
<table><tr><th>Date</th><th>Event</th></tr><tr><td>15/09/2026</td><td>Decision by Parliament, 1st reading</td></tr></table>
<table><tr><th>Name</th><th>Date</th><th>Interest representatives</th></tr><tr><td>GORI Giorgio</td><td>09/06/2026</td><td>European Association</td></tr></table>
</body></html>
"""


def _source(**extra):
    source = {"code": "t", "url": "https://taxation-customs.ec.europa.eu/page_en", "tier": "A", "watch": [], "filter": False}
    source.update(extra)
    return source


class DatedTest(unittest.TestCase):
    def test_news_entries_only(self):
        found, _ = extract.entries(_source(watch=["dated"]), NEWS, [])
        texts = [entry["text"] for entry in found]
        self.assertEqual(len(found), 2, texts)
        self.assertTrue(texts[0].startswith("22Oct2026 | New guidance on electricity imports | The Commission"))
        self.assertTrue(any("How do CBAM certificates work?" in text for text in texts))
        self.assertFalse(any("English" in text for text in texts))


class LinksTest(unittest.TestCase):
    def test_document_links_left_to_originals(self):
        with_docs, _ = extract.entries(_source(watch=["links"], documents=True), NEWS, [])
        without, _ = extract.entries(_source(watch=["links"]), NEWS, [])
        self.assertEqual([entry["text"] for entry in with_docs], ["CBAM Registry page"])
        self.assertEqual(len(without), 2)


class RowsTest(unittest.TestCase):
    def test_skip_tables_by_header(self):
        source = _source(watch=["rows"], skipTables=["Interest representatives"])
        found, counts = extract.entries(source, PROCEDURE, [])
        texts = [entry["text"] for entry in found]
        self.assertIn("15/09/2026 | Decision by Parliament, 1st reading", texts)
        self.assertFalse(any("GORI" in text for text in texts))
        self.assertEqual(counts["rows"], 4)

    def test_all_tables_without_setting(self):
        found, _ = extract.entries(_source(watch=["rows"]), PROCEDURE, [])
        self.assertTrue(any("GORI" in entry["text"] for entry in found))


if __name__ == "__main__":
    unittest.main()


class JsonWatchTest(unittest.TestCase):
    SOURCE = {
        "code": "hys", "url": "https://ec.europa.eu/list", "tier": "A", "watch": ["json"],
        "json": {"url": "https://ec.europa.eu/api", "list": "page.content", "id": "id", "state": ["statuses.0.stage", "statuses.0.feedback"],
                 "fields": {"제목": "title", "단계": "statuses.0.stage", "마감": "statuses.0.end"}, "labels": {"DRAFT": "법령 초안 단계"}},
    }

    def _body(self, stage, feedback="OPEN"):
        import json
        return json.dumps({"page": {"content": [{"id": 16932.0, "title": "CBAM declarations", "statuses": [{"stage": stage, "feedback": feedback, "end": "2026/08/06 23:59:59"}]}]}}).encode()

    def test_state_change_makes_a_new_entry(self):
        from tools.collect import jsonwatch
        first, counts = jsonwatch.entries(self.SOURCE, self._body("PLANNED"), [])
        same, _ = jsonwatch.entries(self.SOURCE, self._body("PLANNED"), [])
        moved, _ = jsonwatch.entries(self.SOURCE, self._body("DRAFT"), [])
        self.assertEqual(counts["rows"], 1)
        self.assertEqual(first[0]["key"], same[0]["key"])
        self.assertNotEqual(first[0]["key"], moved[0]["key"])
        self.assertEqual(moved[0]["text"], "CBAM declarations | DRAFT | 2026/08/06 23:59:59")
        self.assertIn("번호: 16932", moved[0]["detail"])
        self.assertIn("단계: DRAFT (법령 초안 단계)", moved[0]["detail"])
