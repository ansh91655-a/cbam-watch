// 수입 연도와 인증서 가격을 넣는 칸. 가격은 수입 연도에 맞춰 넣어 둔다(셈은 calc/prices.js).
// 2026년 수입분에는 수입한 분기의 가격이 적용되므로 분기를 고르게 하고, 2027년부터는 인증서를 사는 때의 주간 가격이 적용되므로 가장 최근에 게시된 가격을 넣어 둔다.
// 가격을 손으로 고치면 '직접 넣기'로 바뀌고, 그 뒤에는 연도를 바꿔도 넣은 가격을 건드리지 않는다.
import { atPurchase, byQuarter, periodsOf, priceOf, suggest } from "../../calc/prices.js";
import { fixed } from "../../calc/numbers.js";
import { koreanDate } from "../../ui/format.js";
import { field, numberInput, selectInput } from "./fields.js";

export const CUSTOM = "custom";

// "2026년 3분기" → "3분기". 분기가 아닌 이름은 그대로.
const short = (label) => String(label).replace(/^\d{4}년\s*/, "");

// 조건에 처음 넣어 둘 가격과 기간: { price, period }
export function startPrice(prices, year) {
  const found = suggest(prices, year);
  return { price: found.value, period: byQuarter(prices, year) ? found.period : "" };
}

// 가격 칸 아래의 도움말: 어느 가격을 넣어 두었고, 그해에는 어떤 가격이 적용되는지
export function priceHint(prices, state) {
  const year = state.year;
  if (byQuarter(prices, year)) {
    const rule = `${year}년 수입분에는 수입한 분기의 가격이 적용됩니다.`;
    const row = periodsOf(prices, year).find((one) => one.period === state.period);
    if (row && row.value !== null) return `${rule} ${row.label} 가격 ${fixed(row.value, 2)}유로를 넣었습니다.`;
    if (row) return `${rule} ${row.label} 가격은 ${row.published ? `${koreanDate(row.published)}에 게시될 예정입니다` : "아직 게시되지 않았습니다"}. 그때까지는 가격을 직접 넣어 주세요.`;
    return `${rule} 지금은 직접 넣은 값으로 계산합니다.`;
  }
  if (atPurchase(year)) {
    const rule = `${year}년 수입분에는 인증서를 사는 때의 주간 가격이 적용됩니다.`;
    if (state.period === CUSTOM) return `${rule} 지금은 직접 넣은 값으로 계산합니다.`;
    const found = suggest(prices, year);
    if (found.from === "period") return `${rule} 가장 최근에 게시된 ${found.label} 가격 ${fixed(found.value, 2)}유로를 넣어 두었습니다.`;
    if (found.from === "latest") return `${rule} 그해의 가격은 아직 게시되지 않아, 가장 최근에 게시된 ${found.label} 가격 ${fixed(found.value, 2)}유로를 넣어 두었습니다.`;
    return `${rule} 게시된 가격이 없어 가격을 직접 넣어 주세요.`;
  }
  const found = suggest(prices, year);
  if (state.period === CUSTOM || found.from === "none") return "직접 넣은 값으로 계산합니다.";
  return `가장 최근에 게시된 ${found.label} 가격 ${fixed(found.value, 2)}유로를 넣어 두었습니다.`;
}

// 분기를 고르는 칸의 항목: 게시된 분기는 가격을, 게시 전인 분기는 게시 예정일을 적는다
function quarterOptions(prices, year) {
  const rows = periodsOf(prices, year).map((row) => [row.period,
    row.value !== null ? `${short(row.label)} · ${fixed(row.value, 2)}유로` : `${short(row.label)} · ${row.published ? `${koreanDate(row.published)} 게시 예정` : "게시 전"}`]);
  return [...rows, [CUSTOM, "직접 넣기"]];
}

// ctx: { book(편 자료), state, prices(data/prices.json), show(결과만 다시 그린다), draw(칸들을 다시 그린다) }
// 돌려주는 것: 칸들(수입 연도, (분기 가격인 해이면) 수입 분기, 인증서 가격)
export function priceFields(ctx) {
  const { book, state, prices, show, draw } = ctx;
  const years = [];
  for (let year = book.years.from; year <= book.years.to; year += 1) years.push([year, `${year}년`]);
  const quarterly = byQuarter(prices, state.year);
  const options = quarterly ? quarterOptions(prices, state.year) : [];
  const picked = options.some(([key]) => key === state.period) ? state.period : CUSTOM;

  const quarter = quarterly ? selectInput("calc-quarter", options, picked, (value) => {
    state.period = value;
    const found = value === CUSTOM ? null : priceOf(prices, state.year, value);
    if (found) state.price = found.value;
    draw("#calc-quarter");
  }) : null;
  const priceField = field("calc-price", "인증서 가격(유로)", numberInput("calc-price", state.price, (value) => {
    state.price = value;
    if (state.period !== CUSTOM) {
      // 손으로 고친 가격: 기간을 '직접 넣기'로 바꾸고 도움말만 고친다(칸을 다시 그리면 글자를 넣다가 초점을 잃는다)
      state.period = CUSTOM;
      if (quarter) quarter.value = CUSTOM;
      const note = document.getElementById("calc-price-hint");
      if (note) note.textContent = priceHint(prices, state);
    }
    show();
  }), priceHint(prices, state));

  return [
    // 연도가 바뀌면 칸에 적어 둔 기본값(마크업, 벤치마크, 기준가격)과 넣어 둔 가격이 달라지므로 칸들을 다시 그린다
    field("calc-year", "수입 연도", selectInput("calc-year", years, state.year, (value) => {
      state.year = Number(value);
      if (state.period !== CUSTOM) Object.assign(state, startPrice(prices, state.year));
      draw("#calc-year");
    })),
    quarter ? field("calc-quarter", "수입 분기", quarter) : null,
    priceField,
  ];
}
