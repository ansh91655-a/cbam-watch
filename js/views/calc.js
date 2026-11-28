// 인증서 비용 추정. 품목과 물량을 넣으면 제출할 CBAM 인증서 수와 비용을 어림해 보여 준다.
// 셈은 js/calc/compute.js가 하고, 값은 법령의 표에서 만든 data/calc.json과 CBAM 계수(data/factor.json), 인증서 가격(data/prices.json)에서 온다.
// 넣는 칸은 품목이나 고르는 것(신고 방법, 연도, 전구물질을 넣는지 등)이 바뀔 때에만 다시 그리고, 값을 고칠 때에는 결과만 다시 그린다(글자를 넣는 동안 초점을 잃지 않게).
// 수입 연도와 인증서 가격의 칸은 calc/price.js, 실제 배출량으로 신고할 때의 칸은 calc/actual.js와 calc/precursors.js, 탄소가격 차감의 칸은 calc/carbon.js,
// 여러 품목을 모아 보는 목록은 calc/basket.js, 넣은 값과 담아 둔 추정을 남겨 두는 일은 calc/memory.js가 한다.
import * as data from "../data.js";
import { unpack } from "../calc/compute.js";
import { band } from "../ui/band.js";
import { empty, fill, h } from "../ui/dom.js";
import { groupTabs } from "../ui/tabs.js";
import { actualFields } from "./calc/actual.js";
import { basketPanel } from "./calc/basket.js";
import { carbonFields } from "./calc/carbon.js";
import { field, numberInput, row, seg } from "./calc/fields.js";
import { pack, recall, remember, restore } from "./calc/memory.js";
import { notes } from "./calc/notes.js";
import { picker } from "./calc/picker.js";
import { priceFields, startPrice } from "./calc/price.js";
import { result } from "./calc/result.js";
import { termsPanel } from "./calc/terms.js";

const MODES = [["default", "기본값으로 신고"], ["actual", "실제 배출량으로 신고"]];

