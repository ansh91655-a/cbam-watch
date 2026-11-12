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
        self.assertEqual(plan["themes"], ["", "?theme=white", "?theme=midnight"])

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
