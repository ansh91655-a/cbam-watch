"""자동 시험(도구 검사)이 도는 경로(.github/workflows/tests.yml): 시험이 읽는 저장소의 파일이 바뀌면 시험이 돈다.

시험은 도구만이 아니라 화면의 코드, 설정, 자료를 직접 읽는다. 새 시험이 새 파일을 읽기 시작했는데 경로에 넣지 않으면
그 파일만 고친 커밋에서는 시험이 돌지 않는다(2026-11-14의 검토에서 화면 모듈 여러 개가 그렇게 빠져 있었다).
"""
import pathlib
import re
import unittest

WORKFLOW = ".github/workflows/tests.yml"
# 시험의 글에 따옴표로 적힌 저장소의 파일 이름(node에 넘기는 글의 './site/js/…'도 든다). 코드와 설정만 본다:
# 자료(data)는 시험이 임시 폴더에 같은 이름으로 만들어 쓰기도 해서 이름만으로는 가릴 수 없고, 폴더째 넣었다(아래의 시험이 본다).
NAMED = re.compile(r"""["'](?:\./)?((?:site|console|sources|\.github)/[^"'\s*{}$\\]+|deploy\.json)["']""")


def patterns(text):
    """워크플로의 push 경로들(적힌 차례대로)."""
    return [line.split('"')[1] for line in text.split("jobs:")[0].splitlines() if line.strip().startswith('- "')]


def matcher(pattern):
    """GitHub의 경로 무늬를 정규식으로 옮긴다: **는 폴더를 넘어 무엇이든, *는 한 폴더 안에서 무엇이든."""
    out, at = "", 0
    while at < len(pattern):
        if pattern.startswith("**", at):
            out, at = out + ".*", at + 2
        elif pattern[at] == "*":
            out, at = out + "[^/]*", at + 1
        else:
            out, at = out + re.escape(pattern[at]), at + 1
    return re.compile(out + r"\Z")


def runs_on(path, rules):
    """그 파일만 바뀐 커밋에서 워크플로가 도는가. 뒤에 적힌 무늬가 이긴다(!로 시작하는 무늬는 뺀다)."""
    hit = False
    for rule in rules:
        negated = rule.startswith("!")
        if matcher(rule[1:] if negated else rule).match(path):
            hit = not negated
    return hit


class TriggersTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rules = patterns(pathlib.Path(WORKFLOW).read_text(encoding="utf-8"))

    def test_the_patterns_are_read_the_way_github_reads_them(self):
        self.assertTrue(runs_on("site/404.html", ["site/*.html"]))
        self.assertFalse(runs_on("site/js/x.html", ["site/*.html"]))                      # *는 폴더를 넘지 않는다
        self.assertTrue(runs_on("site/js/views/rules/side.js", ["site/js/**"]))
        self.assertFalse(runs_on("data/laws-ko/a.json", ["data/**", "!data/laws-ko/**"]))   # 뒤에 적은 빼는 무늬가 이긴다
        self.assertTrue(runs_on("data/laws-ko/a.json", ["!data/laws-ko/**", "data/**"]))    # 차례가 바뀌면 듣지 않는다
        self.assertFalse(runs_on("deploy.json.bak", ["deploy.json"]))

    def test_code_and_settings_the_tests_name_are_watched(self):
        """시험이 이름을 적어 읽는 화면의 코드, 운영 콘솔, 설정, 워크플로는 모두 경로에 들어 있다."""
        missing = {}
        for test in sorted(pathlib.Path("tests").glob("test_*.py")):
            for name in NAMED.findall(test.read_text(encoding="utf-8")):
                if pathlib.Path(name).is_file() and not runs_on(name, self.rules):
                    missing.setdefault(name, []).append(test.name)
        self.assertEqual(missing, {})

    def test_the_tools_and_the_tests_themselves_are_watched(self):
        for name in ("tools/publish/build_site.py", "tools/sitecheck/checks/axe_rules.mjs", "tests/test_triggers.py", "requirements.txt", WORKFLOW):
            self.assertTrue(runs_on(name, self.rules), name)

    def test_data_is_watched_like_the_site_deploy_but_not_at_every_translation_batch(self):
        """사이트에 싣는 자료가 바뀌면 돈다(날마다의 게시도). 번역은 묶음마다가 아니라 실행이 끝났다는 표가 바뀔 때 한 번 돈다."""
        for name in sorted(str(path) for path in pathlib.Path("data").glob("*.json")):
            self.assertTrue(runs_on(name, self.rules), name)
        self.assertFalse(runs_on("data/laws-ko/32023R0956.json", self.rules))
        self.assertTrue(runs_on("stamps/translated.json", self.rules))
        self.assertLess(self.rules.index("data/**"), self.rules.index("!data/laws-ko/**"))   # 빼는 줄은 넣는 줄 뒤에 있어야 듣는다
        for name in ("language/glossary.json", "originals/text/guide-1.txt", "originals/units/guide-1.json"):
            self.assertTrue(runs_on(name, self.rules), name)

    def test_what_is_left_out_is_left_out_on_purpose(self):
        """시험이 읽지 않는 것과, 자동 실행이 돌 때마다 바뀌고 그 실행이 스스로 검사하는 것에는 돌지 않는다."""
        # (화면 쪽의 두 이름은 있는 파일의 이름이 아니다: 있는 파일을 적으면 위의 시험이 '시험이 읽는 파일'로 센다)
        for name in ("site/css/any.css", "site/assets/thumbs/any.webp", "collected/archive/ec-news.json", "originals/state.json",
                     "language/translation-terms.json", "language/translation-reviews.json", "locks/translating.json", "README.md"):
            self.assertFalse(runs_on(name, self.rules), name)


if __name__ == "__main__":
    unittest.main()
