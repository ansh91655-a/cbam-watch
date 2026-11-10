"""robots.txt를 지키는지: 어느 묶음을 따르는지, 어느 줄이 이기는지, 읽지 못한 날에는 어떻게 하는지."""
import datetime
import os
import tempfile
import unittest

from tools.common import robots

KST = datetime.timezone(datetime.timedelta(hours=9))
SAMPLE = """
# 보기
User-agent: *
Disallow: /private/
Disallow: /search
Allow: /private/open/
Disallow: /*.pdf$
Crawl-delay: 5

User-agent: badbot
User-agent: otherbot
Disallow: /

Sitemap: https://example.org/sitemap.xml
"""


def _rules(text):
    return robots.rules_for(robots.parse(text))


class RulesTest(unittest.TestCase):
    def test_the_longest_matching_line_wins_and_allow_wins_a_tie(self):
        rules = _rules(SAMPLE)
        self.assertTrue(robots.permits(rules, "/"))
        self.assertTrue(robots.permits(rules, "/news/2026"))
        self.assertFalse(robots.permits(rules, "/private/x"))
        self.assertTrue(robots.permits(rules, "/private/open/x"))
        self.assertFalse(robots.permits(rules, "/search?q=cbam"))
        self.assertTrue(robots.permits(_rules("User-agent: *\nDisallow: /a\nAllow: /a"), "/a/b"))

    def test_wildcards_and_the_end_mark(self):
        rules = _rules(SAMPLE)
        self.assertFalse(robots.permits(rules, "/docs/guide.pdf"))
        self.assertTrue(robots.permits(rules, "/docs/guide.pdf?download=1"))  # '$'는 주소의 끝에만 맞는다
        self.assertFalse(robots.permits(_rules("User-agent: *\nDisallow: /*?page="), "/list?page=2"))

    def test_an_empty_disallow_blocks_nothing_and_no_rules_allow_everything(self):
        self.assertTrue(robots.permits(_rules("User-agent: *\nDisallow:"), "/anything"))
        self.assertTrue(robots.permits(_rules("<html><body>없는 쪽</body></html>"), "/anything"))
        self.assertFalse(robots.permits(_rules("User-agent: *\nDisallow: /"), "/anything"))

    def test_a_group_naming_this_collector_replaces_the_group_for_everyone(self):
        text = "User-agent: *\nDisallow: /\n\nUser-agent: CBAM-Watch\nDisallow: /admin/\n"
        self.assertTrue(robots.permits(_rules(text), "/news"))
        self.assertFalse(robots.permits(_rules(text), "/admin/x"))

    def test_what_a_site_forbids_claude_is_forbidden_to_this_collector_too(self):
        text = "User-agent: *\nAllow: /\n\nUser-agent: ClaudeBot\nUser-agent: GPTBot\nDisallow: /\n"
        self.assertFalse(robots.permits(_rules(text), "/news"))
        self.assertTrue(robots.permits(_rules("User-agent: *\nAllow: /\n\nUser-agent: GPTBot\nDisallow: /\n"), "/news"))

    def test_rules_of_several_groups_naming_us_are_joined(self):
        text = "User-agent: cbam-watch\nDisallow: /a/\n\nUser-agent: anthropic-ai\nDisallow: /b/\n"
        rules = _rules(text)
        self.assertFalse(robots.permits(rules, "/a/1"))
        self.assertFalse(robots.permits(rules, "/b/1"))
        self.assertTrue(robots.permits(rules, "/c/1"))


