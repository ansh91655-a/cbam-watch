// 인증서 비용 추정의 셈. 화면과 떨어져 있어 시험할 수 있다(tests/test_calc.py가 node로 돌린다).
// 자료(data/calc.json)는 법령의 표에서 만든 것이고, 여기에서는 법령의 식을 그대로 따른다.
//   내재배출량(톤당) = 기본값의 총배출량 × (1 + 마크업)      기본값으로 신고할 때
//                    = 넣은 값                                실제 배출량으로 신고할 때
//   무상할당 조정(톤당) = CBAM 벤치마크 × CBAM 계수 × 부문 간 보정계수
//   인증서(톤당) = 내재배출량 − 무상할당 조정 (0보다 작으면 0)

// 사이트에 실린 짧은 꼴(자리로 읽는 배열)을 이름이 붙은 꼴로 편다.
export function unpack(book) {
  const rows = (book.rows || []).map(([shown, text, origin, direct, indirect, total]) => ({ shown, text, origin, direct, indirect, total }));
  const variant = ([value, route, period]) => ({ value, route, period });
  const goods = (book.goods || []).map(([code, text, sector, a, b, defaults]) => ({
    code, text, sector, a: a.map(variant), b: b.map(variant),
    defaults: defaults.map(([row, route, ...benchmark]) => ({ row: rows[row], route, benchmark })),
  }));
  return { ...book, rows, goods };
}

// 해마다의 값 가운데 그해에 쓰는 값: 그해의 값이 없으면 그보다 앞선 가장 가까운 해의 값(법령이 '몇 년부터'라고 적은 값).
function standing(values, year) {
  const years = Object.keys(values || {}).map(Number).filter((one) => one <= year).sort((a, b) => a - b);
  return years.length ? values[String(years[years.length - 1])] : null;
}

// 기본값에 더하는 마크업(%).
export function markup(book, sector, year) {
  const group = (book.markups || []).find((one) => one.sectors.includes(sector));
  return group ? standing(group.values, year) : null;
}

// 벤치마크의 연도 구간: { index: benchmark 배열의 자리, key: 표의 표시 (1)·(2), assumed: 정해진 구간을 지난 해인지 }.
export function period(book, year) {
  const periods = book.periods || [];
  const index = periods.findIndex((one) => year >= one.from && year <= one.to);
  if (index >= 0) return { index, key: periods[index].key, assumed: false };
  const last = periods.length - 1;
  return { index: year < periods[0].from ? 0 : last, key: periods[year < periods[0].from ? 0 : last].key, assumed: true };
}

// 부문 간 보정계수(%): 정해진 해는 그 값, 정해지지 않은 해는 100으로 가정한다.
export function cscf(book, year) {
  const value = (book.cscf || {})[String(year)];
  return typeof value === "number" ? { value, assumed: false } : { value: 100, assumed: true };
}

// CBAM 계수(%): 경로에 그해의 값이 있으면 그 값, 경로의 마지막 해를 지났으면 0(무상할당이 끝난 뒤).
export function factorAt(path, year) {
  const values = (path && path.values) || {};
  if (typeof values[String(year)] === "number") return values[String(year)];
  const years = Object.keys(values).map(Number);
  if (!years.length) return null;
  return year > Math.max(...years) ? 0 : null;
}

// 합금강의 높은 등급(고합금강)의 경로. 기본값으로 신고할 때에는 기본값 행의 경로와 이 경로의 벤치마크 가운데 큰 값을 쓴다(tools/calc/build.py와 같은 규칙).
const ALLOY_HIGH = "J";

// 실제 배출량으로 신고할 때 고를 수 있는 생산경로(벤치마크 B열에 경로 표시가 있는 품목만).
export function routesOf(good) {
  return [...new Set(good.b.map((one) => one.route).filter(Boolean))];
}

// 벤치마크 표의 한 열(A열이나 B열)에서 경로와 연도 구간에 맞는 값. 표시가 없는 값 하나뿐이면 그 값이다.
export function valueAt(column, route, key) {
  for (const [wantRoute, wantKey] of [[route, key], [route, 0], ["", key], ["", 0]]) {
    const hit = (column || []).find((one) => one.route === wantRoute && one.period === wantKey);
    if (hit) return hit.value;
  }
  return null;
}

// B열에서 경로와 연도 구간에 맞는 값.
export function benchmarkAt(good, route, key) {
  return valueAt(good.b, route, key);
}

// 한 해의 추정. input: { good, choice(기본값 짝의 자리), mode("default" | "actual"), see(실제 배출량), route(실제일 때의 경로), year, tonnes, price }
// 돌려주는 값의 단위: 톤당 값은 tCO2e/t, certificates는 tCO2e(= 인증서 수), cost는 유로.
export function estimate(book, path, input) {
  const { good, mode, year } = input;
  const choice = good.defaults[input.choice || 0] || good.defaults[0];
  const span = period(book, year);
  const factor = factorAt(path, year);
  const correction = cscf(book, year);
  let embedded;
  let benchmark;
  let rate = null;
  let route = choice.route;   // 벤치마크를 고른 생산경로(경로를 가르지 않는 품목은 "")
  let routeAlt = "";          // 기본값으로 신고할 때 함께 견준 경로(합금강: 두 등급 가운데 큰 값을 쓴다)
  if (mode === "actual") {
    if (input.see === "" || input.see === null || input.see === undefined) return null; // 값을 넣기 전에는 추정하지 않는다
    embedded = Number(input.see);
    if (routesOf(good).includes(input.route)) route = input.route;
    benchmark = benchmarkAt(good, route, span.key);
  } else {
    rate = markup(book, good.sector, year);
    embedded = choice.row.total * (1 + rate / 100);
    benchmark = choice.benchmark[span.index];
    if (route && route !== ALLOY_HIGH && routesOf(good).includes(ALLOY_HIGH)) routeAlt = ALLOY_HIGH;
  }
  if (!Number.isFinite(embedded) || embedded < 0 || benchmark === null || factor === null) return null;
  const allocation = benchmark * (factor / 100) * (correction.value / 100);
  const perTonne = Math.max(0, embedded - allocation);
  const tonnes = Number(input.tonnes) || 0;
  const price = Number(input.price) || 0;
  return {
    year, mode, embedded, markup: rate, benchmark, route, routeAlt, factor, cscf: correction.value, allocation, perTonne,
    covered: Math.min(embedded, allocation),            // 무상할당 조정으로 덜어지는 몫(톤당)
    certificates: perTonne * tonnes, cost: perTonne * tonnes * price, costPerTonne: perTonne * price,
    assumed: { benchmark: span.assumed, cscf: correction.assumed, updated: year >= 2027 },
  };
}

// 여러 해의 추정(물량과 가격은 그대로 두고 해만 바꾼다).
export function series(book, path, input) {
  const rows = [];
  for (let year = book.years.from; year <= book.years.to; year += 1) rows.push(estimate(book, path, { ...input, year }));
  return rows.filter(Boolean);
}

// 품목 찾기: 코드의 앞자리나 이름의 낱말로 찾는다. 숫자만 넣으면 코드로 본다.
export function search(goods, text, limit = 8) {
  const query = String(text || "").trim().toLowerCase();
  if (!query) return [];
  const code = query.replace(/[\s.]/g, "");
  if (/^\d+$/.test(code)) return goods.filter((good) => good.code.startsWith(code.slice(0, 8))).slice(0, limit);
  const words = query.split(/\s+/);
  return goods.filter((good) => words.every((word) => good.text.toLowerCase().includes(word))).slice(0, limit);
}
