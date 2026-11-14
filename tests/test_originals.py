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
        self.assertEqual(len(state["unreachableNames"]), 3)   # 무엇을 받지 못하는지 이름으로 남긴다(주간 보고가 적는다)
        self.assertTrue(all(name and "이름을 모르는" not in name for name in state["unreachableNames"]), state["unreachableNames"])
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

    def test_a_blocked_document_can_be_supplied_by_hand(self):
        # 자동으로 받지 못하는 문서를 사람이 받아 넣는다: 대장에 오르고, 받지 못한 문서에서 빠지고, 다음부터는 다시 받으려 하지 않는다
        from tools.originals import supply
        urls = [self._doc(doc_id, "en", "", f"본문 {index}") for index, doc_id in enumerate((ID1, ID2, ID3))]
        self.web.pages[PAGE_A] = ({"Content-Type": "text/html"}, _page(*urls))
        self.web.blocked = {urls[0], urls[1]}
        for _ in range(3):
            run.main([])
        state = self._state()
        self.assertEqual((set(state["docs"]), state["unreachableCount"]), ({ID3}, 2))
        self.assertEqual([row[0] for row in supply.listing()], [ID1, ID2])

        self.assertEqual(supply.add(ID1, "손으로 받은 본문".encode(), "leaflet-KP1.txt")[0], "added")
        state = self._state()
        doc = state["docs"][ID1]
        self.assertEqual((doc["filename"], doc["page"], doc["url"], bool(doc["supplied"])),
                         ("leaflet-KP1.txt", "page-a", f"https://taxation-customs.ec.europa.eu/document/download/{ID1}_en", True))
        self.assertTrue(pathlib.Path(doc["versions"][-1]["file"]).is_file() and pathlib.Path(doc["versions"][-1]["text"]).is_file())
        self.assertEqual((set(state["pending"]), state["unreachableCount"], state["docCount"], state["pendingCount"]), ({ID2}, 1, 2, 1))
        self.assertEqual(self._feed(), [])   # 처음 본 날부터 있던 문서는 소식이 아니다

        # 모르는 번호는 넣지 않는다. 같은 파일을 다시 넣어도 판이 늘지 않는다
        self.assertEqual(supply.add(ID4, b"x", "x.txt")[0], "unknown")
        self.assertEqual(supply.add(ID1, "손으로 받은 본문".encode(), "leaflet-KP1.txt")[0], "same")
        self.assertEqual(len(self._state()["docs"][ID1]["versions"]), 1)

        # 다음 실행: 넣은 문서는 다시 받으려 하지 않는다(여전히 받아 주지 않는 주소다). 다른 문서는 전과 같이 확인한다
        asked = []
        real = self.web.fetch
        with mock.patch.object(run, "fetch", lambda url, **more: asked.append(url) or real(url, **more)):
            run.main(["--full"])
        self.assertNotIn(urls[0], asked)
        self.assertIn(urls[2], asked)
        state = self._state()
        self.assertNotIn("lastError", state["docs"][ID1])
        self.assertFalse(any("그만 받음" in note for note in state["notes"]))

        # 본문이 달라진 파일을 다시 넣으면 새 판이 된다
        self.assertEqual(supply.add(ID1, "손으로 받은 본문\n\n더해진 문단".encode(), "leaflet-KP1.txt")[0], "version")
        self.assertEqual(len(self._state()["docs"][ID1]["versions"]), 2)

        # 화면에서 링크가 빠지면 넣은 문서도 사라졌다고 알린다
        self.web.pages[PAGE_A] = ({"Content-Type": "text/html"}, _page(urls[1], urls[2]))
        run.main([])
        self.assertEqual([item["change"] for item in self._feed()], ["unlinked"])
        self.assertFalse(self._state()["docs"][ID1]["linked"])

    def test_a_supplied_document_can_be_kept_as_text_only(self):
        # 문서 안에 EU의 것이 아닌 그림이 있다고 적혀 있으면 사본을 싣지 않고 본문만 받아 둔다. 원문 대장은 원래 올라온 곳으로 잇는다
        from tools.originals import supply
        from tools.publish import derive
        urls = [self._doc(ID1, "en", "", "본문"), self._doc(ID2, "en", "", "본문 둘")]
        self.web.pages[PAGE_A] = ({"Content-Type": "text/html"}, _page(*urls))
        self.web.blocked = set(urls)
        run.main([])
        why = "문서에 EU의 것이 아닌 그림이 있다고 적혀 있음"
        outcome, said = supply.add(ID1, "그림이 든 문서의 본문".encode(), "leaflet.txt", no_copy=why)
        version = self._state()["docs"][ID1]["versions"][-1]
        self.assertEqual((outcome, version["file"], version["kept"], version["withheld"]), ("added", "", False, why))
        self.assertIn("사본 없음", said)
        self.assertEqual(pathlib.Path(version["text"]).read_text(encoding="utf-8"), "그림이 든 문서의 본문")
        self.assertEqual([path for path in pathlib.Path("originals/files").rglob("*") if path.is_file()] if pathlib.Path("originals/files").exists() else [], [])
        body, _ = derive.documents()
        row = next(row for row in body["documents"] if row["id"] == ID1)
        self.assertEqual((row["stored"], row["download"]), (False, f"https://taxation-customs.ec.europa.eu/document/download/{ID1}_en"))
        self.assertEqual(derive.stored_files(), [])
        # 본문을 뽑지 못하는 파일은 사본 없이 넣을 수 없다(남는 것이 없다)
        self.assertEqual(supply.add(ID2, b"PK\x03\x04", "bundle.zip", no_copy=why)[0], "unreadable")
        self.assertIn(ID2, self._state()["pending"])

    def test_a_pdf_kept_as_text_only_has_its_units_read_before_the_copy_goes(self):
        # 사본을 두지 않는 PDF는 지우기 전에 뜻 단위를 읽어 둔다(사본이 없으면 나중에 읽을 수 없다)
        import shutil
        try:
            import pikepdf
        except ImportError:
            self.skipTest("pikepdf가 있어야 한다")
        if not shutil.which("pdftotext"):
            self.skipTest("pdftotext가 있어야 한다")
        from tools.originals import supply
        url = self._doc(ID1, "en", "", "본문")
        self.web.pages[PAGE_A] = ({"Content-Type": "text/html"}, _page(url))
        self.web.blocked = {url}
        run.main([])
        pdf = pikepdf.new()
        pdf.add_blank_page(page_size=(200, 200))
        pdf.save("leaflet.pdf")
        self.assertEqual(supply.add(ID1, pathlib.Path("leaflet.pdf").read_bytes(), "leaflet-KP3.pdf", no_copy="남의 그림이 든 문서")[0], "added")
        version = self._state()["docs"][ID1]["versions"][-1]
        self.assertEqual((version["file"], version["pages"]), ("", 1))
        units = pathlib.Path("originals/units") / ID1 / (pathlib.Path(version["text"]).stem + ".json")
        self.assertEqual(json.loads(units.read_text(encoding="utf-8")), {"pages": 1, "tagged": False, "layout": True, "units": []})
        self.assertFalse(pathlib.Path("originals/files").exists() and any(path.is_file() for path in pathlib.Path("originals/files").rglob("*")))

    def test_the_supply_command_lists_and_adds(self):
        import contextlib
        import io
        from tools.originals import supply
        url = self._doc(ID1, "en", "", "본문")
        self.web.pages[PAGE_A] = ({"Content-Type": "text/html"}, _page(url))
        self.web.blocked = {url}
        run.main([])
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(supply.main(["--list"]), 0)
            pathlib.Path("got.txt").write_text("받은 본문", encoding="utf-8")
            self.assertEqual(supply.main([ID1.upper(), "got.txt", "--name", "leaflet-KP2.txt"]), 0)
            self.assertEqual(supply.main([ID4, "got.txt"]), 2)       # 모르는 번호
            self.assertEqual(supply.main([ID1, "none.txt"]), 2)      # 없는 파일
        said = out.getvalue()
        self.assertIn(f"{ID1}  page-a", said)
        self.assertIn("받지 못한 문서 1건", said)
        self.assertIn("넣음: ", said)
        self.assertEqual(self._state()["docs"][ID1]["filename"], "leaflet-KP2.txt")


if __name__ == "__main__":
    unittest.main()
