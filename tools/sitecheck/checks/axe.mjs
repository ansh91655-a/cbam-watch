// 접근성 자동 검사(axe-core). 주요 화면을 색 변형마다, 넓은 화면과 좁은 화면으로 본다.
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { go, open } from "../browser.mjs";
import { kept } from "./axe_rules.mjs";

const source = readFileSync(createRequire(import.meta.url).resolve("axe-core/axe.min.js"), "utf8");
const TAGS = ["wcag2a", "wcag2aa", "wcag21aa", "best-practice"];

// 지금 화면에 검사를 돌려 위반을 [{ id, impact, count, at }]로 돌려준다.
export async function violations(page) {
  await page.evaluate(source);
  const found = await page.evaluate(async (tags) => {
    const seen = await window.axe.run(document, { runOnly: { type: "tag", values: tags } });
    return seen.violations.map((one) => ({ id: one.id, impact: one.impact || "", nodes: one.nodes.map((node) => node.target.join(" ")) }));
  }, TAGS);
  return kept(found).map((one) => ({ id: one.id, impact: one.impact, count: one.nodes.length, at: one.nodes.slice(0, 2).join(" | ").slice(0, 160) }));
}

export async function axe(browser, base, plan) {
  const failures = [];
  let checked = 0;
  for (const theme of plan.themes) {
    for (const width of plan.axeWidths) {
      const { page } = await open(browser, base, width, theme);
      for (const view of plan.axeViews) {
        await go(page, view);
        for (const one of await violations(page)) {
          failures.push({ check: "axe", where: `${view} (너비 ${width}${theme ? `, ${theme.slice(1)}` : ""})`, why: `${one.id}(${one.impact}) ${one.count}곳: ${one.at}` });
        }
        checked += 1;
      }
      await page.close();
    }
  }
  return { name: "접근성", checked, failures };
}
