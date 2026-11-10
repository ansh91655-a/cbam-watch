// 원문 화면의 제목 부분을 찍는다(kind가 "page"인 것만).
// 쓰는 법: node tools/thumbs/shots.mjs <할 일 파일> <그림을 둘 폴더>   결과는 <폴더>/pages.json에 쓴다.
// 화면에 떠 있는 것(쿠키 안내, 붙박이 머리글)과 그림을 치운 뒤 제목(h1)부터 아래로 찍는다. 기관 로고가 있는 머리 부분은 그림에 들어가지 않는다.
import fs from "node:fs";
import puppeteer from "puppeteer-core";

const [, , todoPath, outDir] = process.argv;
const jobs = JSON.parse(fs.readFileSync(todoPath, "utf8")).filter((job) => job.kind === "page");
const CHROME = process.env.CHROME_BIN || ["/usr/bin/google-chrome", "/usr/bin/google-chrome-stable", "/usr/bin/chromium-browser", "/usr/bin/chromium"].find((path) => fs.existsSync(path));
const VIEW = { width: 480, height: 1200, deviceScaleFactor: 2 }; // 좁은 화면으로 열어 글자가 그림에서 크게 보이게 한다
const CLIP = { width: 480, height: 300 };
const AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36";
const ROBOT = /captcha|automated scraping|flagged as potentially automated|unusual traffic|enable javascript and cookies/i; // 본문에 이런 말이 있으면 막힌 화면이다
const REFUSED = /access denied|forbidden|not found|just a moment|are you a robot|verify you are|error \d{3}|request blocked/i;

// 화면 안에서 돈다: 떠 있는 것과 그림을 치우고 제목의 자리를 돌려준다.
// 그림(사진, 삽화, 동영상)은 누구의 것인지 화면만으로는 알 수 없으므로 싣지 않는다. 미리보기에는 글만 남는다.
function prepare() {
  for (const node of document.querySelectorAll("body *")) {
    const position = getComputedStyle(node).position;
    if (position === "fixed" || position === "sticky") node.style.setProperty("display", "none", "important");
  }
  for (const node of document.querySelectorAll("img, picture, video, iframe, figure, canvas, svg, object, embed")) {
    node.style.setProperty("display", "none", "important");
  }
  const shown = (list) => [...document.querySelectorAll(list)].filter((node) => node.getBoundingClientRect().height > 0 && node.textContent.trim().length >= 2);
  let heads = shown("main h1, article h1, [role=main] h1, #content h1, h1");
  if (!heads.length) heads = shown("main h2, article h2, [role=main] h2, h2"); // 큰 제목이 없는 화면은 그다음 제목부터
  if (!heads.length) return null;
  const words = document.body.innerText.slice(0, 3000);
  const top = heads[0].getBoundingClientRect().top;
  // 제목보다 위에 있는 것(머리글, 경로 표시, 작은 머리말)은 보이지 않게 한다. 자리는 그대로 두어 제목이 움직이지 않는다.
  for (const node of document.querySelectorAll("body *")) {
    const box = node.getBoundingClientRect();
    if (box.height > 0 && box.bottom <= top + 1) node.style.setProperty("visibility", "hidden", "important");
  }
  return { top: top + window.scrollY, text: heads[0].textContent.trim().replace(/\s+/g, " ").slice(0, 140), words };
}

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function shoot(browser, job) {
  const page = await browser.newPage();
  try {
    await page.setViewport(VIEW);
    await page.setUserAgent(AGENT);
    const response = await page.goto(job.url, { waitUntil: "networkidle2", timeout: 45000 });
    const status = response ? response.status() : 0;
    await sleep(900);
    const found = await page.evaluate(prepare);
    if (status >= 400 || status === 202) return { name: job.name, ok: false, why: `응답 ${status}` };
    if (!found) return { name: job.name, ok: false, why: "제목을 찾지 못함" };
    if (REFUSED.test(found.text) || ROBOT.test(found.words)) return { name: job.name, ok: false, why: `막힌 화면: ${found.text.slice(0, 60)}` };
    await page.screenshot({ path: `${outDir}/${job.name}.png`, clip: { x: 0, y: Math.max(0, found.top - 14), ...CLIP } });
    return { name: job.name, ok: true, title: found.text };
  } catch (error) {
    return { name: job.name, ok: false, why: String(error).slice(0, 160) };
  } finally {
    await page.close();
  }
}

fs.mkdirSync(outDir, { recursive: true });
const results = [];
if (jobs.length) {
  const browser = await puppeteer.launch({ executablePath: CHROME, headless: "new", args: ["--no-sandbox", "--disable-gpu", "--disable-blink-features=AutomationControlled", "--lang=en-GB"] });
  for (const job of jobs) {
    const result = await shoot(browser, job);
    results.push(result);
    console.log(result.ok ? "찍음" : "실패", job.url, result.ok ? "" : result.why);
  }
  await browser.close();
}
fs.writeFileSync(`${outDir}/pages.json`, JSON.stringify(results, null, 1));
