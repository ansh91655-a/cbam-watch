// 인증서 비용 추정의 자료(data/calc.json)에서 값을 고르는 일. 화면과 떨어져 있어 시험할 수 있다(tests/test_calc.py가 node로 돌린다).
// 자료는 법령의 표에서 만든 것이다: 품목마다의 기본값과 CBAM 벤치마크(A열·B열), 마크업, 부문 간 보정계수, 벤치마크의 연도 구간.

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

// 합금강의 높은 등급(고합금강)의 경로. 기본값으로 정할 때에는 기본값 행의 경로와 이 경로의 벤치마크 가운데 큰 값을 쓴다(tools/calc/build.py와 같은 규칙).
export const ALLOY_HIGH = "J";

// 고를 수 있는 생산경로(벤치마크 B열에 경로 표시가 있는 품목만).
export function routesOf(good) {
  return [...new Set(good.b.map((one) => one.route).filter(Boolean))];
}

// 기본값으로 신고할 때 벤치마크를 고르는 생산경로(들): 기본값 행의 경로와, 합금강이면 함께 견주는 고합금강의 경로(둘 가운데 큰 값을 쓴다).
// 경로를 가르지 않는 품목은 빈 배열이다.
export function defaultRoutes(good, pair) {
  const route = (pair && pair.route) || "";
  const alt = route && route !== ALLOY_HIGH && routesOf(good).includes(ALLOY_HIGH) ? ALLOY_HIGH : "";
  return [route, alt].filter(Boolean);
}

// 벤치마크 표의 한 열(A열이나 B열)에서 경로와 연도 구간에 맞는 값. 표시가 없는 값 하나뿐이면 그 값이다.
export function valueAt(column, route, key) {
  for (const [wantRoute, wantKey] of [[route, key], [route, 0], ["", key], ["", 0]]) {
    const hit = (column || []).find((one) => one.route === wantRoute && one.period === wantKey);
    if (hit) return hit.value;
  }
  return null;
}

// B열(기본 CBAM 벤치마크)에서 경로와 연도 구간에 맞는 값.
export function benchmarkAt(good, route, key) {
  return valueAt(good.b, route, key);
}

// A열(공정 관련 CBAM 벤치마크)에서 경로와 연도 구간에 맞는 값. 전구물질의 몫은 들어 있지 않다.
export function processBenchmarkAt(good, route, key) {
  return valueAt(good.a, route, key);
}

// 기본값으로 정하는 B열의 값: 기본값 행(pair)의 경로를 쓰고, 다른 경로를 고르면(다른 나라에서 만든 전구물질) 그 경로의 값을 쓴다.
// 합금강처럼 등급이 여럿이면 고합금강의 값과 견주어 큰 값이다. 돌려주는 것: { value, route, routeAlt }
export function defaultBenchmarkAt(good, pair, span, route = "") {
  const own = (pair && pair.route) || "";
  const picked = route && routesOf(good).includes(route) ? route : own;
  if (picked === own) return { value: pair.benchmark[span.index], route: own, routeAlt: defaultRoutes(good, pair)[1] || "" };
  const value = benchmarkAt(good, picked, span.key);
  const high = picked !== ALLOY_HIGH && routesOf(good).includes(ALLOY_HIGH) ? benchmarkAt(good, ALLOY_HIGH, span.key) : null;
  return { value: high === null ? value : Math.max(value, high), route: picked, routeAlt: high === null ? "" : ALLOY_HIGH };
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
