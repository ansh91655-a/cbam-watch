// 넣은 조건과 담아 둔 추정을 이 탭에 남겨 두었다가(sessionStorage) 화면을 다시 열 때 되살린다. 다른 화면을 보고 돌아와도 넣은 값이 남아 있게 한다.
// 값은 이 브라우저 탭에만 남고 서버로 가지 않는다. 남기지 못하거나 읽지 못해도 추정은 그대로 된다.
import { newPrecursor } from "./precursors.js";

const KEY = "cbam-calc";
const VERSION = 2;
const CARBON = ["perTonne", "price", "covered", "free", "rate", "other", "dcp", "ref"];
const PERIOD = /^(custom|\d{4}-Q[1-4]|\d{4}-\d\d-\d\d)?$/;  // 고른 가격의 기간: 손으로 넣음, 분기, 주(시작일), 또는 빈 글(넣어 둔 가격 그대로)

// 수를 넣는 칸의 값: 0 이상의 수이거나 빈 칸("")
const number = (value) => (typeof value === "number" && Number.isFinite(value) && value >= 0 ? value : "");
const oneOf = (value, allowed, fallback) => (allowed.includes(value) ? value : fallback);

// 조건을 남길 수 있는 꼴로 줄인다: 품목은 코드로 적고, 가격 자료처럼 화면이 붙이는 것은 뺀다.
export function pack(state) {
  return {
    code: state.good ? state.good.code : "", choice: state.choice, mode: state.mode, year: state.year, tonnes: state.tonnes, price: state.price, period: state.period, path: state.path,
    direct: state.direct, indirect: state.indirect, route: state.route, pre: state.pre, scope: state.scope,
    precursors: state.precursors.map((item) => ({ code: item.good.code, choice: item.choice, route: item.route, mass: item.mass, see: item.see, sefa: item.sefa })),
    carbon: { how: state.carbon.how, entry: state.carbon.entry, ...Object.fromEntries(CARBON.map((key) => [key, state.carbon[key]])) },
  };
}

// 남긴 꼴을 조건으로 되돌린다. 품목이 지금의 자료에 없으면 null. 값은 하나씩 꼴을 확인해, 깨진 값은 빈 칸이나 처음 값으로 둔다.
// book: 편 자료(calc/compute.js의 unpack), paths: CBAM 계수의 경로들
export function restore(saved, book, paths) {
  const find = (code) => book.goods.find((one) => one.code === code) || null;
  const good = saved && typeof saved === "object" ? find(saved.code) : null;
  if (!good) return null;
  const within = (value, length) => (Number.isInteger(value) && value >= 0 && value < length ? value : 0);
  const routes = (book.routes || []).map((route) => route.key);
  const carbon = saved.carbon || {};
  return {
    good, choice: within(saved.choice, good.defaults.length), mode: oneOf(saved.mode, ["default", "actual"], "default"),
    year: Number.isInteger(saved.year) && saved.year >= book.years.from && saved.year <= book.years.to ? saved.year : book.years.from,
    tonnes: number(saved.tonnes), price: number(saved.price), path: oneOf(saved.path, paths.map((one) => one.key), paths[0].key),
    // 기간을 적어 두지 않은 옛 기록의 가격은 손으로 넣은 것으로 본다(연도를 바꿔도 덮어쓰지 않게)
    period: typeof saved.period === "string" && PERIOD.test(saved.period) ? saved.period : "custom",
    direct: number(saved.direct), indirect: number(saved.indirect), route: oneOf(saved.route, routes, ""),
    pre: oneOf(saved.pre, ["none", "listed"], "none"), scope: oneOf(saved.scope, ["whole", "process"], "whole"),
    precursors: (Array.isArray(saved.precursors) ? saved.precursors : []).map((item) => {
      const found = item && find(item.code);
      return found ? newPrecursor(found, { choice: within(item.choice, found.defaults.length), route: oneOf(item.route, routes, ""), mass: number(item.mass), see: number(item.see), sefa: number(item.sefa) }) : null;
    }).filter(Boolean),
    carbon: { how: oneOf(carbon.how, ["none", "paid", "default"], "none"), entry: oneOf(carbon.entry, ["report", "build"], "report"), ...Object.fromEntries(CARBON.map((key) => [key, number(carbon[key])])) },
  };
}

// state: 지금 넣은 조건, basket: 담아 둔 추정들(pack으로 줄인 꼴)
export function remember(state, basket) {
  try { sessionStorage.setItem(KEY, JSON.stringify({ v: VERSION, now: pack(state), basket })); } catch (error) { /* 남기지 못해도 추정은 된다 */ }
}

// 남겨 둔 것: { state(되살린 조건, 없으면 null), basket(담아 둔 추정들 가운데 지금의 자료로 되살릴 수 있는 것) }
export function recall(book, paths) {
  let saved = null;
  try { saved = JSON.parse(sessionStorage.getItem(KEY) || "null"); } catch (error) { saved = null; }
  if (!saved || saved.v !== VERSION) return { state: null, basket: [] };
  return { state: restore(saved.now, book, paths), basket: (Array.isArray(saved.basket) ? saved.basket : []).filter((item) => restore(item, book, paths)) };
}
