// 수입 연도에 맞는 인증서 가격을 고른다. 화면 요소를 다루지 않는다(tests/test_calc_prices.py가 node로 돌린다).
// 자료는 data/prices.json이다: prices([{ period, kind("quarter" | "week" | "range"), label, from, to, published, value }])와
// 아직 게시되지 않은 기간 upcoming([{ period, kind, label, from, to, published }]).
//
// 법령이 정한 것(이행규정 (EU) 2025/2548)
//   2026년 수입분: 수입한 분기의 가격이 적용된다(제1조(6)). 그래서 분기를 고르게 한다.
//   2027년부터:   가격을 주마다 계산하고, 인증서를 사는 때의 가격이 적용된다(제5조). 그래서 가장 최근에 게시된 가격을 넣어 두고 고쳐 쓰게 한다.

const inYear = (row, year) => String((row && row.from) || "").startsWith(`${year}-`);
const priced = (row) => typeof row.value === "number" && Number.isFinite(row.value);

// 그해의 기간들을 이른 것부터: [{ period, kind, label, from, to, published, value(게시 전이면 null) }]
export function periodsOf(book, year) {
  const found = new Map();
  for (const row of [...((book && book.upcoming) || []), ...((book && book.prices) || [])]) {
    if (!inYear(row, year)) continue;
    const period = row.period || row.from;   // 기간의 이름이 없는 줄은 시작일로 가린다
    found.set(period, { period, kind: row.kind || "", label: row.label || period, from: row.from, to: row.to || row.from, published: row.published || "", value: priced(row) ? row.value : null });
  }
  return [...found.values()].sort((a, b) => String(a.from).localeCompare(String(b.from)));
}

// 가장 최근 기간의 게시된 가격(해와 상관없이). 없으면 null
export function latestPrice(book) {
  const rows = ((book && book.prices) || []).filter(priced);
  return rows.length ? [...rows].sort((a, b) => String(a.from).localeCompare(String(b.from)))[rows.length - 1] : null;
}

// 그해의 가격을 분기로 고르는가: 그해의 기간이 있고 모두 분기일 때(2026년)
export function byQuarter(book, year) {
  const rows = periodsOf(book, year);
  return rows.length > 0 && rows.every((row) => row.kind === "quarter");
}

// 그해의 가격을 사는 때의 가격으로 보는가: 주간 가격이 시작되는 해부터(2027년부터)
export const WEEKLY_FROM = 2027;
export const atPurchase = (year) => Number(year) >= WEEKLY_FROM;

// 처음에 넣어 둘 가격. { value, period, label, from }
//   from "period": 그해의 기간 가운데 가장 최근에 게시된 가격
//   from "latest": 그해의 가격이 아직 없어, 가장 최근에 게시된 다른 해의 가격
//   from "none":   게시된 가격이 하나도 없음(value는 0)
export function suggest(book, year) {
  const mine = periodsOf(book, year).filter((row) => row.value !== null);
  if (mine.length) {
    const row = mine[mine.length - 1];
    return { value: row.value, period: row.period, label: row.label, from: "period" };
  }
  const latest = latestPrice(book);
  return latest ? { value: latest.value, period: "", label: latest.label, from: "latest" } : { value: 0, period: "", label: "", from: "none" };
}

// 고른 기간의 가격. 그해의 기간이 아니거나 아직 게시 전이면 null
export function priceOf(book, year, period) {
  const row = periodsOf(book, year).find((one) => one.period === period);
  return row && row.value !== null ? { value: row.value, label: row.label } : null;
}

// 그해의 것으로 게시된 가격의 평균(센트까지)과 개수. 가격이 없으면 null
// partial: 그해의 가격이 더 남았는지(게시 전인 기간이 있거나, 게시된 마지막 기간이 그해의 끝에 닿지 않았을 때)
// 탄소가격 차감의 기준가격을 정하는 셈이다(이행규정 (EU) 2026/2498 제7조(3)). calc/carbon.js의 referencePrice가 이 값을 쓴다
const YEAR_END = "-12-25";  // 그해의 마지막 주나 분기는 이날 뒤에 끝난다
export function yearMean(book, year) {
  const rows = periodsOf(book, year);
  const known = rows.filter((row) => row.value !== null);
  if (!known.length) return null;
  const mean = known.reduce((sum, row) => sum + row.value, 0) / known.length;
  const last = known[known.length - 1];
  const partial = rows.some((row) => row.value === null) || String(last.to) < `${year}${YEAR_END}`;
  return { year: Number(year), value: Math.round(mean * 100) / 100, count: known.length, partial, kind: rows[0].kind };
}

// 가격이 게시된 해들(이른 해부터)
export function pricedYears(book) {
  const years = new Set(((book && book.prices) || []).filter(priced).map((row) => Number(String(row.from).slice(0, 4))).filter(Boolean));
  return [...years].sort((a, b) => a - b);
}