export async function render(main, arg) {
  const [raw, factorBook, prices] = await Promise.all([data.calc(), data.factor(), data.prices()]);
  const head = band("인증서 비용 추정", "품목과 물량을 넣으면 제출할 CBAM 인증서 수와 비용을 어림해 드립니다. 기본값으로도, 실제 배출량과 전구물질, 제3국에서 낸 탄소가격을 넣어서도 계산합니다.", groupTabs("calc"));
  if (!raw || !Array.isArray(raw.goods) || !raw.goods.length || !factorBook.paths.length) {
    fill(main, head, empty("추정에 쓸 자료를 준비하고 있습니다."));
    return;
  }
  const book = unpack(raw);
  const asked = String(arg || "").replace(/\D/g, "");  // 주소로 받은 코드(#calc-7208). 품목 하나에 꼭 맞으면 그 품목을 고르고, 아니면 찾는 칸에 넣어 둔다
  const thisYear = Math.min(Math.max(new Date().getFullYear(), book.years.from), book.years.to);
  // 처음의 조건. 넣는 값은 빈 칸("")이거나 수다. 인증서 가격은 수입 연도에 맞는 것을 넣어 둔다(period: 고른 분기. "custom"이면 손으로 넣은 가격)
  const fresh = () => ({
    good: null, choice: 0, mode: "default",
    year: thisYear, ...startPrice(prices, thisYear),
    tonnes: 100, path: factorBook.paths[0].key,
    direct: "", indirect: "", route: "", pre: "none", scope: "whole", precursors: [],
    carbon: { how: "none", entry: "report", perTonne: "", price: "", covered: "", free: "", rate: "", other: "", dcp: "", ref: "" },
    prices,  // 기준가격을 정하는 데 쓰는 인증서 가격
  });
  // 주소에 품목이 없거나 남겨 둔 품목과 같으면 남겨 둔 조건을 되살린다. 다른 품목을 가리키면 처음의 조건에서 그 품목으로 시작한다.
  const wanted = book.goods.find((good) => good.code === asked) || null;
  const kept = recall(book, factorBook.paths);
  const saved = kept.state;
  const basket = kept.basket;  // 담아 둔 추정들(남길 수 있게 줄인 꼴)
  const state = saved && (!asked || saved.good === wanted) ? { ...fresh(), ...saved } : { ...fresh(), good: wanted };
  if (state.good && !asked) history.replaceState(null, "", `#calc-${state.good.code}`);
  let typed = state.good ? "" : asked;
  const box = h("section", { class: "cn-box calc-box", "aria-label": "추정 조건" });
  const out = h("div", { class: "stack-l calc-out" });
  // 값을 고칠 때마다 결과 전체를 읽어 주면 길므로, 화면 낭독기에는 인증서 수와 비용 한 줄만 알린다
  const said = h("p", { class: "sr", role: "status" });
  const pathOf = (key) => factorBook.paths.find((one) => one.key === key) || factorBook.paths[0];
  const path = () => pathOf(state.path);
  const pair = () => state.good.defaults[state.choice] || state.good.defaults[0];

  // 여러 품목 모아 보기: 담아 둔 추정을 조건으로 되살려 셈한다. 담기, 불러오기, 빼기를 한 뒤에는 '이 추정 담기' 단추로 초점을 돌려 둔다.
  function basketView(canAdd) {
    const again = () => { show(); const add = out.querySelector(".calc-basket-add"); if (add) add.focus(); };
    return basketPanel({
      book, canAdd,
      items: basket.map((item) => restore(item, book, factorBook.paths)).filter(Boolean).map((one) => ({ input: { ...one, prices }, path: pathOf(one.path) })),
      onAdd: () => { basket.push(pack(state)); again(); },
      onDrop: (index) => { basket.splice(index, 1); again(); },
      onLoad: (index) => {
        const found = restore(basket[index], book, factorBook.paths);
        if (!found) return;
        Object.assign(state, fresh(), found);
        typed = "";
        history.replaceState(null, "", `#calc-${state.good.code}`);
        draw("#calc-tonnes");
      },
    });
  }

  function show() {
    remember(state, basket);
    if (!state.good) {
      said.textContent = "";
      fill(out, empty("품목을 고르면 추정 결과가 여기에 나옵니다."), basket.length ? basketView(false) : null);
      return;
    }
    const found = result(book, path(), state);
    if (said.textContent !== found.said) said.textContent = found.said;
    fill(out, ...found.nodes, basketView(found.ready));
  }

  // 품목을 고른 뒤에 보이는 칸들: 세부 품목, 물량·연도·가격, 신고 방법, (실제 배출량이면) 내재배출량과 전구물질, 탄소가격 차감, CBAM 계수의 경로
  function conditions() {
    const good = state.good;
    const origin = pair().row.origin;
    const ctx = { book, state, path, prices, show, draw };
    const set = (key) => (value) => { state[key] = value; show(); };
    return [
      good.defaults.length > 1 ? row("세부 품목",
        seg("choice", "세부 품목", good.defaults.map((one, index) => [index, one.row.text]), state.choice, (index) => { state.choice = index; state.route = ""; draw(`[data-seg="choice:${index}"]`); })) : null,
      h("div", { class: "calc-grid" }, [
        field("calc-tonnes", "수입 물량(톤)", numberInput("calc-tonnes", state.tonnes, set("tonnes"))),
        ...priceFields(ctx),
      ]),
      row("신고 방법", [
        seg("mode", "신고 방법", MODES, state.mode, (mode) => {
          state.mode = mode;
          if (mode !== "actual" && state.carbon.how === "paid") state.carbon.how = "none";  // 기본값으로 신고하면 실질적으로 지불된 탄소가격은 청구할 수 없다
          draw(mode === "actual" ? "#calc-direct" : `[data-seg="mode:${mode}"]`);
        }),
        state.mode === "default"
          ? h("p", { class: "count", text: origin === "kr" ? "법령이 정한 대한민국의 기본값에 마크업을 더해 계산합니다." : "이 품목은 대한민국의 기본값이 없어, 법령이 정한 대로 '그 밖의 나라와 영역'의 기본값에 마크업을 더해 계산합니다." })
          : null,
      ]),
      ...(state.mode === "actual" ? actualFields(ctx) : []),
      carbonFields(ctx),
      row("CBAM 계수", [
        seg("path", "CBAM 계수", factorBook.paths.map((one) => [one.key, one.name]), state.path, (key) => { state.path = key; draw(`[data-seg="path:${key}"]`); }),
        h("p", { class: "count", text: "2028년부터 두 값이 달라집니다. 개정안은 심의 중인 제안입니다." }),
      ]),
      h("div", { class: "calc-foot" }, [
        h("p", { class: "count", text: "넣으신 값은 이 브라우저 탭에만 남고 서버로 보내지 않습니다." }),
        h("button", { type: "button", class: "btn calc-reset", text: "처음부터 다시", onclick: () => {
          Object.assign(state, fresh());  // 넣은 조건만 비운다. 담아 둔 추정은 그대로 둔다
          typed = "";
          history.replaceState(null, "", "#calc");
          draw("#calc-q");
        } }),
      ]),
    ];
  }

  // 넣는 칸을 다시 그린다. focus에 선택자를 주면 그 칸으로 초점을 옮긴다(다시 그리면서 초점이 사라지지 않게).
  function draw(focus) {
    fill(box,
      h("h2", { class: "calc-step", text: "품목과 조건" }),
      picker(book.goods, state.good, (good) => {
        typed = "";
        // 품목이 바뀌면 그 품목에 딸린 값(세부 품목, 생산경로, 넣은 배출량과 전구물질, 제품 1톤당 탄소가격)은 비운다. 물량, 연도, 가격은 그대로 둔다.
        const blank = fresh();
        Object.assign(state, { good, choice: 0, route: "", direct: "", indirect: "", pre: blank.pre, scope: blank.scope, precursors: [] });
        Object.assign(state.carbon, { perTonne: "", covered: "", other: "" });
        history.replaceState(null, "", good ? `#calc-${good.code}` : "#calc");
        draw(good ? "#calc-tonnes" : "#calc-q");
      }, typed),
      ...(state.good ? conditions() : []));
    show();
    const target = focus ? box.querySelector(focus) : null;
    if (target) target.focus();
  }

  fill(main, head, box, said, out, termsPanel(raw, true), notes(book, factorBook));
  draw();
}
