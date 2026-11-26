"""전달한 한글 파일(HWPX)의 표기를 바꾸는 도구(tools/hwp/patch.py)."""
import contextlib
import io
import json
import pathlib
import tempfile
import unittest
import zipfile

from tools.hwp import patch

SECTION = '<hs:sec><hp:p><hp:run><hp:t>공동 중앙 플랫폼의 데이터 컨트롤러와 컨트롤러</hp:t></hp:run></hp:p><hp:p><hp:run><hp:t>공동 중</hp:t></hp:run><hp:run><hp:t>앙 플랫폼</hp:t></hp:run></hp:p></hs:sec>'


class Patch(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.folder.name)
        with zipfile.ZipFile(self.root / "in.hwpx", "w") as box:
            box.writestr(zipfile.ZipInfo("mimetype"), "application/hwp+zip")   # 압축하지 않고 맨 앞에 둔다
            box.writestr("Contents/header.xml", "<head>공동 중앙 플랫폼</head>", zipfile.ZIP_DEFLATED)
            box.writestr("Contents/section0.xml", SECTION, zipfile.ZIP_DEFLATED)
        (self.root / "pairs.json").write_text(json.dumps([["데이터 컨트롤러", "개인정보처리자"], ["컨트롤러", "개인정보처리자"], ["공동 중앙 플랫폼", "공통 중앙 플랫폼"]], ensure_ascii=False), encoding="utf-8")

    def tearDown(self):
        self.folder.cleanup()

    def run_patch(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = patch.main(str(self.root / "in.hwpx"), str(self.root / "out.hwpx"), str(self.root / "pairs.json"))
        return code, json.loads(out.getvalue())

    def test_words_are_swapped_in_order_and_only_in_the_body(self):
        code, report = self.run_patch()
        with zipfile.ZipFile(self.root / "out.hwpx") as box:
            names = [info.filename for info in box.infolist()]
            kinds = [info.compress_type for info in box.infolist()]
            body = box.read("Contents/section0.xml").decode("utf-8")
            head = box.read("Contents/header.xml").decode("utf-8")
        self.assertEqual(names, ["mimetype", "Contents/header.xml", "Contents/section0.xml"])
        self.assertEqual(kinds, [zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED, zipfile.ZIP_DEFLATED])
        self.assertIn("공통 중앙 플랫폼의 개인정보처리자와 개인정보처리자", body)   # '데이터 컨트롤러'를 먼저 바꿔 '데이터 개인정보처리자'가 되지 않는다
        self.assertEqual(head, "<head>공동 중앙 플랫폼</head>")                      # 글이 아닌 파일은 건드리지 않는다
        self.assertEqual(report["바꾼 곳"], {"데이터 컨트롤러": 1, "컨트롤러": 1, "공동 중앙 플랫폼": 1})
        self.assertEqual(code, 1)   # 글 조각 사이에서 끊긴 낱말이 남아 있다

    def test_a_word_split_across_runs_is_reported_as_left(self):
        _, report = self.run_patch()
        self.assertEqual(report["남은 곳"], {"공동 중앙 플랫폼": 1})


if __name__ == "__main__":
    unittest.main()
