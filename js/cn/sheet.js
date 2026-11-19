// 품목 한 장 보기의 셈. 조회한 코드에 닿는 8자리 품목을 인증서 비용 추정의 자료에서 찾고, 품목마다의 값을 낸다.
// 셈은 비용 추정의 것(js/calc/compute.js)을 그대로 쓴다. 화면 요소를 다루지 않으므로 node로 시험한다(tests/test_sitejs.py).
import { estimate, routesOf, series, valueAt } from "../calc/compute.js";

export const LIST_LIMIT = 12; // 코드 아래의 품목을 한 번에 보여 주는 줄 수

const digits = (text) => String(text || "").replace(/\D/g, "");

// 조회한 코드 아래의 8자리 품목들. 8자리를 넘게 넣었으면 앞 8자리로 찾는다.
export function goodsUnder(goods, query) {
  const code = digits(query).slice(0, 8);
  return code.length < 4 ? [] : (goods || []).filter((good) => good.code.startsWith(code));
}

// 넣은 코드의 품목이 자료에 없을 때 가장 가까운 윗자리: 앞 6자리, 앞 4자리 차례로 보아 처음 품목이 있는 곳. 없으면 null
export function nearest(goods, query) {
  const code = digits(query).slice(0, 8);
  for (const size of [6, 4]) {
    if (code.length <= size) continue;
    const found = goodsUnder(goods, code.slice(0, size));
    if (found.length) return { code: code.slice(0, size), count: found.length };
  }
  return null;
}

// 어림에 쓰는 해: 올해. 자료가 다루는 해의 밖이면 가장 가까운 해
export function sheetYear(book, thisYear) {
  return Math.min(Math.max(Number(thisYear) || book.years.from, book.years.from), book.years.to);
}

// 품목 하나를 기본값으로 신고할 때의 제품 1톤당 값(choice: 세부 품목의 자리). 어림할 수 없으면 null
export function line(book, path, good, year, price, choice = 0) {
  const now = estimate(book, path, { good, choice, mode: "default", year, tonnes: 1, price });
  if (!now) return null;
  const pair = good.defaults[choice] || good.defaults[0];
  return { ...now, code: good.code, text: good.text, row: pair.row, value: pair.row.total, more: good.defaults.length - 1 };
}

// 해마다의 제품 1톤당 인증서와 비용(인증서 가격은 그대로 두고 해만 바꾼다)
export function yearly(book, path, good, price, choice = 0) {
  return series(book, path, { good, choice, mode: "default", tonnes: 1, price })
    .map((row) => ({ year: row.year, perTonne: row.perTonne, costPerTonne: row.costPerTonne, assumed: row.assumed.benchmark || row.assumed.cscf, updated: row.assumed.updated }));
}

// 총배출량의 기본값에 마크업을 더한 값: 법령이 적은 해마다 [{ year, rate, value, onward(그해부터 쭉 쓰는 값인지) }]
export function markedUp(book, sector, total) {
  const group = (book.markups || []).find((one) => one.sectors.includes(sector));
  const values = (group && group.values) || {};
  const years = Object.keys(values).map(Number).sort((a, b) => a - b);
  return years.map((year, index) => ({ year, rate: values[String(year)], value: total * (1 + values[String(year)] / 100), onward: index === years.length - 1 }));
}

// 생산경로마다의 CBAM 벤치마크: [{ route, name, a: [연도 구간마다의 값], b: [...] }]. 경로를 가르지 않는 품목은 route가 ""인 한 줄이다.
export function benchmarks(book, good) {
  const keys = (book.periods || []).map((one) => one.key);
  const routes = [...new Set([...routesOf(good), ...good.a.map((one) => one.route).filter(Boolean)])];
  const name = (route) => (book.routes.find((one) => one.key === route) || { name: route }).name;
  return (routes.length ? routes : [""]).map((route) => ({
    route, name: route ? name(route) : "", a: keys.map((key) => valueAt(good.a, route, key)), b: keys.map((key) => valueAt(good.b, route, key)),
  }));
}

// 연도 구간에 따라 값이 달라지는 줄이 있는지(없으면 표에 구간을 나누어 적지 않는다)
export function splitByPeriod(rows) {
  return rows.some((row) => [row.a, row.b].some((values) => values.some((value) => value !== values[0])));
}

// 조회 결과의 표시: 어느 줄을 보여 줄지 가린다(자료의 when과 같은 이름).
// entries: 조회한 코드가 닿은 부속서 I의 줄들, priced: 기본값과 벤치마크의 표에 이 코드의 품목이 있는지, sectorPriced: 그 부문이 비용 추정에 실려 있는지
export function flagsOf(entries, priced, sectorPriced) {
  return { direct: entries.some((entry) => entry.directOnly), both: entries.some((entry) => !entry.directOnly), priced: Boolean(priced), unpriced: !priced && !sectorPriced };
}

// when이 없는 줄은 늘, 있는 줄은 그 표시가 선 품목에만 보여 준다
export function shown(rows, flags) {
  return (rows || []).filter((row) => !row.when || flags[row.when]);
}

// 조회한 코드가 닿은 줄의 부문(부문별 모아 보기의 자료에서). 줄들이 여러 부문에 걸치면 첫 줄의 부문
export function sectorOf(sectors, entries) {
  const name = entries.length ? entries[0].sector : "";
  return (sectors || []).find((sector) => (sector.cn || []).includes(name)) || null;
}
