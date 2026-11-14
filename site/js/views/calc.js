// 인증서 비용 추정. 품목과 물량을 넣으면 제출할 CBAM 인증서 수와 비용을 어림해 보여 준다.
// 셈은 js/calc/compute.js가 하고, 값은 법령의 표에서 만든 data/calc.json과 CBAM 계수(data/factor.json), 인증서 가격(data/prices.json)에서 온다.
// 넣는 칸은 품목이나 신고 방법이 바뀔 때에만 다시 그리고, 값을 고칠 때에는 결과만 다시 그린다(글자를 넣는 동안 초점을 잃지 않게).
import * as data from "../data.js";
import { routesOf, unpack } from "../calc/compute.js";
import { band } from "../ui/band.js";
import { empty, fill, h } from "../ui/dom.js";
import { groupTabs } from "../ui/tabs.js";
import { notes } from "./calc/notes.js";
import { picker } from "./calc/picker.js";
import { result } from "./calc/result.js";
import { termsPanel } from "./calc/terms.js";

const MODES = [["default", "기본값으로 신고"], ["actual", "실제 배출량으로 신고"]];

// 여럿 가운데 하나를 고르는 단추 줄. 누르면 눌린 표시를 스스로 옮기고 onPick을 부른다.
// 누른 뒤에 칸들을 다시 그리는 경우에도 초점을 되찾을 수 있게, 단추마다 줄의 이름과 값을 적어 둔다(data-seg).
function seg(name, label, options, current, onPick) {
  const buttons = options.map(([key, text]) => h("button", { type: "button", text, "data-seg": `${name}:${key}`, "aria-pressed": String(key === current), onclick: () => {
    buttons.forEach((button) => button.setAttribute("aria-pressed", String(button.dataset.seg === `${name}:${key}`)));
    onPick(key);
  } }));
  return h("div", { class: "seg seg-wrap", role: "group", "aria-label": label }, buttons);
}

function field(id, label, control, hint) {
  return h("div", { class: "calc-field" }, [h("label", { class: "field", for: id }, [h("span", { text: label }), control]), hint ? h("p", { class: "count", text: hint }) : null]);
}