class GateTest(unittest.TestCase):
    def setUp(self):
        self.previous = os.getcwd()
        self.folder = tempfile.TemporaryDirectory()
        os.chdir(self.folder.name)
        self.clock = datetime.datetime(2026, 11, 11, 6, 10, tzinfo=KST)
        self.calls = []

    def tearDown(self):
        os.chdir(self.previous)
        self.folder.cleanup()

    def _gate(self, answers):
        def load(address):
            self.calls.append(address)
            return answers[address]
        return robots.Gate(load=load, now=lambda: self.clock)

    def test_it_asks_each_site_once_and_remembers_blocked_addresses(self):
        gate = self._gate({"https://a.example/robots.txt": (200, "User-agent: *\nDisallow: /private/")})
        self.assertEqual(gate.check("https://a.example/news"), (True, ""))
        self.assertFalse(gate.check("https://a.example/private/x")[0])
        self.assertTrue(gate.check("https://A.example/robots.txt")[0])
        self.assertEqual(self.calls, ["https://a.example/robots.txt"])
        self.assertEqual([url for url, _ in robots.blocked_today("2026-11-11")], ["https://a.example/private/x"])
        self.assertEqual(robots.blocked_today("2026-11-12"), [])

    def test_a_missing_file_allows_everything(self):
        gate = self._gate({"https://b.example/robots.txt": (404, "없음")})
        self.assertTrue(gate.check("https://b.example/anything")[0])

    def test_an_unreadable_file_falls_back_to_the_stored_copy_or_blocks_the_site(self):
        self._gate({"https://c.example/robots.txt": (200, "User-agent: *\nDisallow: /x/")}).check("https://c.example/")
        self.clock += datetime.timedelta(days=1)
        later = self._gate({"https://c.example/robots.txt": (503, ""), "https://d.example/robots.txt": (0, "")})
        self.assertTrue(later.check("https://c.example/news")[0])       # 전에 받아 둔 규칙을 쓴다
        self.assertFalse(later.check("https://c.example/x/1")[0])
        allowed, why = later.check("https://d.example/news")           # 받아 둔 것이 없으면 받지 않는다
        self.assertFalse(allowed)
        self.assertIn("읽지 못해", why)

    def test_a_stored_copy_is_reused_within_the_same_run_and_refetched_the_next_day(self):
        answers = {"https://e.example/robots.txt": (200, "User-agent: *\nDisallow:")}
        self._gate(answers).check("https://e.example/")
        self._gate(answers).check("https://e.example/")  # 같은 실행의 다른 프로그램
        self.assertEqual(len(self.calls), 1)
        self.clock += datetime.timedelta(hours=24)
        self._gate(answers).check("https://e.example/")
        self.assertEqual(len(self.calls), 2)

    def test_too_many_requests_counts_as_unreadable(self):
        allowed, _ = self._gate({"https://f.example/robots.txt": (429, "")}).check("https://f.example/x")
        self.assertFalse(allowed)

    def test_addresses_that_are_not_web_pages_are_not_checked(self):
        gate = self._gate({})
        self.assertTrue(gate.check("mailto:someone@example.org")[0])
        self.assertEqual(self.calls, [])


class FetchTest(unittest.TestCase):
    def test_fetch_does_not_open_a_blocked_address(self):
        from tools.common import net
        previous = robots._gate
        robots._gate = robots.Gate(load=lambda address: (200, "User-agent: *\nDisallow: /"), cache="")
        try:
            status, headers, body, error = net.fetch("https://blocked.example/page", retries=0)
        finally:
            robots._gate = previous
        self.assertEqual((status, body), (0, b""))
        self.assertIn("robots.txt", error)


class HealthTest(unittest.TestCase):
    def test_blocked_addresses_are_reported_once_per_day_grouped_by_site(self):
        from tools.run import health
        blocked = [("https://a.example/x", "robots.txt가 자동 읽기를 막음"), ("https://a.example/y", "robots.txt가 자동 읽기를 막음"), ("https://b.example/z", "robots.txt를 읽지 못해 받지 않음(응답 503)")]
        found = health._robots_problems("2026-11-11", blocked)
        self.assertEqual(len(found), 1)
        self.assertIn("3건", found[0])
        self.assertIn("a.example, b.example", found[0])
        self.assertEqual(health._robots_problems("2026-11-11", []), [])


if __name__ == "__main__":
    unittest.main()
