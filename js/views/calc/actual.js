// 실제 배출량으로 신고할 때 넣는 칸: 내재배출량(직접·간접)과, 무상할당 조정에 쓰는 생산경로와 전구물질.
// 전구물질을 따로 넣지 않으면 기본 벤치마크(B열)로 어림하고, 따로 넣으면 법령의 식대로 공정 벤치마크(A열)에 전구물질마다의 무상할당을 더한다.
import { benchmarkAt, period, processBenchmarkAt, routesOf } from "../../calc/compute.js";
import { tonnes } from "../../calc/numbers.js";
import { h } from "../../ui/dom.js";
import { field, group, numberInput, row, seg, selectInput } from "./fields.js";
import { precursorEditor } from "./precursors.js";

const PRE = [["none", "따로 넣지 않음"], ["listed", "따로 넣음"]];
const SCOPE = [["whole", "들어 있음(제품 전체의 값)"], ["process", "들어 있지 않음(공정만의 값)"]];
const ANNEX_II = { href: "#pdf-32025R2621.p5", text: "전력 배출계수의 기본값(부속서 II) 보기" };

// 전구물질을 따로 넣지 않을 때와 넣을 때 벤치마크가 어떻게 달라지는지: 고른 생산경로와 해의 A열·B열 값을 함께 적는다
function benchmarkNote(book, state, route) {
  const key = period(book, state.year).key;
  const a = processBenchmarkAt(state.good, route, key);
  const b = benchmarkAt(state.good, route, key);
  if (a === null || b === null) return "";
  if (a === b) return `이 품목은 공정 벤치마크(A열)와 기본 벤치마크(B열)가 같습니다(${tonnes(b)}). 전구물질이 없으면 이대로 법령의 식과 같습니다.`;
  return state.pre === "listed"
    ? `공정 벤치마크(A열 ${tonnes(a)})에 전구물질마다의 무상할당을 더합니다. 전구물질을 넣지 않으면 공정의 몫만 남습니다.`
    : `전구물질의 몫까지 넣어 둔 기본 벤치마크(B열 ${tonnes(b)})로 어림합니다. 전구물질을 따로 넣으면 법령의 식대로 공정 벤치마크(A열 ${tonnes(a)})에 전구물질마다의 무상할당을 더합니다.`;
}

// ctx: { book, state, path, show(결과만 다시 그린다), draw(칸들을 다시 그린다) }. 돌려주는 것: 칸들의 묶음 둘(내재배출량, 무상할당 조정)
export function actualFields(ctx) {
  const { book, state, show, draw } = ctx;
  const good = state.good;
  const pair = good.defaults[state.choice] || good.defaults[0];
  const counts = pair.row.indirect !== null;                      // 간접배출량도 세는 품목인지
  const listed = state.pre === "listed";
  const own = listed && state.scope === "process";                 // 넣는 값이 공정만의 값인지
  // 세부 품목(TARIC 코드)이 생산경로를 정하는 품목(백색·회색 클링커 등)은 경로를 따로 묻지 않는다.
  // 전구물질을 따로 넣으면 공정 벤치마크(A열)를 쓰므로, A열이 경로마다 다른 품목에만 경로를 묻는다(그 밖의 품목은 전구물질마다 경로를 고른다).
  const varies = (column) => column.some((one) => one.route);
  const routes = good.defaults.length > 1 || !varies(listed ? good.a : good.b) ? [] : routesOf(good);
  const route = routesOf(good).includes(state.route) ? state.route : pair.route;
  const routeName = (key) => (book.routes.find((one) => one.key === key) || { name: key }).name;
  const set = (key) => (value) => { state[key] = value; show(); };
  return [
    group("h-calc-see", "내재배출량", [
      h("div", { class: "calc-grid" }, [
        field("calc-direct", own ? "공정의 직접배출량(tCO2e/t)" : "직접배출량(tCO2e/t)", numberInput("calc-direct", state.direct, set("direct"), { placeholder: own ? null : `기본값 ${tonnes(pair.row.direct)}` }),
          own ? "이 사업장의 공정에서 나온 배출량만 넣습니다." : "제품 1톤당 값입니다. 전구물질에서 온 배출량까지 넣은 값입니다."),
        counts ? field("calc-indirect", own ? "공정의 간접배출량(tCO2e/t)" : "간접배출량(tCO2e/t)", numberInput("calc-indirect", state.indirect, set("indirect"), { placeholder: own ? null : `기본값 ${tonnes(pair.row.indirect)}` }),
          [h("span", { text: "생산공정에서 쓴 전력량에 전력의 배출계수를 곱한 값입니다. " }), h("a", ANNEX_II)]) : null,
      ]),
      counts ? null : h("p", { class: "count", text: "이 품목은 직접배출량만 셉니다." }),
    ]),
    group("h-calc-faa", "무상할당 조정", [
      routes.length ? h("div", { class: "calc-grid" }, field("calc-route", "생산경로", selectInput("calc-route", routes.map((key) => [key, routeName(key)]), route, (value) => { state.route = value; draw("#calc-route"); }),
        "CBAM 벤치마크가 생산경로에 따라 다릅니다.")) : null,
      row("전구물질", [
        seg("pre", "전구물질", PRE, state.pre, (pre) => { state.pre = pre; draw(`[data-seg="pre:${pre}"]`); }),
        h("p", { class: "count", text: benchmarkNote(book, state, route) }),
      ]),
      listed ? row("위에 넣은 배출량에 전구물질의 몫이", seg("scope", "위에 넣은 배출량에 전구물질의 몫이 들어 있는지", SCOPE, state.scope, (scope) => { state.scope = scope; draw(`[data-seg="scope:${scope}"]`); })) : null,
      ...(listed ? precursorEditor(ctx) : []),
    ]),
  ];
}
