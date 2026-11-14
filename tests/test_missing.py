"""없는 주소로 왔을 때의 안내: 주소를 화면으로 가르는 것(site/js/router.js), 찾으려던 화면을 어림하는 것(site/js/nav/guess.js),
사이트에 없는 경로에서 GitHub Pages가 보여 주는 화면(site/404.html)."""
import json
import pathlib
import re
import shutil
import subprocess
import unittest

SCRIPT = r"""
globalThis.location = { hash: '' };   // 라우터는 처음 읽힐 때 지금의 주소를 적어 둔다
const { MISSING, route } = await import('./site/js/router.js');
const { guess } = await import('./site/js/nav/guess.js');
const views = (text) => guess(text).map((one) => one.view);
console.log(JSON.stringify({
  missing: MISSING,
  routes: Object.fromEntries(['', '#', '#main', '#news', '#news-price', '#law-32023R0956.art-7', '#rule', '#rules', '#glossary-x', '#missing', '#%EC%9A%A9%EC%96%B4'].map((hash) => [hash, route(hash)])),
  guesses: Object.fromEntries(['rule', 'term', 'glossary', 'handbooks', 'regulation-2023', 'deadline', 'cal', '%EC%9A%A9%EC%96%B4', '용어집', 'new', 'xy', 'zzzz', '', 'wp-login.php'].map((text) => [text, views(text)])),
  shape: guess('rule')[0],
}));
"""


@unittest.skipUnless(shutil.which("node"), "node가 없으면 화면의 셈은 시험하지 않는다")
class RouteTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        done = subprocess.run(["node", "--input-type=module", "-e", SCRIPT], capture_output=True, text=True)
        if done.returncode:
            raise AssertionError(done.stderr[-1500:])
        cls.seen = json.loads(done.stdout)

    def test_an_address_that_is_not_a_screen_goes_to_the_guide(self):
        routes = self.seen["routes"]
        for hash_ in ("", "#", "#main"):                                             # 글이 없는 주소와 '본문으로 건너뛰기'의 자리는 첫 화면이다
            self.assertEqual(routes[hash_], {"name": "home", "arg": ""}, hash_)
        self.assertEqual(routes["#news"], {"name": "news", "arg": ""})
        self.assertEqual(routes["#news-price"], {"name": "news", "arg": "price"})
        self.assertEqual(routes["#law-32023R0956.art-7"], {"name": "law", "arg": "32023R0956.art-7"})
        self.assertEqual(routes["#rules"], {"name": "rules", "arg": ""})
        self.assertEqual(routes["#rule"], {"name": "missing", "arg": "rule"})         # 화면의 이름이 아니면 안내 화면으로 가고, 주소의 글을 그대로 넘긴다
        self.assertEqual(routes["#glossary-x"], {"name": "missing", "arg": "glossary-x"})
        self.assertEqual(routes["#missing"], {"name": "missing", "arg": "missing"})   # 안내 화면의 이름은 주소로 쓰지 않는다
        self.assertEqual(self.seen["missing"], "missing")

    def test_the_screen_that_was_meant_is_guessed_from_the_first_word(self):
        guesses = self.seen["guesses"]
        self.assertEqual(guesses["rule"], ["rules"])                                  # 앞머리가 같은 이름
        self.assertEqual(guesses["term"], ["terms"])
        self.assertEqual(guesses["handbooks"], ["handbook"])
        self.assertEqual(guesses["glossary"], ["terms"])                              # 그 화면을 찾을 때 쓸 만한 말
        self.assertEqual(guesses["regulation-2023"], ["laws"])                        # 첫 낱말만 본다
        self.assertEqual(guesses["deadline"], ["calendar"])
        self.assertEqual(guesses["%EC%9A%A9%EC%96%B4"], ["terms"])                    # 한글 주소는 풀어서 견준다('용어')
        self.assertEqual(guesses["용어집"], ["terms"])
        self.assertEqual(guesses["new"], ["news"])
        self.assertEqual(guesses["cal"][0], "calendar")                               # 여럿이 걸리면 메뉴의 차례대로, 셋까지만
        self.assertLessEqual(len(guesses["cal"]), 3)
        for text in ("xy", "zzzz", "", "wp-login.php"):                               # 두 글자와 엉뚱한 말에는 어림하지 않는다
            self.assertEqual(guesses[text], [], text)
        self.assertEqual({key: self.seen["shape"][key] for key in ("view", "href", "title")}, {"view": "rules", "href": "#rules", "title": "규제"})

    def test_the_guide_is_drawn_by_its_own_view(self):
        app = pathlib.Path("site/js/app.js").read_text(encoding="utf-8")
        self.assertIn('import { render as missing } from "./views/missing.js";', app)
        view = pathlib.Path("site/js/views/missing.js").read_text(encoding="utf-8")
        for needed in ('guess(arg)', 'allScreens()', 'role: "search"', "return TITLE;"):
            self.assertIn(needed, view)


class PageTest(unittest.TestCase):
    """사이트에 없는 경로에서 보이는 화면(site/404.html). 어느 깊이에서도 열리므로 링크를 온전한 주소로 적는다."""

    @classmethod
    def setUpClass(cls):
        cls.page = pathlib.Path("site/404.html").read_text(encoding="utf-8")
        cls.site = json.loads(pathlib.Path("site/site.config.json").read_text(encoding="utf-8"))["url"]

    def test_it_is_not_indexed_and_says_what_it_is(self):
        self.assertIn('<meta name="robots" content="noindex, nofollow">', self.page)
        self.assertIn("<h1>찾는 주소가 없습니다</h1>", self.page)
        self.assertIn("비공식 사이트", self.page)

    def test_every_link_goes_to_a_screen_of_this_site(self):
        router = pathlib.Path("site/js/router.js").read_text(encoding="utf-8")
        views = set(json.loads(re.search(r"const VIEWS = (\[[^\]]*\]);", router).group(1)))
        links = re.findall(r'href="([^"]+)"', self.page)
        self.assertGreaterEqual(len(links), 6)
        for link in links:
            self.assertTrue(link.startswith(self.site), link)                         # 사이트의 주소(site.config.json의 url)로 시작한다
            rest = link[len(self.site):]
            self.assertTrue(rest in ("", "assets/favicon.svg") or (rest.startswith("#") and rest[1:] in views), link)
        self.assertIn(f'id="home" href="{self.site}"', self.page)                     # 경로를 사이트의 주소로 넘길 때 이 링크의 주소를 쓴다

    def test_the_build_carries_it_to_the_top_of_the_site(self):
        build = pathlib.Path("tools/publish/build_site.py").read_text(encoding="utf-8")
        self.assertIn('shutil.copytree("site", out', build)                           # site/ 아래의 파일은 그대로 사이트의 맨 위에 실린다


if __name__ == "__main__":
    unittest.main()
