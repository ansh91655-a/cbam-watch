"""화면 모듈을 한꺼번에 받게 하는 줄 넣기(tools/publish/preload.py)를 임시 폴더와 실제 화면 파일로 확인한다."""
import pathlib
import tempfile
import unittest

from tools.publish import preload

PAGE = '<!doctype html>\n<html><head>\n<title>t</title>\n</head>\n<body>\n<script type="module" src="js/app.js"></script>\n</body></html>\n'


def _site(folder, files, page=PAGE):
    root = pathlib.Path(folder)
    (root / "index.html").write_text(page, encoding="utf-8")
    for path, text in files.items():
        (root / path).parent.mkdir(parents=True, exist_ok=True)
        (root / path).write_text(text, encoding="utf-8")
    return root


class PreloadTest(unittest.TestCase):
    def test_imports_are_read_in_every_form_but_not_from_comments_or_dynamic_calls(self):
        text = ('import * as data from "./data.js";\n'
                'import {\n  a,\n  b,\n} from "../ui/dom.js";\n'
                "export { c } from './c.js';\n"
                'import "./side.js";\n'
                '// import { old } from "./old.js";\n'
                'const later = await import("./later.js");\n'
                'const text = "import x from ./not.js";\n'
                'import other from "https://example.org/x.js";\n')
        self.assertEqual(preload.imports(text), ["./data.js", "../ui/dom.js", "./c.js", "./side.js"])

    def test_modules_follow_the_chain_once_each_in_the_order_met(self):
        with tempfile.TemporaryDirectory() as folder:
            root = _site(folder, {
                "js/app.js": 'import { a } from "./a.js";\nimport { b } from "./views/b.js";\nconst f = () => import("./ui/late.js");\n',
                "js/a.js": 'import { c } from "./ui/c.js";\nexport const a = c;\n',
                "js/views/b.js": 'import { c } from "../ui/c.js";\nimport { a } from "../a.js";\nexport const b = c + a;\n',
                "js/ui/c.js": "export const c = 1;\n",
                "js/ui/late.js": "export const late = 1;\n",
            })
            self.assertEqual(preload.modules(root), (["js/app.js", "js/a.js", "js/views/b.js", "js/ui/c.js"], None))

    def test_the_lines_go_into_the_head_once_and_the_page_is_otherwise_untouched(self):
        with tempfile.TemporaryDirectory() as folder:
            root = _site(folder, {"js/app.js": 'import { a } from "./a.js";\n', "js/a.js": "export const a = 1;\n"})
            self.assertEqual(preload.inject(root), (2, ""))
            text = (root / "index.html").read_text(encoding="utf-8")
            self.assertIn('<link rel="modulepreload" href="js/app.js">\n<link rel="modulepreload" href="js/a.js">\n</head>', text)
            self.assertEqual(text.replace('<link rel="modulepreload" href="js/app.js">\n<link rel="modulepreload" href="js/a.js">\n', ""), PAGE)
            self.assertEqual(preload.inject(root), (0, "이미 들어 있음"))   # 두 번 넣지 않는다

    def test_a_broken_chain_or_an_unknown_page_leaves_the_page_as_it_is(self):
        with tempfile.TemporaryDirectory() as folder:
            root = _site(folder, {"js/app.js": 'import { a } from "./gone.js";\n'})
            self.assertEqual(preload.inject(root), (0, "이어진 모듈을 찾지 못함: js/gone.js"))
            self.assertEqual((root / "index.html").read_text(encoding="utf-8"), PAGE)
        with tempfile.TemporaryDirectory() as folder:
            root = _site(folder, {"js/app.js": ""}, page="<html><head></head><body></body></html>")
            self.assertEqual(preload.inject(root)[0], 0)
        with tempfile.TemporaryDirectory() as folder:
            self.assertEqual(preload.inject(folder), (0, "index.html이 없음"))

    def test_the_real_site_chain_is_whole_and_leaves_out_what_is_loaded_on_demand(self):
        paths, missing = preload.modules("site")
        self.assertIsNone(missing)
        self.assertEqual(paths[0], "js/app.js")
        self.assertEqual(len(paths), len(set(paths)))
        self.assertGreater(len(paths), 60)
        for late in ("js/ui/feedback.js", "js/ui/subscribe.js", "js/theme.js"):   # 그때그때 받는 것과 모듈이 아닌 것
            self.assertNotIn(late, paths)
        self.assertEqual(pathlib.Path("site/index.html").read_text(encoding="utf-8").count(preload.MARK), 1)


if __name__ == "__main__":
    unittest.main()
