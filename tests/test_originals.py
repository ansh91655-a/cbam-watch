"""원문 판 관리의 흐름을 가짜 화면과 가짜 내려받기로 확인한다."""
import json
import os
import pathlib
import tempfile
import unittest
from unittest import mock

from tools.originals import discover, run

PAGE_A = "https://taxation-customs.ec.europa.eu/a_en"
PAGE_B = "https://taxation-customs.ec.europa.eu/b_en"
ID1 = "11111111-1111-4111-8111-111111111111"
ID2 = "22222222-2222-4222-8222-222222222222"
ID3 = "33333333-3333-4333-8333-333333333333"
ID4 = "44444444-4444-4444-8444-444444444444"
PAD = "<p>" + "x" * 900 + "</p>"


def _page(*links):
    return ("<html><body>" + PAD + "".join(f'<a href="{href}">Download</a>' for href in links) + "</body></html>").encode()


class Web:
    """주소별 응답을 들고 있다가 fetch 대신 답한다."""

    def __init__(self):
        self.pages = {}
        self.blocked = set()

    def fetch(self, url, **_):
        if url in self.blocked:
            return 403, {}, b"blocked", "HTTP Error 403: Forbidden"
        if url not in self.pages:
            return 404, {}, b"", "HTTP Error 404"
        headers, body = self.pages[url]
        return 200, headers, body, ""


