// 가로 넘침과 화면 오류. 화면마다 여러 너비로 열어 본다.
import { go, measure, open } from "../browser.mjs";

function reasons(seen, errors) {
  const why = [];
  if (seen.overflow) why.push(`가로로 넘침(${seen.width}px > ${seen.vw}px${seen.wide.length ? `, ${seen.wide.join(", ")}` : ""})`);
  else if (seen.wide.length) why.push(`화면 밖으로 나간 요소(${seen.wide.join(", ")})`);
  if (!seen.title) why.push("제목이 없음(화면이 그려지지 않음)");
  if (seen.broken.length) why.push(`깨진 값이 찍힘(${seen.broken.join(", ")})`);
  return why.concat(errors);
}

async function sweep(browser, base, width, views, failures) {
  const { page, took } = await open(browser, base, width);
  took();  // 첫 화면을 여는 동안의 것은 #home을 볼 때 다시 잡힌다
  let checked = 0;
  for (const view of views) {
    await go(page, view);
    const why = reasons(await measure(page), took());
    if (why.length) failures.push({ check: "layout", where: `${view} (너비 ${width})`, why: why.join("; ") });
    checked += 1;
  }
  await page.close();
  return checked;
}

export async function layout(browser, base, plan) {
  const failures = [];
  let checked = 0;
  for (const width of plan.widths) checked += await sweep(browser, base, width, plan.views, failures);
  for (const width of plan.ruleWidths) checked += await sweep(browser, base, width, plan.rules, failures);
  return { name: "가로 넘침과 화면 오류", checked, failures };
}
