"""화면 점검 도구(tools/sitecheck) 가운데 브라우저 없이 볼 수 있는 것: 무엇을 검사할지 정하는 일과 사이트를 띄우는 일."""
import json
import pathlib
import shutil
import subprocess
import tempfile
import unittest


@unittest.skipUnless(shutil.which("node"), "node가 없으면 화면 점검 도구는 시험하지 않는다")
class SitecheckTest(unittest.TestCase):
    def setUp(self):
        self.site = pathlib.Path(tempfile.mkdtemp())
        (self.site / "data").mkdir()
        self.addCleanup(shutil.rmtree, self.site, ignore_errors=True)

    def write(self, name, body):
        (self.site / "data" / name).write_text(json.dumps(body, ensure_ascii=False), encoding="utf-8")

    def node(self, script, *args):
        done = subprocess.run(["node", "--input-type=module", "-e", script, *args], capture_output=True, text=True, check=True)
        return json.loads(done.stdout)

    def test_the_plan_follows_the_data_of_the_built_site(self):
        self.write("items.json", {"items": [{"id": "old", "published": "2026-01-02"}, {"id": "gone", "published": "2026-12-01", "withdrawn": True}, {"id": "new", "published": "2026-11-10"}]})
        self.write("topics.json", {"topics": [{"code": "law"}]})
        self.write("regulations.json", {"groups": [{"code": "eu-acts"}], "regulations": [{"id": "a"}, {"id": "b", "figure": "cbam-factor"}, {"id": "c", "positions": {}}]})
        self.write("calc.json", {"goods": [["72081000", "x", "steel", [], [], []]]})
        plan = self.node("import { plan } from './tools/sitecheck/plan.mjs'; console.log(JSON.stringify(plan(process.argv[1])));", str(self.site))
        self.assertIn("#item-new", plan["views"])          # 가장 최근 소식(요약을 내린 것은 빼고)
        self.assertNotIn("#item-gone", plan["views"])
        for view in ("#home", "#news-law", "#rules-eu-acts", "#calc", "#calc-72081000", "#calendar-2027", "#cn-7208", "#search", "#search-7208", "#search-%EA%B8%B0%EB%B3%B8%EA%B0%92"):
            self.assertIn(view, plan["views"])
        self.assertIn("#search-%EA%B8%B0%EB%B3%B8%EA%B0%92", plan["axeViews"])  # 검색 결과 화면도 접근성 검사에 든다
        self.assertEqual(plan["rules"], ["#rules-a", "#rules-b", "#rules-c"])
        self.assertIn("#rules-b", plan["axeViews"])        # 그림이 있는 규제와 비교표가 있는 규제는 접근성 검사에 든다
        self.assertIn("#rules-c", plan["axeViews"])
        for view in ("#rules-recent", "#rules-recent-90", "#rule", "#nowhere-at-all"):   # 규제 변화 기록과, 없는 주소의 안내 화면(어림할 수 있는 주소와 없는 주소)
            self.assertIn(view, plan["views"])
        self.assertIn("#rules-recent", plan["axeViews"])
        self.assertIn("#rule", plan["axeViews"])
        self.assertEqual(plan["themes"], ["", "?theme=white", "?theme=midnight"])

    def test_a_chapter_on_another_scheme_is_looked_at_on_its_own(self):
        # 다른 제도를 다루는 장(scope가 있는 장)은 절이 가장 많아도 '절이 가장 많은 장'의 자리를 차지하지 않고 따로 본다.
        # 그 범위의 용어가 있으면 글 속 용어 풀이도 그 장에서 다뤄 보고, 풀이 칸의 링크가 그 장 안으로만 가는지 본다
        sections = lambda count, **extra: [{"id": f"s{at}", "title": "절", **extra} for at in range(count)]
        self.write("handbook.json", {"chapters": [{"id": "overview", "title": "한눈에 보기", "sections": sections(2)}, {"id": "certificates", "title": "인증서 수", "sections": sections(3)},
                                                  {"id": "uk", "title": "영국 CBAM", "scope": "uk", "sections": sections(5, figure={"kind": "flow"})}]})
        self.write("gloss.json", {"terms": [{"forms": ["내재배출량"], "ko": "내재배출량"}, {"forms": ["회계기간"], "ko": "회계기간", "scope": "uk"}], "scopes": {"uk": []}})
        plan = self.node("import { plan } from './tools/sitecheck/plan.mjs'; console.log(JSON.stringify(plan(process.argv[1])));", str(self.site))
        self.assertIn("#handbook-certificates", plan["views"])
        self.assertEqual(plan["views"].count("#handbook-uk"), 1)
        self.assertIn("#handbook-uk", plan["axeViews"])
        self.assertEqual(plan["glossViews"], ["#handbook-certificates", "#handbook-uk"])
        self.assertEqual(plan["glossScoped"], {"#handbook-uk": "#handbook-uk."})
        # 그 범위의 용어가 없으면 그 장에서는 용어 풀이를 다뤄 보지 않는다(표시할 것이 없다)
        self.write("gloss.json", {"terms": [{"forms": ["내재배출량"], "ko": "내재배출량"}]})
        plan = self.node("import { plan } from './tools/sitecheck/plan.mjs'; console.log(JSON.stringify(plan(process.argv[1])));", str(self.site))
        self.assertEqual((plan["glossViews"], plan["glossScoped"]), (["#handbook-certificates"], {}))

    def test_links_in_a_scrolled_chip_row_are_not_taken_for_skip_links(self):
        # 좁은 화면에서 가로로 넘겨 보는 고르기 줄(.side-nav)의 링크가 화면 왼쪽 밖에 놓이면 axe는 건너뛰기 링크로 본다. 그 줄 안의 것만 세지 않는다
        # 어느 자리 안의 요소인지는 화면에서 요소로 가려 place에 적어 온다. 고르는 말(at)에는 윗자리가 적히지 않을 수 있어 글자로 가리지 않는다
        inside, real = {"at": 'a[href$="eu-law"]', "place": ".side-nav"}, {"at": ".skip", "place": ""}
        named = {"at": '.side-nav-like > a[href$="#news"]', "place": ""}   # 고르는 말에 비슷한 글자가 있어도 그 줄 안의 요소가 아니면 센다
        found = [{"id": "skip-link", "impact": "moderate", "nodes": [{"at": '.side-nav > a[href$="#rules"]', "place": ".side-nav"}, inside]},
                 {"id": "skip-link", "impact": "moderate", "nodes": [inside, real, named]},
                 {"id": "color-contrast", "impact": "serious", "nodes": [inside]}]
        script = ("import { kept, PLACES } from './tools/sitecheck/checks/axe_rules.mjs';"
                  " console.log(JSON.stringify({ kept: kept(JSON.parse(process.argv[1])), places: PLACES }));")
        seen = self.node(script, json.dumps(found))
        self.assertEqual(seen["kept"], [{"id": "skip-link", "impact": "moderate", "nodes": [real, named]},   # 진짜 건너뛰기 링크와 그 줄 밖의 것은 남는다
                                        {"id": "color-contrast", "impact": "serious", "nodes": [inside]}])   # 다른 위반은 그 줄 안의 것도 그대로 센다
        self.assertEqual(seen["places"], [".side-nav"])
        check = pathlib.Path("tools/sitecheck/checks/axe.mjs").read_text(encoding="utf-8")
        self.assertIn("elementRef: true", check)                                    # 요소를 함께 받아
        self.assertIn("places.find((place) => element.closest(place))", check)      # 요소의 윗자리로 가린다

    def test_the_plan_survives_a_site_without_data(self):
        plan = self.node("import { plan } from './tools/sitecheck/plan.mjs'; console.log(JSON.stringify(plan(process.argv[1])));", str(self.site))
        self.assertIn("#home", plan["views"])
        self.assertEqual(plan["rules"], [])
        self.assertIsNone(plan["good"])

    def test_the_server_gives_files_of_the_site_and_nothing_outside_it(self):
        (self.site / "index.html").write_text("<p>첫 화면</p>", encoding="utf-8")
        self.write("x.json", {"ok": True})
        (self.site.parent / "secret.txt").write_text("밖의 파일", encoding="utf-8")
        self.addCleanup((self.site.parent / "secret.txt").unlink, missing_ok=True)
        script = ("import { serve } from './tools/sitecheck/serve.mjs'; const server = await serve(process.argv[1]); const out = [];"
                  " for (const path of ['', 'data/x.json', 'nothing.html', '%2e%2e/secret.txt', '..%2fsecret.txt']) {"
                  " const response = await fetch(server.url + path); out.push([response.status, response.headers.get('content-type'), (await response.text()).slice(0, 20)]); }"
                  " await server.close(); console.log(JSON.stringify(out));")
        got = self.node(script, str(self.site))
        self.assertEqual(got[0], [200, "text/html; charset=utf-8", "<p>첫 화면</p>"])
        self.assertEqual(got[1][:2], [200, "application/json; charset=utf-8"])
        self.assertEqual([row[0] for row in got[2:]], [404, 404, 404])
        self.assertNotIn("밖의 파일", json.dumps(got, ensure_ascii=False))


if __name__ == "__main__":
    unittest.main()
