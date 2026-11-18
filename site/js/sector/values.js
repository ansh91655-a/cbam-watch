// 부문별 모아 보기의 '기본값과 벤치마크' 표에 싣는 줄을 인증서 비용 추정의 자료(data/calc.json)에서 만든다.
// 값은 법령의 표에서 온 것 그대로이고, 여기에서는 부문의 품목을 고르고 줄로 펴기만 한다.
// 화면 요소를 다루지 않으므로 node로 시험한다(tests/test_sitejs.py).
import { defaultRoutes } from "../calc/compute.js";
import { benchmarks, markedUp } from "../cn/sheet.js";

export const PAGE = 40;   // 표에 한 번에 보여 주는 줄 수

const routeName = (book, key) => (key ? ((book.routes || []).find((one) => one.key === key) || { name: key }).name : "");

// 부문의 품목마다 한 줄(기본값 표의 줄이 둘로 갈린 품목은 두 줄):
// { code, text, shown(기본값 표의 줄에 적힌 코드), rowText, origin("kr" | "other"), direct, indirect, total, route, routeName,
//   benchmark: [연도 구간마다 기본값으로 신고할 때 쓰는 값], routes(그 품목의 생산경로 수), split(세부 품목으로 갈린 줄인지) }
export function valueRows(book, sector) {
  const rows = [];
  for (const good of book.goods || []) {
    if (good.sector !== sector) continue;
    const routes = benchmarks(book, good).filter((one) => one.route).length;
    for (const pair of good.defaults) {
      rows.push({
        code: good.code, text: good.text, shown: String(pair.row.shown).replace(/\s/g, ""), rowText: pair.row.text, origin: pair.row.origin,
        direct: pair.row.direct, indirect: pair.row.indirect, total: pair.row.total, route: pair.route, routeName: routeName(book, pair.route),
        benchmark: pair.benchmark, routes, split: good.defaults.length > 1,
      });
    }
  }
  return rows;
}

// 찾는 말로 줄을 고른다. 숫자만 넣으면 코드의 앞자리로, 글자를 넣으면 품목 이름(법령의 영문)과 생산경로 이름의 낱말로 본다.
export function filterRows(rows, text) {
  const query = String(text || "").trim().toLowerCase();
  if (!query) return rows;
  const code = query.replace(/[\s.]/g, "");
  if (/^\d+$/.test(code)) {
    // 8자리를 넘게 넣었으면 기본값 표의 줄에 적힌 코드(세부 품목)와 먼저 견주고, 맞는 줄이 없으면 앞 8자리로 찾는다
    const exact = code.length > 8 ? rows.filter((row) => row.shown.startsWith(code)) : [];
    return exact.length ? exact : rows.filter((row) => row.code.startsWith(code.slice(0, 8)) || row.shown.startsWith(code));
  }
  const words = query.split(/\s+/);
  return rows.filter((row) => words.every((word) => `${row.text} ${row.rowText} ${row.routeName}`.toLowerCase().includes(word)));
}

// 품목 하나의 생산경로마다의 벤치마크(펼친 줄에 싣는다): [{ route, name, a: [...], b: [...], used(기본값으로 신고할 때 쓰는 경로인지) }]
// pair는 기본값 표의 줄과 그 줄의 경로. 합금강은 두 경로의 값 가운데 큰 것을 쓰므로 둘 다 표시한다.
export function routeRows(book, good, pair) {
  const used = defaultRoutes(good, pair);
  return benchmarks(book, good).map((row) => ({ ...row, used: used.includes(row.route) }));
}

// 부문의 한눈에 보는 값: 품목 수, 줄 수, 기본값의 나라별 줄 수, 간접배출량의 값이 있는 줄 수, 생산경로를 가르는 품목 수, 마크업
export function summary(book, sector) {
  const rows = valueRows(book, sector);
  const group = (book.markups || []).find((one) => one.sectors.includes(sector));
  return {
    goods: new Set(rows.map((row) => row.code)).size, rows: rows.length,
    korea: rows.filter((row) => row.origin === "kr").length, other: rows.filter((row) => row.origin !== "kr").length,
    indirect: rows.filter((row) => row.indirect !== null && row.indirect !== undefined).length,
    routed: new Set(rows.filter((row) => row.routes > 1).map((row) => row.code)).size,
    markups: (group && group.values) || {},
  };
}

const cell = (value) => {
  if (value === null || value === undefined) return "";
  const text = String(value);
  return /[",\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
};

// 표를 내려받는 파일(CSV)의 글. 품목과 생산경로마다 한 줄이고, 수는 법령의 값 그대로(소수점은 마침표)다.
export function csv(book, sector) {
  const spans = (book.periods || []).map((one) => `${one.from}-${one.to}`);
  const group = (book.markups || []).find((one) => one.sectors.includes(sector));
  const years = Object.keys((group && group.values) || {}).sort();
  const head = ["cn_code", "goods", "default_row_code", "default_row", "default_origin", "direct_tco2e_per_t", "indirect_tco2e_per_t", "total_tco2e_per_t",
    ...years.map((year) => `total_with_markup_${year}`), "route", "route_name", "used_for_default_reporting",
    ...spans.map((span) => `benchmark_b_${span}`), ...spans.map((span) => `benchmark_a_${span}`)];
  const lines = [head.join(",")];
  for (const good of book.goods || []) {
    if (good.sector !== sector) continue;
    for (const pair of good.defaults) {
      const marked = markedUp(book, sector, pair.row.total);
      for (const route of routeRows(book, good, pair)) {
        lines.push([good.code, good.text, String(pair.row.shown).replace(/\s/g, ""), pair.row.text, pair.row.origin === "kr" ? "Korea, Republic of" : "Other countries and territories",
          pair.row.direct, pair.row.indirect, pair.row.total, ...years.map((year) => { const hit = marked.find((one) => String(one.year) === year); return hit ? Number(hit.value.toFixed(4)) : ""; }),
          route.route, route.name, route.route ? (route.used ? "yes" : "no") : "yes", ...route.b, ...route.a].map(cell).join(","));
      }
    }
  }
  return `${lines.join("\r\n")}\r\n`;
}
