// 글 속 용어 풀이를 실제로 다뤄 본다: 글에 표시된 용어를 누르면 풀이 칸이 그 곁에 뜨고, Esc로 닫히며 초점이 용어로 돌아오는지 본다.
// 열어 보기만 해서는 드러나지 않는 문제(칸이 화면 밖으로 나감, 자판으로 닿지 않음, 닫은 뒤 초점을 잃음)를 잡는다.
import { go, open } from "../browser.mjs";
import { violations } from "./axe.mjs";

const pause = (ms) => new Promise((done) => setTimeout(done, ms));

// 풀이 칸의 상태: 보이는지, 화면 안에 있는지, 무엇이 들었는지, 초점이 어디에 있는지
const tipState = (page) => page.evaluate(() => {
  const tip = document.querySelector(".gloss-tip");
  if (!tip || tip.hidden) return { open: false, focus: document.activeElement ? document.activeElement.className : "" };
  const box = tip.getBoundingClientRect();
  return {
    open: true, inside: box.left >= 0 && box.right <= document.documentElement.clientWidth + 1, name: (tip.querySelector("#gloss-tip-name") || {}).textContent || "",
    text: (tip.querySelector(".gloss-tip-text") || {}).textContent || "", links: [...tip.querySelectorAll(".gloss-tip-links a")].map((link) => link.getAttribute("href")),
    focusInTip: tip.contains(document.activeElement), expanded: document.querySelectorAll('.gloss[aria-expanded="true"]').length,
  };
});

async function walk(browser, base, view, width, failures) {
  const { page, took } = await open(browser, base, width);
  const fail = (step, why) => failures.push({ check: "gloss", where: `${view} (너비 ${width}) ${step}`, why });
  await go(page, view);
  await pause(400);   // 표시는 화면을 그린 뒤에 붙는다
  took();
  const marked = await page.$$eval("main .gloss", (nodes) => nodes.length);
  if (!marked) { fail("열기", "글에 표시된 용어가 없음"); await page.close(); return 1; }
  // 마우스로 누르기
  await page.evaluate(() => document.querySelector("main .gloss").scrollIntoView({ block: "center" }));
  await page.click("main .gloss");
  await pause(200);
  let seen = await tipState(page);
  if (!seen.open) fail("누르기", "풀이 칸이 뜨지 않음");
  else {
    if (!seen.inside) fail("누르기", "풀이 칸이 화면의 좌우를 넘어감");
    if (!seen.name || seen.text.length < 8) fail("누르기", "풀이 칸에 용어의 이름이나 풀이가 없음");
    if (!seen.links.some((href) => String(href).startsWith("#terms-"))) fail("누르기", "용어집으로 가는 링크가 없음");
    if (seen.expanded !== 1) fail("누르기", "펼친 용어의 표시(aria-expanded)가 하나가 아님");
    for (const one of await violations(page)) fail("접근성", `${one.id}(${one.impact}) ${one.count}곳: ${one.at}`);
  }
  // Esc로 닫으면 초점이 용어로 돌아온다
  await page.keyboard.press("Escape");
  await pause(150);
  seen = await tipState(page);
  if (seen.open) fail("Esc", "풀이 칸이 닫히지 않음");
  else if (!String(seen.focus).includes("gloss")) fail("Esc", "닫은 뒤 초점이 용어로 돌아오지 않음");
  // 자판으로 열면 초점이 칸으로 가고, Tab으로 칸 안의 링크에 닿는다
  await page.keyboard.press("Enter");
  await pause(200);
  seen = await tipState(page);
  if (!seen.open || !seen.focusInTip) fail("자판", "Enter로 열었을 때 초점이 풀이 칸으로 가지 않음");
  else {
    await page.keyboard.press("Tab");
    const onLink = await page.evaluate(() => Boolean(document.activeElement && document.activeElement.closest(".gloss-tip-links")));
    if (!onLink) fail("자판", "Tab으로 풀이 칸의 링크에 닿지 않음");
  }
  // 칸 밖을 누르면 닫힌다
  await page.mouse.click(4, 4);
  await pause(150);
  if ((await tipState(page)).open) fail("밖을 누르기", "풀이 칸이 닫히지 않음");
  for (const error of took()) fail("화면 오류", error);
  await page.close();
  return 1;
}

export async function gloss(browser, base, plan) {
  const failures = [];
  let checked = 0;
  for (const view of plan.glossViews || []) {
    for (const width of [390, 1280]) checked += await walk(browser, base, view, width, failures);
  }
  return { name: "글 속 용어 풀이 다뤄 보기", checked, failures };
}
