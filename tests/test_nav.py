"""사이트의 화면과 묶음을 적은 표(site/js/nav/map.js)와, 그 표를 따라야 하는 것들이 서로 맞는지.

머리글의 주 메뉴와 바닥 메뉴(index.html), 주소를 화면으로 잇는 곳(router.js, app.js), 화면 안의 탭(ui/tabs.js), 전체 메뉴(ui/allmenu.js), 아이콘(ui/icons.js)을 본다.
"""
import json
import pathlib
import re
import shutil
import subprocess
import unittest

SCRIPT = r"""
import { allScreens, GROUPS, groupOf, SCREENS, screensOf, UNDER } from './site/js/nav/map.js';
import { PAGES } from './site/js/search/pages.js';
console.log(JSON.stringify({
  groups: GROUPS, screens: SCREENS, under: UNDER, all: allScreens(), pages: PAGES,
  of: Object.fromEntries(['home', 'item', 'law', 'changes', 'pdf', 'calc', 'sector', 'handbook', 'terms', 'about', 'docs', 'search', 'design'].map((view) => [view, (groupOf(view) || {}).key || null])),
  first: GROUPS.map((group) => screensOf(group)[0].href),
}));
"""


@unittest.skipUnless(shutil.which("node"), "node가 없으면 화면의 표는 시험하지 않는다")
class MapTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        done = subprocess.run(["node", "--input-type=module", "-e", SCRIPT], capture_output=True, text=True)
        if done.returncode:
            raise AssertionError(done.stderr[-1500:])
        cls.seen = json.loads(done.stdout)
        cls.page = pathlib.Path("site/index.html").read_text(encoding="utf-8")
        cls.views = [view for group in cls.seen["groups"] for view in group["views"]]

    def test_every_screen_sits_in_exactly_one_group_and_is_fully_described(self):
        self.assertEqual(sorted(self.views), sorted(self.seen["screens"]))       # 표의 화면은 모두 어느 묶음에 들고, 두 번 들지 않는다
        self.assertEqual(len(self.views), len(set(self.views)))
        icons = pathlib.Path("site/js/ui/icons.js").read_text(encoding="utf-8")
        for view, one in self.seen["screens"].items():
            for key in ("name", "icon", "about"):
                self.assertTrue(one.get(key), (view, key))
            self.assertIn(f' "{one["icon"]}": ', icons, view)                    # 아이콘이 실제로 있다
            self.assertTrue(one.get("words"), view)
            if view not in ("home", "about"):
                self.assertTrue(one.get("detail"), view)                         # 안내 화면에 싣는 설명
        self.assertEqual([one["href"] for one in self.seen["all"]], [f"#{view}" for view in self.views])

    def test_screens_outside_the_menu_fall_under_the_right_group(self):
        self.assertEqual(self.seen["of"], {"home": "home", "item": "news", "law": "library", "changes": "library", "pdf": "library", "calc": "goods", "sector": "goods",
                                           "handbook": "handbook", "terms": "handbook", "about": "handbook", "docs": "library", "search": None, "design": None})

    def test_the_header_menu_in_the_page_follows_the_table(self):
        nav = self.page.split('<nav class="site-nav"', 1)[1].split("</nav>", 1)[0]
        links = re.findall(r'<a href="(#\w+)" data-key="(\w+)"(?: data-menu="(\w+)")?>([^<]+)</a>', nav)
        self.assertEqual(len(links), nav.count("<a "))                           # 모든 링크가 이 꼴이다
        groups = self.seen["groups"]
        self.assertEqual([(href, key, name) for href, key, _, name in links], [(first, group["key"], group["name"]) for group, first in zip(groups, self.seen["first"])])
        # 첫 화면 말고는 모두 펼침 목록이 있다(목록의 내용은 js/ui/navmenu.js의 menuLists: tests/test_search.py가 본다)
        self.assertEqual([menu for _, _, menu, _ in links], [""] + [group["key"] for group in groups[1:]])

    def test_the_footer_lists_every_screen(self):
        foot = self.page.split('<nav class="foot-links"', 1)[1].split("</nav>", 1)[0]
        links = re.findall(r'<a href="(#\w+)">([^<]+)</a>', foot)
        self.assertEqual(links, [(one["href"], one["name"]) for one in self.seen["all"]])

    def test_every_screen_can_be_routed_and_named(self):
        router = pathlib.Path("site/js/router.js").read_text(encoding="utf-8")
        app = pathlib.Path("site/js/app.js").read_text(encoding="utf-8")
        routed = set(json.loads(re.search(r"const VIEWS = (\[[^\]]*\]);", router).group(1)))
        drawn = set(re.findall(r"\w+", re.search(r"const VIEWS = \{([^}]*)\};", app).group(1)))
        named = set(re.findall(r"(\w+): \"", re.search(r"const NAMES = \{([^}]*)\};", app).group(1)))
        wanted = set(self.views) | set(self.seen["under"])
        self.assertLessEqual(wanted, routed)
        self.assertEqual(routed, drawn)                                          # 주소로 갈 수 있는 화면은 모두 그릴 수 있다
        self.assertLessEqual(wanted - {"home"}, named)                           # 브라우저 탭에 적는 이름(첫 화면은 사이트 이름만 적는다)
        for under, parent in self.seen["under"].items():
            self.assertIn(parent, self.views, under)

    def test_the_search_shortcuts_come_from_the_table(self):
        pages = self.seen["pages"]
        self.assertEqual([page["href"] for page in pages], [one["href"] for one in self.seen["all"]])
        by_href = {page["href"]: page for page in pages}
        self.assertEqual(by_href["#price"]["name"], "CBAM 인증서 가격")           # 길게 부르는 이름으로 싣고
        self.assertIn("인증서 가격", by_href["#price"]["words"])                  # 메뉴의 짧은 이름으로도 찾는다
        self.assertEqual(by_href["#news"]["name"], "소식")

    def test_views_use_the_group_tabs_and_the_full_menu_knows_its_groups(self):
        tabs = pathlib.Path("site/js/ui/tabs.js").read_text(encoding="utf-8")
        self.assertIn("export function groupTabs(view)", tabs)
        called = {}
        for path in pathlib.Path("site/js/views").rglob("*.js"):
            for view in re.findall(r'groupTabs\("(\w+)"\)', path.read_text(encoding="utf-8")):
                called.setdefault(view, []).append(path.name)
        many = {view for group in self.seen["groups"] if len(group["views"]) > 1 for view in group["views"]}
        self.assertEqual(set(called), many)                                      # 화면이 여럿인 묶음의 화면은 모두 탭을 그린다
        menu = pathlib.Path("site/js/ui/allmenu.js").read_text(encoding="utf-8")
        columns = json.loads(re.search(r"const COLUMNS = (\[\[.*?\]\]);", menu).group(1))
        self.assertEqual(sorted(key for column in columns for key in column), sorted(group["key"] for group in self.seen["groups"]))
        self.assertRegex(self.page, r'<button class="all-menu" id="all-menu" type="button" aria-haspopup="dialog"[^>]*>.*?<span>전체 메뉴</span></button>')


if __name__ == "__main__":
    unittest.main()
