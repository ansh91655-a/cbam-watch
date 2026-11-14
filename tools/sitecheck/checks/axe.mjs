// 접근성 자동 검사(axe-core). 주요 화면을 색 변형마다, 넓은 화면과 좁은 화면으로 본다.
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { go, open } from "../browser.mjs";
import { kept, PLACES } from "./axe_rules.mjs";

const source = readFileSync(createRequire(import.meta.url).resolve("axe-core/axe.min.js"), "utf8");
const TAGS = ["wcag2a", "wcag2aa", "wcag21aa", "best-practice"];

// 지금 화면에 검사를 돌려 위반을 [{ id, impact, count, at }]로 돌려준다.
// 위반이 난 요소가 어느 자리 안에 있는지는 요소로 본다(elementRef로 요소를 함께 받는다). 이 사이트에서는 위반이 아닌 것을 그 자리로 가려낸다(axe_rules.mjs).
export async function violations(page) {
  await page.evaluate(source);
  const found = await page.evaluate(async ({ tags, places }) => {
    const seen = await window.axe.run(document, { runOnly: { type: "tag", values: tags }, elementRef: true });
    const placeOf = (element) => (element instanceof Element && places.find((place) => element.closest(place))) || "";
    return seen.violations.map((one) => ({ id: one.id, impact: one.impact || "", nodes: one.nodes.map((node) => ({ at: node.target.join(" "), place: placeOf(node.element) })) }));
  }, { tags: TAGS, places: PLACES });
  return kept(found).map((one) => ({ id: one.id, impact: one.impact, count: one.nodes.length, at: one.nodes.slice(0, 2).map((node) => node.at).join(" | ").slice(0, 160) }));
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
