// 브라우저를 띄우고 화면을 옮겨 다니는 공통 도구. 이미 깔려 있는 크롬을 쓴다(따로 내려받지 않는다).
import { existsSync } from "node:fs";
import puppeteer from "puppeteer-core";

const CHROME = [process.env.CHROME_PATH, "/usr/bin/google-chrome", "/usr/bin/google-chrome-stable", "/usr/bin/chromium", "/usr/bin/chromium-browser",
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"];
const QUIET_MS = 300;    // 화면이 이만큼 조용하면 다 그린 것으로 본다
const IDLE_MS = 1200;    // 아무 변화도 없을 때(같은 화면) 기다리는 시간
const LIMIT_MS = 6000;   // 계속 움직이는 화면이라도 이만큼 지나면 넘어간다

export async function launch() {
  const executablePath = CHROME.find((path) => path && existsSync(path));
  if (!executablePath) throw new Error("크롬을 찾지 못했습니다. CHROME_PATH에 실행 파일의 경로를 적어 주세요.");
  // 러너가 바쁠 때 브라우저가 제때 뜨지 않는 일이 있다(2026-11에 한 번). 화면의 문제가 아니므로 조금 쉬었다가 다시 띄워 본다.
  let failure;
  for (let attempt = 1; attempt <= 3; attempt += 1) {
    try {
      return await puppeteer.launch({ executablePath, headless: true, args: ["--no-sandbox", "--disable-gpu", "--hide-scrollbars"], timeout: 60000 });
    } catch (error) {
      failure = error;
      console.error(`브라우저 띄우기 ${attempt}번째 실패: ${String(error.message).slice(0, 160)}`);
      await new Promise((resolve) => setTimeout(resolve, 5000 * attempt));
    }
  }
  throw failure;
}

// 너비를 정한 새 탭. 움직임을 줄인 설정으로 열어, 그리는 중간 모습이 아니라 다 그린 모습을 본다.
// 돌려주는 값: { page, took(): 지난번 took() 뒤에 생긴 화면 오류들 }
export async function open(browser, base, width, query = "") {
  const page = await browser.newPage();
  const seen = [];
  page.on("pageerror", (error) => seen.push(`오류: ${String(error.message).slice(0, 160)}`));
  page.on("console", (message) => { if (message.type() === "error") seen.push(`콘솔: ${message.text().slice(0, 160)}`); });
  page.on("requestfailed", (request) => {
    // PDF 보기는 파일을 받다가 스스로 끊고 필요한 만큼만 다시 받는다. 그렇게 끊긴 것은 문제가 아니다
    const cut = (request.failure() || {}).errorText === "net::ERR_ABORTED" && /\.pdf$/i.test(new URL(request.url()).pathname);
    if (request.url().startsWith(base) && !cut) seen.push(`받지 못함: ${request.url().slice(base.length)}`);
  });
  page.on("response", (response) => { if (response.url().startsWith(base) && response.status() >= 400) seen.push(`${response.status()}: ${response.url().slice(base.length)}`); });
  await page.emulateMediaFeatures([{ name: "prefers-reduced-motion", value: "reduce" }]);
  await page.setViewport({ width, height: 900, deviceScaleFactor: 1 });
  await page.goto(`${base}${query}#home`, { waitUntil: "networkidle2", timeout: 60000 });
  return { page, took: () => seen.splice(0) };
}

// 주소의 #화면으로 옮기고, 화면이 조용해질 때까지 기다린다.
export async function go(page, hash) {
  await page.evaluate((target, quiet, idle, limit) => new Promise((done) => {
    const main = document.getElementById("main");
    let timer = null;
    let over = false;
    const finish = () => { if (over) return; over = true; observer.disconnect(); clearTimeout(timer); done(); };
    const observer = new MutationObserver(() => { clearTimeout(timer); timer = setTimeout(finish, quiet); });
    observer.observe(main, { childList: true, subtree: true, characterData: true });
    timer = setTimeout(finish, idle);
    setTimeout(finish, limit);
    if (location.hash !== target) location.hash = target;
  }), hash, QUIET_MS, IDLE_MS, LIMIT_MS);
  await page.evaluate(() => document.fonts.ready.then(() => true));
}

// 화면의 꼴: 가로로 넘쳤는지, 화면 밖으로 나간 요소, 제목, 본문에 찍힌 깨진 값.
// 화면 밖으로 나간 요소는 글이 든 것만 센다. 꾸밈 그림은 일부러 화면 밖까지 깔고 잘라 내기도 하지만(첫 화면의 지도),
// 글이 화면 밖으로 나가면 잘려서 읽을 수 없다. 옆으로 밀어 보는 칸(표, 탭) 안의 것은 넘친 것이 아니다.
export function measure(page) {
  return page.evaluate(() => {
    const vw = window.innerWidth;
    const wide = [];
    const hasText = (node) => [...node.childNodes].some((child) => child.nodeType === 3 && child.textContent.trim());
    for (const node of document.querySelectorAll("main *, header *, footer *")) {
      if (!hasText(node) || node.closest("[aria-hidden='true'], svg")) continue;
      const box = node.getBoundingClientRect();
      if (!box.width || !box.height || box.right <= vw + 1) continue;
      let scrolls = false;
      for (let up = node.parentElement; up && up !== document.body; up = up.parentElement) {
        if (/(auto|scroll)/.test(getComputedStyle(up).overflowX)) { scrolls = true; break; }
      }
      if (!scrolls) wide.push(`${node.tagName.toLowerCase()}${node.className && typeof node.className === "string" ? "." + node.className.split(" ")[0] : ""}`);
    }
    const main = document.getElementById("main");
    const text = main ? main.innerText : "";
    return {
      overflow: document.documentElement.scrollWidth > vw + 1,
      width: document.documentElement.scrollWidth, vw,
      wide: [...new Set(wide)].slice(0, 4),
      title: ((main && main.querySelector("h1")) || {}).textContent || "",
      broken: (text.match(/\b(undefined|NaN)\b|\[object Object\]/g) || []).slice(0, 3),
    };
  });
}
