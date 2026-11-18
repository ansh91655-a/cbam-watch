"""법령의 관보 PDF 받아 두기(tools.archive.actpdf): 파일 잇기와 쪽 덜기, 목록의 줄, 받을 법령, 받아 둔 것은 다시 청하지 않기."""
import io
import json
import pathlib
import tempfile
import unittest
from unittest import mock

from tools.archive import actpdf
from tools.cn import versions

try:
    import pikepdf
except ImportError:  # 꾸러미가 없는 환경에서는 건너뛴다
    pikepdf = None


def _pdf(*widths):
    """쪽마다 너비가 다른 빈 PDF. 너비로 어느 쪽인지 알아본다."""
    pdf = pikepdf.new()
    for width in widths:
        pdf.add_blank_page(page_size=(width, 200))
    out = io.BytesIO()
    pdf.save(out)
    return out.getvalue()


def _widths(data):
    with pikepdf.open(io.BytesIO(data)) as pdf:
        return [int(page.mediabox[2]) for page in pdf.pages]


@unittest.skipUnless(pikepdf, "pikepdf가 있어야 한다")
class JoinTest(unittest.TestCase):
    def test_a_single_file_kept_whole_is_returned_as_it_came(self):
        only = _pdf(101, 102, 103)
        self.assertEqual(actpdf.join([only]), (only, 3, 3))          # 손대지 않으므로 원문의 꼬리표 짜임이 남는다

    def test_parts_are_joined_in_the_order_given(self):
        data, pages, full = actpdf.join([_pdf(101, 102), _pdf(201), _pdf(301, 302)])
        self.assertEqual((_widths(data), pages, full), ([101, 102, 201, 301, 302], 5, 5))

    def test_only_the_pages_to_keep_are_left(self):
        data, pages, full = actpdf.join([_pdf(101, 102, 103), _pdf(201, 202, 203)], keep=[(1, 2), (5, 6)])
        self.assertEqual((_widths(data), pages, full), ([101, 102, 202, 203], 4, 6))
        self.assertEqual(actpdf.join([_pdf(101, 102, 103)], keep=[(2, 2)])[1:], (1, 3))   # 파일이 하나여도 덜어 낸다

    def test_pages_outside_the_file_are_an_error(self):
        with self.assertRaises(ValueError):
            actpdf.join([_pdf(101, 102)], keep=[(2, 3)])

    def test_the_same_input_gives_the_same_file(self):
        parts = [_pdf(101, 102), _pdf(201)]
        self.assertEqual(actpdf.join(parts, keep=[(1, 1), (3, 3)])[0], actpdf.join(parts, keep=[(1, 1), (3, 3)])[0])


@unittest.skipUnless(pikepdf, "pikepdf가 있어야 한다")
class EntryTest(unittest.TestCase):
    def test_the_line_says_where_the_file_came_from(self):
        data, line = actpdf.entry("32025R2548", "인증서 가격 이행규정", [_pdf(101, 102)])
        self.assertEqual((line["celex"], line["title"], line["pages"], line["parts"], line["bytes"]), ("32025R2548", "인증서 가격 이행규정", 2, 1, len(data)))
        self.assertEqual(line["url"], "https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=CELEX:32025R2548")
        self.assertTrue(line["file"].endswith("pdfs/32025R2548.pdf") and len(line["sha256"]) == 64)
        self.assertNotIn("fullPages", line)

    def test_a_trimmed_act_says_what_was_left_out(self):
        with mock.patch.dict(actpdf.KEEP, {"32099R0001": [(1, 1), (3, 4)]}), mock.patch.dict(actpdf.ABOUT, {"32099R0001": "조문과 한 나라의 표"}):
            data, line = actpdf.entry("32099R0001", "표가 긴 법령", [_pdf(101, 102, 103, 104, 105)])
        self.assertEqual((_widths(data), line["pages"], line["fullPages"], line["kept"]), ([101, 103, 104], 3, 5, [[1, 1], [3, 4]]))
        self.assertEqual(line["about"], "조문과 한 나라의 표")           # 남긴 쪽에 무엇이 있는지 화면이 알린다

    def test_the_pages_kept_of_the_long_acts_are_in_order(self):
        for celex, spans in actpdf.KEEP.items():
            flat = [number for span in spans for number in span]
            self.assertEqual(flat, sorted(flat), celex)
            self.assertIn(celex, {number for number, _ in actpdf.acts.ACTS})
            self.assertTrue(actpdf.ABOUT.get(celex), celex)


class TargetsTest(unittest.TestCase):
    def test_the_regulation_is_the_consolidated_version_the_site_shows(self):
        stored = {"entries": [{"name": "other", "code": "x"}, {"name": "cbam-consolidated", "code": "02023R0956-20270101"}]}
        with mock.patch.object(actpdf, "read_json", return_value=stored):
            found = actpdf.targets()
        self.assertEqual(found[0], ("02023R0956-20270101", "CBAM 규정 통합본"))
        self.assertEqual(found[1:], list(actpdf.acts.ACTS))

    def test_without_a_record_the_first_version_is_used(self):
        with mock.patch.object(actpdf, "read_json", return_value={}):
            self.assertEqual(actpdf.targets()[0][0], versions.FIRST)