class OriginalsFlowTest(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.previous = os.getcwd()
        os.chdir(self.folder.name)
        self.web = Web()
        self._registry([("page-a", PAGE_A)])
        patches = [mock.patch.object(run, "fetch", self.web.fetch), mock.patch.object(discover, "fetch", self.web.fetch), mock.patch.object(run.time, "sleep", lambda _: None)]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)

    def tearDown(self):
        os.chdir(self.previous)
        self.folder.cleanup()

    def _registry(self, pages):
        sources = [{"no": i + 1, "code": code, "name": code, "group": "EU 공식", "url": url, "tier": "A", "watch": ["links"], "collector": "github", "documents": True}
                   for i, (code, url) in enumerate(pages)]
        pathlib.Path("sources").mkdir(exist_ok=True)
        pathlib.Path("sources/registry.json").write_text(json.dumps({"sources": sources, "keywords": []}), encoding="utf-8")

    def _doc(self, doc_id, lang, name, text, page=PAGE_A):
        tail = f"_{lang}" if lang else ""
        query = f"?filename={name}" if name else ""
        url = f"https://taxation-customs.ec.europa.eu/document/download/{doc_id}{tail}{query}"
        self.web.pages[url] = ({"Content-Type": "text/plain", "Content-Disposition": 'attachment; filename="from-header.txt"'}, text.encode())
        return url

    def _state(self):
        return json.loads(pathlib.Path("originals/state.json").read_text(encoding="utf-8"))

    def _feed(self):
        files = sorted(pathlib.Path("collected/feed").glob("*.json")) if pathlib.Path("collected/feed").exists() else []
        return [item for path in files for item in json.loads(path.read_text(encoding="utf-8"))["items"]]

    def test_baseline_then_changes(self):
        one = self._doc(ID1, "en", "Guide.txt", "첫 문단\n\n둘째 문단")
        swedish = self._doc(ID2, "sv", "Act-SV.txt", "svenska")
        english = self._doc(ID2, "en", "Act-EN.txt", "english text")
        self.web.pages[PAGE_A] = ({"Content-Type": "text/html"}, _page(one, swedish, english))
        run.main([])
        state = self._state()
        self.assertEqual(set(state["docs"]), {ID1, ID2})
        self.assertEqual(state["docs"][ID2]["filename"], "Act-EN.txt")  # 영어판을 고른다
        self.assertEqual(self._feed(), [])  # 첫 실행은 기준선

        # 본문이 바뀐 새 판
        self._doc(ID1, "en", "Guide.txt", "첫 문단\n\n둘째 문단을 고침\n\n셋째 문단")
        run.main(["--full"])
        items = self._feed()
        self.assertEqual([item["change"] for item in items], ["new-version"])
        self.assertEqual(items[0]["stats"]["added"], 1)
        self.assertTrue(pathlib.Path(items[0]["diff"]).exists())
        self.assertEqual(len(self._state()["docs"][ID1]["versions"]), 2)

        # 같은 파일을 다시 받으면 아무 일도 없다
        run.main(["--full"])
        self.assertEqual(len(self._feed()), 1)

        # 새 문서: 이름이 주소에 없으면 응답 머리글의 이름을 쓴다
        three = self._doc(ID3, "en", "", "새 문서의 본문")
        self.web.pages[PAGE_A] = ({"Content-Type": "text/html"}, _page(one, english, three))
        run.main([])
        items = self._feed()
        self.assertEqual(items[-1]["change"], "new-document")
        self.assertEqual(self._state()["docs"][ID3]["filename"], "from-header.txt")

        # 화면을 읽지 못한 날에는 문서가 사라졌다고 하지 않는다
        del self.web.pages[PAGE_A]
        run.main([])
        self.assertTrue(all(doc["linked"] for doc in self._state()["docs"].values()))

        # 화면에서 링크가 빠지면 알린다
        self.web.pages[PAGE_A] = ({"Content-Type": "text/html"}, _page(one, english))
        run.main([])
        self.assertEqual(self._feed()[-1]["change"], "unlinked")
        self.assertFalse(self._state()["docs"][ID3]["linked"])

    def test_new_page_is_baselined_quietly(self):
        one = self._doc(ID1, "en", "Guide.txt", "본문")
        self.web.pages[PAGE_A] = ({"Content-Type": "text/html"}, _page(one))
        run.main([])
        # 화면 하나를 더한다: 그 화면에 원래 있던 문서는 소식이 아니다
        four = self._doc(ID4, "en", "Archive.zip", "PK-binary")
        self._registry([("page-a", PAGE_A), ("page-b", PAGE_B)])
        self.web.pages[PAGE_B] = ({"Content-Type": "text/html"}, _page(four))
        run.main([])
        state = self._state()
        self.assertIn(ID4, state["docs"])
        self.assertEqual(self._feed(), [])
        self.assertEqual(set(state["pages"]), {"page-a", "page-b"})
        version = state["docs"][ID4]["versions"][0]
        self.assertEqual((version["file"], version.get("kept")), ("", False))  # 압축 파일은 해시만 적는다

    def test_blocked_downloads_wait_quietly(self):
        # 첫 실행에서 일부 문서를 받지 못한다: 받지 못한 것은 대기 목록에 남고, 나머지는 그대로 받으며, 나중에 받아도 소식이 아니다
        urls = [self._doc(doc_id, "en", f"Doc{index}.txt", f"본문 {index}") for index, doc_id in enumerate((ID1, ID2, ID3, ID4))]
        self.web.pages[PAGE_A] = ({"Content-Type": "text/html"}, _page(*urls))
        self.web.blocked = {urls[0], urls[1], urls[2]}
        run.main([])
        state = self._state()
        self.assertEqual(set(state["docs"]), {ID4})  # 앞의 셋이 막혀도 넷째는 받는다
        self.assertEqual([state["pending"][doc_id]["tries"] for doc_id in (ID1, ID2, ID3)], [1, 1, 1])
        run.main([])
        run.main([])
        state = self._state()
        self.assertEqual(state["unreachableCount"], 3)  # 세 번 실패하면 평소에는 다시 시도하지 않는다
        self.web.blocked = set()
        run.main(["--full"])
        state = self._state()
        self.assertEqual(set(state["docs"]), {ID1, ID2, ID3, ID4})
        self.assertEqual(state["pending"], {})
        self.assertEqual(self._feed(), [])

    def test_known_documents_failing_in_a_row_stop_the_run(self):
        urls = [self._doc(doc_id, "en", f"Doc{index}.txt", f"본문 {index}") for index, doc_id in enumerate((ID1, ID2, ID3))]
        self.web.pages[PAGE_A] = ({"Content-Type": "text/html"}, _page(*urls))
        run.main([])
        self.web.blocked = set(urls)
        run.main([])
        state = self._state()
        self.assertTrue(any("그만 받음" in note for note in state["notes"]))
        self.assertEqual(sum(1 for doc in state["docs"].values() if doc.get("lastError")), 2)
        self.assertEqual(self._feed(), [])  # 받지 못했다고 문서가 사라졌다거나 바뀌었다고 하지 않는다

    def test_new_link_on_known_page_is_news_even_if_late(self):
        one = self._doc(ID1, "en", "Guide.txt", "본문")
        self.web.pages[PAGE_A] = ({"Content-Type": "text/html"}, _page(one))
        run.main([])
        late = self._doc(ID2, "en", "Late.txt", "늦게 받은 새 문서")
        self.web.pages[PAGE_A] = ({"Content-Type": "text/html"}, _page(one, late))
        self.web.blocked = {late}
        run.main([])
        self.assertEqual(self._feed(), [])
        self.assertFalse(self._state()["pending"][ID2]["quiet"])
        self.web.blocked = set()
        run.main([])
        self.assertEqual([item["change"] for item in self._feed()], ["new-document"])

    def test_translations_can_be_skipped(self):
        english = self._doc(ID1, "en", "Factsheet_EN_Cement.txt", "english")
        serbian = self._doc(ID2, "en", "Factsheet_Cement_SR.pdf", "srpski")
        self.web.pages[PAGE_A] = ({"Content-Type": "text/html"}, _page(english, serbian))
        registry = json.loads(pathlib.Path("sources/registry.json").read_text(encoding="utf-8"))
        registry["sources"][0]["skipDocuments"] = ["_(MK|SR)\\.pdf$"]
        pathlib.Path("sources/registry.json").write_text(json.dumps(registry), encoding="utf-8")
        run.main([])
        self.assertEqual(set(self._state()["docs"]), {ID1})

    def test_same_text_is_not_a_new_version(self):
        one = self._doc(ID1, "en", "Guide.html", "<html><body><p>같은 본문</p></body></html>")
        self.web.pages[PAGE_A] = ({"Content-Type": "text/html"}, _page(one))
        run.main([])
        self._doc(ID1, "en", "Guide.html", "<html><body><!-- 만든 시각이 다름 --><p>같은 본문</p></body></html>")
        run.main(["--full"])
        state = self._state()
        self.assertEqual(self._feed(), [])
        self.assertEqual(len(state["docs"][ID1]["versions"]), 1)
        self.assertEqual(len(state["docs"][ID1]["versions"][0]["sameTextHashes"]), 1)
        self.assertEqual(len(list(pathlib.Path(f"originals/files/{ID1}").iterdir())), 1)


if __name__ == "__main__":
    unittest.main()
