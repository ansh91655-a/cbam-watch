// 전구물질을 넣는 칸. 전구물질마다 제품 1톤에 들어간 양을 넣고, 그 전구물질의 내재배출량과 고유 내재무상할당량은 받은 값이 있으면 넣는다.
// 비워 둔 값은 법령의 기본값으로 정한다(calc/precursor.js). 줄을 더하거나 지우면 칸들을 다시 그리고, 값을 고칠 때에는 결과만 다시 그린다.
import { period, routesOf } from "../../calc/compute.js";
import { tonnes } from "../../calc/numbers.js";
import { precursorLine } from "../../calc/precursor.js";
import { h } from "../../ui/dom.js";
import { icon } from "../../ui/icons.js";
import { field, numberInput, selectInput } from "./fields.js";
import { finder, spaced } from "./picker.js";

let serial = 0;  // 줄마다의 번호(칸의 id에 쓴다)

// 새 전구물질 줄. more로 넣어 둔 값을 줄 수 있다(되살릴 때).
export function newPrecursor(good, more = {}) {
  serial += 1;
  return { id: serial, good, choice: 0, route: "", mass: "", see: "", sefa: "", ...more };
}

// 한 줄: 품목, 들어간 양, (공정만의 값을 넣었으면) 내재배출량, 고유 내재무상할당량, 세부 품목이나 생산경로
function precursorRow(ctx, item, index) {
  const { book, state, show, draw } = ctx;
  const good = item.good;
  const base = `calc-pre-${item.id}`;
  const pair = good.defaults[item.choice] || good.defaults[0];
  // 비워 두면 쓰는 값(전구물질 1톤에 대한 값)을 칸에 흐리게 적어 둔다
  const standard = precursorLine(book, ctx.path(), { good, choice: item.choice, route: item.route, mass: 1 }, state.year);
  const set = (key) => (value) => { item[key] = value; show(); };
  const routes = good.defaults.length > 1 ? [] : routesOf(good);
  const routeName = (key) => (book.routes.find((route) => route.key === key) || { name: key }).name;
  const variety = good.defaults.length > 1
    ? field(`${base}-choice`, "세부 품목", selectInput(`${base}-choice`, good.defaults.map((one, at) => [at, one.row.text]), item.choice, (value) => { item.choice = Number(value); item.route = ""; draw(`#${base}-choice`); }))
    : routes.length ? field(`${base}-route`, "생산경로", selectInput(`${base}-route`, routes.map((key) => [key, routeName(key)]), item.route || pair.route, (value) => { item.route = value; draw(`#${base}-route`); })) : null;
  return h("li", { class: "calc-pre", "aria-label": `전구물질 ${spaced(good.code)}` }, [
    h("div", { class: "calc-pre-head" }, [
      h("p", {}, [h("span", { class: "cn-code", text: spaced(good.code) }), h("span", { class: "calc-good-text", lang: "en", text: good.text })]),
      h("button", { type: "button", class: "btn calc-pre-drop", "aria-label": `전구물질 ${spaced(good.code)} 지우기`, onclick: () => { state.precursors.splice(index, 1); draw("#calc-pre-q"); } },
        [icon("close", 14), h("span", { text: "지우기" })]),
    ]),
    h("div", { class: "calc-grid calc-pre-grid" }, [
      field(`${base}-mass`, "제품 1톤에 들어간 양(톤)", numberInput(`${base}-mass`, item.mass, set("mass"), { placeholder: "예: 1.05" })),
      state.scope === "process" ? field(`${base}-see`, "내재배출량(tCO2e/t)", numberInput(`${base}-see`, item.see, set("see"), { placeholder: standard ? `기본값 ${tonnes(standard.see.value)}` : null })) : null,
      field(`${base}-sefa`, "고유 내재무상할당량(tCO2e/t)", numberInput(`${base}-sefa`, item.sefa, set("sefa"), { placeholder: standard ? `기본 ${tonnes(standard.sefa.value)}` : null })),
      variety,
    ]),
  ]);
}

// 세부 품목이 여럿인 전구물질(백색·회색 클링커)을 더할 때 처음 골라 둘 것: 제품의 기본 벤치마크와 같은 값을 가진 것, 없으면 제품과 같은 생산경로의 것
function firstChoice(book, state, good) {
  if (good.defaults.length < 2) return 0;
  const at = period(book, state.year).index;
  const pair = state.good.defaults[state.choice] || state.good.defaults[0];
  const same = good.defaults.findIndex((one) => one.benchmark[at] === pair.benchmark[at]);
  return Math.max(0, same >= 0 ? same : good.defaults.findIndex((one) => one.route && one.route === pair.route));
}

// ctx: { book, state, path(지금 고른 CBAM 계수의 경로), show(결과만 다시 그린다), draw(칸들을 다시 그린다) }
export function precursorEditor(ctx) {
  const { book, state, draw } = ctx;
  const add = (good) => {
    const item = newPrecursor(good, { choice: firstChoice(book, state, good) });
    state.precursors.push(item);
    draw(`#calc-pre-${item.id}-mass`);
  };
  const [form, status, list] = finder(book.goods, add, { id: "calc-pre-q", label: "전구물질 더하기(CN 코드나 영문 품목 이름)", placeholder: "예: 7208 또는 clinker" });
  const blank = state.scope === "process"
    ? "비워 둔 내재배출량은 대한민국 기본값에 마크업을 더한 값으로, 비워 둔 고유 내재무상할당량은 기본 벤치마크(B열)에 CBAM 계수와 부문 간 보정계수를 곱한 값으로 계산합니다."
    : "비워 둔 고유 내재무상할당량은 기본 벤치마크(B열)에 CBAM 계수와 부문 간 보정계수를 곱한 값으로 계산합니다.";
  return [
    state.precursors.length ? h("ol", { class: "calc-pre-list" }, state.precursors.map((item, index) => precursorRow(ctx, item, index))) : null,
    h("div", { class: "calc-pre-add" }, [form, status, list]),
    h("p", { class: "count", text: `${blank} 다른 나라에서 만든 전구물질은 그 나라의 기본값과 생산경로에 맞추어 넣어 주세요.` }),
  ];
}