@unittest.skipUnless(pikepdf, "pikepdf가 있어야 한다")
class CrawlTest(unittest.TestCase):
    def _run(self, folder, wanted, answers):
        """임시 폴더에서 한 번 돌린다. answers는 {CELEX: (파일들, 사유)}. 돌려주는 것은 (결과, 청한 법령들)."""
        root = pathlib.Path(folder)
        asked = []

        def files(celex):
            asked.append(celex)
            return answers[celex]

        def save(code, entries, report, incomplete=None):
            (root / f"{code}.json").write_text(json.dumps({"report": report, "entries": entries}), encoding="utf-8")

        with mock.patch.object(actpdf, "ROOT", root), mock.patch.object(actpdf, "FOLDER", root / "pdfs"), mock.patch.object(actpdf, "targets", return_value=wanted), \
                mock.patch.object(actpdf, "files", side_effect=files), mock.patch.object(actpdf, "save_index", side_effect=save):
            return actpdf.crawl(), asked

    def test_only_what_is_not_stored_is_asked_for(self):
        wanted = [("32025R0001", "하나"), ("32025R0002", "둘")]
        answers = {"32025R0001": ([_pdf(101)], ""), "32025R0002": ([_pdf(201), _pdf(202)], "")}
        with tempfile.TemporaryDirectory() as folder:
            result, asked = self._run(folder, wanted, answers)
            self.assertEqual((result, asked), ({"stored": 2, "fetched": 2, "removed": 0, "failures": []}, ["32025R0001", "32025R0002"]))
            self.assertEqual(_widths((pathlib.Path(folder) / "pdfs/32025R0002.pdf").read_bytes()), [201, 202])
            listing = pathlib.Path(folder) / "eu-pdfs.json"
            first = listing.read_text(encoding="utf-8")
            self.assertEqual([line["celex"] for line in json.loads(first)["entries"]], ["32025R0001", "32025R0002"])
            result, asked = self._run(folder, wanted, answers)
            self.assertEqual((result, asked), ({"stored": 2, "fetched": 0, "removed": 0, "failures": []}, []))
            self.assertEqual(listing.read_text(encoding="utf-8"), first)      # 받을 것이 없으면 목록도 그대로다

    def test_a_new_act_is_fetched_and_a_version_no_longer_shown_is_removed(self):
        answers = {"02023R0956-20251020": ([_pdf(101)], ""), "02023R0956-20270101": ([_pdf(111)], ""), "32025R0001": ([_pdf(201)], "")}
        with tempfile.TemporaryDirectory() as folder:
            self._run(folder, [("02023R0956-20251020", "CBAM 규정 통합본"), ("32025R0001", "하나")], answers)
            result, asked = self._run(folder, [("02023R0956-20270101", "CBAM 규정 통합본"), ("32025R0001", "하나")], answers)
            self.assertEqual((result, asked), ({"stored": 2, "fetched": 1, "removed": 1, "failures": []}, ["02023R0956-20270101"]))
            self.assertEqual(sorted(path.name for path in (pathlib.Path(folder) / "pdfs").iterdir()), ["02023R0956-20270101.pdf", "32025R0001.pdf"])
            entries = json.loads((pathlib.Path(folder) / "eu-pdfs.json").read_text(encoding="utf-8"))["entries"]
            self.assertEqual([line["celex"] for line in entries], ["02023R0956-20270101", "32025R0001"])

    def test_what_could_not_be_fetched_is_reported_and_tried_again_next_time(self):
        wanted = [("32025R0001", "하나"), ("32025R0002", "둘"), ("32025R0003", "셋")]
        answers = {"32025R0001": ([_pdf(101)], ""), "32025R0002": ([], "응답 404"), "32025R0003": ([b"not a pdf"], "")}
        with tempfile.TemporaryDirectory() as folder:
            result, _ = self._run(folder, wanted, answers)
            self.assertEqual((result["stored"], result["fetched"]), (1, 1))
            self.assertEqual(result["failures"][0], "32025R0002: 응답 404")
            self.assertTrue(result["failures"][1].startswith("32025R0003: "))  # 읽을 수 없는 파일도 실행을 멈추지 않는다
            answers["32025R0002"] = ([_pdf(201)], "")
            result, asked = self._run(folder, wanted, answers)
            self.assertEqual((result["stored"], result["fetched"], asked), (2, 1, ["32025R0002", "32025R0003"]))

    def test_a_file_over_the_limit_is_not_stored(self):
        with tempfile.TemporaryDirectory() as folder, mock.patch.object(actpdf, "LIMIT", 10):
            result, _ = self._run(folder, [("32025R0001", "하나")], {"32025R0001": ([_pdf(101)], "")})
            self.assertEqual((result["stored"], len(result["failures"])), (0, 1))
            self.assertIn("너무 큼", result["failures"][0])
            self.assertFalse((pathlib.Path(folder) / "pdfs/32025R0001.pdf").exists())


