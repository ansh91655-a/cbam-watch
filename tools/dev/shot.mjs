// 만든 사이트 폴더의 화면을 그림으로 찍는다. 고친 화면을 눈으로 확인할 때 손으로 돌린다.
// 쓰는 법: node tools/dev/shot.mjs <사이트 폴더> <찍을 곳> [...]
//   찍을 곳은 "<#화면>@<너비>[:<높이>]=<그림 파일>" 꼴이다. 높이를 주지 않으면 화면 전체를 찍는다(너무 길면 6000까지).
//   예: node tools/dev/shot.mjs _site "#news-notices@1280=/tmp/notices.png" "#news@390:900=/tmp/news-m.png"
// 화면마다 가로 넘침과 화면 오류도 함께 찍어 준다(tools/sitecheck의 도구를 쓴다).
import { go, launch, measure, open } from "../sitecheck/browser.mjs";
import { serve } from "../sitecheck/serve.mjs";

const [folder, ...targets] = process.argv.slice(2);
if (!folder || !targets.length) {
  console.error("쓰는 법: node tools/dev/shot.mjs <사이트 폴더> \"<#화면>@<너비>[:<높이>]=<그림 파일>\" ...");
  process.exit(1);
}
const site = await serve(folder);
const browser = await launch();
try {
  for (const target of targets) {
    const [where, file] = target.split("=");
    const [hash, size = "1280"] = where.split("@");
    const [width, height] = size.split(":").map(Number);
    const { page, took } = await open(browser, site.url, width);
    await go(page, hash);
    const seen = await measure(page);
    if (height) await page.setViewport({ width, height, deviceScaleFactor: 1 });
    const full = !height;
    const tall = await page.evaluate(() => document.documentElement.scrollHeight);
    await page.screenshot({ path: file, fullPage: full && tall <= 6000, ...(full && tall > 6000 ? { clip: { x: 0, y: 0, width, height: 6000 } } : {}) });
    console.log(JSON.stringify({ hash, width, file, title: seen.title, overflow: seen.overflow, wide: seen.wide, broken: seen.broken, errors: took() }));
    await page.close();
  }
} finally {
  await browser.close();
  await site.close();
}
