// 만든 사이트를 브라우저로 열어 검사한다. 문제가 있으면 0이 아닌 값으로 끝난다.
// 쓰는 법: node tools/sitecheck/run.mjs <사이트 폴더> [--only layout,axe,calc,gloss] [--report 결과를 적을 파일]
//   layout  모든 화면과 규제 화면을 여러 너비로 열어 가로 넘침, 그려지지 않은 화면, 깨진 값, 화면 오류를 본다
//   axe     주요 화면에 접근성 자동 검사를 돌린다(색 변형마다, 넓은 화면과 좁은 화면)
//   calc    인증서 비용 추정 화면을 실제로 다뤄 본다
//   gloss   글 속 용어 풀이를 실제로 다뤄 본다(누르기, 자판, 닫기)
import { writeFileSync } from "node:fs";
import { launch } from "./browser.mjs";
import { axe } from "./checks/axe.mjs";
import { calc } from "./checks/calc.mjs";
import { gloss } from "./checks/gloss.mjs";
import { layout } from "./checks/layout.mjs";
import { plan } from "./plan.mjs";
import { serve } from "./serve.mjs";

const CHECKS = { layout, axe, calc, gloss };
const args = process.argv.slice(2);
const value = (name) => (args.includes(name) ? args[args.indexOf(name) + 1] : "");
const site = args.find((one, index) => !one.startsWith("--") && !["--only", "--report"].includes(args[index - 1])) || "_site";
const only = value("--only") ? value("--only").split(",") : Object.keys(CHECKS);

const started = Date.now();
const server = await serve(site);
const browser = await launch();
const results = [];
let crashed = "";
try {
  const what = plan(site);
  for (const key of only) {
    if (!CHECKS[key]) throw new Error(`모르는 검사 이름: ${key}`);
    const result = await CHECKS[key](browser, server.url, what);
    results.push(result);
    console.log(`${result.name}: ${result.checked}번 봄, 문제 ${result.failures.length}건`);
    for (const one of result.failures.slice(0, 30)) console.log(`  - ${one.where}: ${one.why}`);
  }
} catch (error) {
  crashed = String((error && error.stack) || error).slice(0, 600);
  console.log(`검사가 끝까지 돌지 못함: ${crashed}`);
} finally {
  await browser.close();
  await server.close();
}
const failures = results.flatMap((result) => result.failures);
const report = { ok: !failures.length && !crashed, seconds: Math.round((Date.now() - started) / 1000), checked: results.reduce((sum, result) => sum + result.checked, 0),
  checks: results.map((result) => ({ name: result.name, checked: result.checked, failures: result.failures.length })), failures: failures.slice(0, 60), crashed };
if (value("--report")) writeFileSync(value("--report"), JSON.stringify(report, null, 1) + "\n");
console.log(report.ok ? `화면 점검 통과: ${report.checked}번 봄(${report.seconds}초)` : `화면 점검 실패: 문제 ${failures.length}건${crashed ? ", 검사 중단" : ""}`);
process.exit(report.ok ? 0 : 1);