export async function render(main, arg) {
  const [raw, factorBook, prices] = await Promise.all([data.calc(), data.factor(), data.prices()]);
  const head = band("인증서 비용 추정", "품목과 물량을 넣으면 제출할 CBAM 인증서 수와 비용을 어림해 드립니다.", groupTabs("calc"));
  if (!raw || !Array.isArray(raw.goods) || !raw.goods.length || !factorBook.paths.length) {
    fill(main, head, empty("추정에 쓸 자료를 준비하고 있습니다."));
    return;
  }
  const book = unpack(raw);
  const asked = String(arg || "").replace(/\D/g, "");  // 주소로 받은 코드(#calc-7208). 품목 하나에 꼭 맞으면 그 품목을 고르고, 아니면 찾는 칸에 넣어 둔다
  const latest = (prices.prices || [])[prices.prices.length - 1];
  const state = {
    good: book.goods.find((good) => good.code === asked) || null,
    choice: 0, mode: "default", see: "", route: "",
    year: Math.min(Math.max(new Date().getFullYear(), book.years.from), book.years.to),
    tonnes: 100, price: latest ? latest.value : 0, path: factorBook.paths[0].key,
  };
  let typed = state.good ? "" : asked;
  const box = h("section", { class: "cn-box calc-box", "aria-label": "추정 조건" });
  const out = h("div", { class: "stack-l calc-out", "aria-live": "polite" });
  const path = () => factorBook.paths.find((one) => one.key === state.path) || factorBook.paths[0];
  const choice = () => state.good.defaults[state.choice] || state.good.defaults[0];

  function show() {
    if (!state.good) {
      fill(out, empty("품목을 고르면 추정 결과가 여기에 나옵니다."));
      return;
    }
    fill(out, ...result(book, path(), state));
  }

  function number(id, value, onChange, extra = {}) {
    const input = h("input", { id, type: "number", inputmode: "decimal", min: "0", step: "any", value: value === "" ? null : value, ...extra });
    input.addEventListener("input", () => { onChange(input.value === "" ? "" : Number(input.value)); show(); });
    return input;
  }

  // 품목을 고른 뒤에 보이는 칸들: 세부 품목, 물량·연도·가격, 신고 방법, CBAM 계수의 경로
  function conditions() {
    const good = state.good;
    const row = choice().row;
    const years = [];
    for (let year = book.years.from; year <= book.years.to; year += 1) years.push(year);
    const yearSelect = h("select", { id: "calc-year" }, years.map((year) => h("option", { value: year, selected: year === state.year, text: `${year}년` })));
    yearSelect.addEventListener("change", () => { state.year = Number(yearSelect.value); show(); });
    // 세부 품목(TARIC 코드)이 생산경로를 정하는 품목(백색·회색 클링커 등)은 경로를 따로 묻지 않는다.
    const routes = good.defaults.length > 1 ? [] : routesOf(good);
    const routeSelect = routes.length ? h("select", { id: "calc-route" }, routes.map((key) =>
      h("option", { value: key, selected: key === (state.route || choice().route), text: (book.routes.find((route) => route.key === key) || { name: key }).name }))) : null;
    if (routeSelect) routeSelect.addEventListener("change", () => { state.route = routeSelect.value; show(); });
    return [
      good.defaults.length > 1 ? h("div", { class: "calc-row" }, [
        h("p", { class: "calc-label", text: "세부 품목" }),
        seg("choice", "세부 품목", good.defaults.map((one, index) => [index, one.row.text]), state.choice, (index) => { state.choice = index; state.route = ""; draw(`[data-seg="choice:${index}"]`); }),
      ]) : null,
      h("div", { class: "calc-grid" }, [
        field("calc-tonnes", "수입 물량(톤)", number("calc-tonnes", state.tonnes, (value) => { state.tonnes = value; })),
        field("calc-year", "수입 연도", yearSelect),
        field("calc-price", "인증서 가격(유로)", number("calc-price", state.price, (value) => { state.price = value; }),
          latest ? `${latest.label} 가격 ${latest.value.toFixed(2)}유로를 넣어 두었습니다.` : null),
      ]),
      h("div", { class: "calc-row" }, [
        h("p", { class: "calc-label", text: "신고 방법" }),
        seg("mode", "신고 방법", MODES, state.mode, (mode) => { state.mode = mode; draw(mode === "actual" ? "#calc-see" : `[data-seg="mode:${mode}"]`); }),
        state.mode === "default"
          ? h("p", { class: "count", text: row.origin === "kr" ? "법령이 정한 대한민국의 기본값에 마크업을 더해 계산합니다." : "이 품목은 대한민국의 기본값이 없어, 법령이 정한 대로 '그 밖의 나라와 영역'의 기본값에 마크업을 더해 계산합니다." })
          : null,
      ]),
      state.mode === "actual" ? h("div", { class: "calc-grid" }, [
        field("calc-see", "제품 1톤당 내재배출량(tCO2e)", number("calc-see", state.see, (value) => { state.see = value; }, { placeholder: `기본값 ${row.total.toFixed(3)}` }),
          row.indirect === null ? "이 품목은 직접배출량만 넣습니다." : "직접배출량과 간접배출량을 더한 값을 넣습니다."),
        routeSelect ? field("calc-route", "생산경로", routeSelect, "무상할당 조정에 쓰는 CBAM 벤치마크가 생산경로에 따라 다릅니다.") : null,
      ]) : null,
      h("div", { class: "calc-row" }, [
        h("p", { class: "calc-label", text: "CBAM 계수" }),
        seg("path", "CBAM 계수", factorBook.paths.map((one) => [one.key, one.name]), state.path, (key) => { state.path = key; show(); }),
        h("p", { class: "count", text: "2028년부터 두 값이 달라집니다. 개정안은 심의 중인 제안입니다." }),
      ]),
    ];
  }

  // 넣는 칸을 다시 그린다. focus에 선택자를 주면 그 칸으로 초점을 옮긴다(다시 그리면서 초점이 사라지지 않게).
  function draw(focus) {
    fill(box,
      h("h2", { class: "calc-step", text: "품목과 조건" }),
      picker(book.goods, state.good, (good) => {
        typed = "";
        state.good = good;
        state.choice = 0;
        state.route = "";
        history.replaceState(null, "", good ? `#calc-${good.code}` : "#calc");
        draw(good ? "#calc-tonnes" : "#calc-q");
      }, typed),
      ...(state.good ? conditions() : []));
    show();
    const target = focus ? box.querySelector(focus) : null;
    if (target) target.focus();
  }

  fill(main, head, box, out, termsPanel(raw, true), notes(book, factorBook));
  draw();
}
