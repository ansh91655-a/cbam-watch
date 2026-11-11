// 인증서 비용 추정 화면을 실제로 다뤄 본다: 품목을 찾아 고르고, 신고 방법과 연도를 바꾸고, 결과가 제대로 나오는지 본다.
// 값을 넣는 화면이라 열어 보기만 해서는 드러나지 않는 문제(초점을 잃음, 결과에 깨진 값, 좁은 화면에서 넘침)를 잡는다.
import { go, measure, open } from "../browser.mjs";
import { violations } from "./axe.mjs";

const pause = (ms) => new Promise((done) => setTimeout(done, ms));

async function press(page, text) {
  const hit = await page.evaluate((label) => {
    const node = [...document.querySelectorAll("main button")].find((one) => one.textContent.trim() === label);
    if (node) node.click();
    return Boolean(node);
  }, text);
  await pause(250);
  return hit;
}

const focused = (page) => page.evaluate(() => (document.activeElement ? document.activeElement.id || document.activeElement.tagName : ""));

async function walk(browser, base, width, failures) {
  const { page, took } = await open(browser, base, width);
  const fail = (step, why) => failures.push({ check: "calc", where: `#calc (너비 ${width}) ${step}`, why });
  await go(page, "#calc");
  took();
  if (!(await page.$("#calc-q"))) { fail("열기", "품목 찾는 칸이 없음"); await page.close(); return 1; }
  await page.type("#calc-q", "7225 30");
  await pause(250);
  const hits = await page.$$eval(".calc-hit", (nodes) => nodes.length);
  if (!hits) fail("품목 찾기", "'7225 30'으로 찾은 품목이 없음");
  else {
    await page.click(".calc-hit");
    await pause(300);
    if ((await focused(page)) !== "calc-tonnes") fail("품목 고르기", "고른 뒤에 초점이 수입 물량 칸으로 가지 않음");
    if (!(await page.$(".calc-stats"))) fail("품목 고르기", "추정 결과가 나오지 않음");
    if (!(await press(page, "실제 배출량으로 신고"))) fail("신고 방법", "'실제 배출량으로 신고' 단추가 없음");
    else {
      if ((await focused(page)) !== "calc-see") fail("신고 방법", "초점이 내재배출량 칸으로 가지 않음");
      if (await page.$(".calc-stats")) fail("신고 방법", "값을 넣기 전인데 결과가 보임");
      await page.type("#calc-see", "2.9");
      await pause(250);
      if (!(await page.$(".calc-compare"))) fail("실제 배출량", "기본값으로 신고할 때와의 비교가 나오지 않음");
    }
    await page.select("#calc-year", "2031");
    await pause(250);
    if (!(await page.$(".calc-flag"))) fail("연도", "가정한 값이 있다는 안내가 나오지 않음");
    if (!(await press(page, "개정안"))) fail("CBAM 계수", "'개정안' 단추가 없음");
    const rows = await page.$$eval(".calc-out tbody tr", (nodes) => nodes.length);
    if (rows < 5) fail("연도별 추정", `표의 행이 ${rows}개뿐임`);
    const seen = await measure(page);
    if (seen.overflow || seen.wide.length) fail("결과", `가로로 넘침(${seen.wide.join(", ") || `${seen.width}px`})`);
    if (seen.broken.length) fail("결과", `깨진 값이 찍힘(${seen.broken.join(", ")})`);
    for (const one of await violations(page)) fail("접근성", `${one.id}(${one.impact}) ${one.count}곳: ${one.at}`);
  }
  for (const error of took()) fail("화면 오류", error);
  await page.close();
  return 1;
}

export async function calc(browser, base, plan) {
  const failures = [];
  if (!plan.good) return { name: "인증서 비용 추정 다뤄 보기", checked: 0, failures: [{ check: "calc", where: "#calc", why: "추정에 쓸 품목 자료가 사이트에 없음" }] };
  let checked = 0;
  for (const width of [390, 1280]) checked += await walk(browser, base, width, failures);
  return { name: "인증서 비용 추정 다뤄 보기", checked, failures };
}