class HealthTest(unittest.TestCase):
    """실행 확인(tools.run.laws_health)은 싣는 법령 가운데 관보 PDF가 없는 것을 사유와 함께 알린다."""

    def test_missing_gazette_pdfs_are_reported_with_the_reason(self):
        from tools.run import laws_health

        wanted = [("32025R0001", "하나"), ("32025R0002", "둘"), ("32025R0003", "셋")]
        with tempfile.TemporaryDirectory() as folder:
            root = pathlib.Path(folder)
            (root / "pdfs").mkdir()
            (root / "pdfs/32025R0001.pdf").write_bytes(b"%PDF")
            report = root / "report.json"
            with mock.patch.object(actpdf, "FOLDER", root / "pdfs"), mock.patch.object(actpdf, "targets", return_value=wanted), mock.patch.object(laws_health, "ACT_PDF_REPORT", str(report)):
                self.assertEqual(laws_health._act_pdf_problems(), ["법령의 관보 PDF를 받아 두지 못함 2건(32025R0002, 32025R0003)"])      # 기록이 없어도 알린다
                report.write_text(json.dumps({"result": {"stored": 1, "failures": ["32025R0002: 응답 404", "32025R0009: 지금은 싣지 않는 법령"]}}), encoding="utf-8")
                self.assertEqual(laws_health._act_pdf_problems(), ["법령의 관보 PDF를 받아 두지 못함 2건(32025R0002, 32025R0003): 32025R0002: 응답 404"])
                report.write_text(json.dumps({"result": {"error": "ModuleNotFoundError: No module named 'pikepdf'"}}), encoding="utf-8")
                self.assertIn("No module named 'pikepdf'", laws_health._act_pdf_problems()[0])
                for celex in ("32025R0002", "32025R0003"):
                    (root / f"pdfs/{celex}.pdf").write_bytes(b"%PDF")
                self.assertEqual(laws_health._act_pdf_problems(), [])        # 모두 받아 두었으면 지난 기록의 사유는 알리지 않는다

    def test_every_act_the_site_shows_has_its_gazette_pdf(self):
        from tools.run import laws_health

        self.assertEqual(laws_health._act_pdf_problems(), [])
        stored = {line["celex"]: line for line in json.loads(pathlib.Path("collected/archive/eu-pdfs.json").read_text(encoding="utf-8"))["entries"]}
        self.assertEqual(sorted(stored), sorted(celex for celex, _ in actpdf.targets()))
        for celex, line in stored.items():
            self.assertEqual(pathlib.Path(line["file"]).stat().st_size, line["bytes"], celex)
            self.assertLessEqual(line["bytes"], actpdf.LIMIT, celex)


class FilesTest(unittest.TestCase):
    """자료 창구에 청하기: PDF의 꼴을 바꿔 가며 청하고, 여럿 가운데 고르라는 답이면 차례대로 모두 받는다."""

    def test_the_kinds_are_tried_until_one_is_served(self):
        seen = []

        def fetch(address, timeout, retries, headers):
            seen.append(headers["Accept"])
            return (200, {}, b"%PDF-1.7 body", "") if headers["Accept"] == actpdf.KINDS[2] else (404, {}, b"", "Not Found")

        with mock.patch.object(actpdf, "fetch", side_effect=fetch), mock.patch.object(actpdf.time, "sleep"):
            self.assertEqual(actpdf.files("32025R2548"), ([b"%PDF-1.7 body"], ""))
        self.assertEqual(seen, list(actpdf.KINDS[:3]))

    def test_no_kind_served_is_a_failure_with_the_answer(self):
        with mock.patch.object(actpdf, "fetch", return_value=(404, {}, b"", "Not Found")), mock.patch.object(actpdf.time, "sleep"):
            parts, why = actpdf.files("32025R2548")
        self.assertEqual(parts, [])
        self.assertIn("404", why)

    def test_several_files_are_fetched_in_their_order(self):
        base = actpdf.CELLAR.format(celex="32025R2547")
        choices = "".join(f'<a href="http://publications.europa.eu/resource/cellar/0a1b2c3d-1111-2222-3333-444455556666.0006.03/DOC_{number}">file {number}</a>' for number in (2, 1))

        def fetch(address, timeout, retries, headers):
            if address == base:
                return 300, {"Content-Type": "text/html; charset=utf-8"}, f"<html><body>{choices}</body></html>".encode("utf-8"), ""
            return 200, {}, b"%PDF " + address.rsplit("_", 1)[1].encode("ascii"), ""

        with mock.patch.object(actpdf, "fetch", side_effect=fetch), mock.patch.object(actpdf.time, "sleep"):
            self.assertEqual(actpdf.files("32025R2547"), ([b"%PDF 1", b"%PDF 2"], ""))


if __name__ == "__main__":
    unittest.main()
