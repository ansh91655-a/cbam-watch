// 인증서 가격. EU 집행위원회의 가격표를 프로그램이 그대로 읽어 그림과 표로 보여 준다.
// 2026년은 분기 가격, 2027년부터는 주간 가격이다. 가격이 늘어나면 기간을 골라 볼 수 있다.
import * as data from "../data.js";
import { priceChart } from "../ui/chart.js";
import { band } from "../ui/band.js";
import { empty, fill, h, safeLink, table } from "../ui/dom.js";
import { countdown, koreanDate, price, signed, today } from "../ui/format.js";

const RANGES = [["all", "전체", null], ["year", "최근 1년", 365], ["quarter", "최근 3개월", 92]];
const RANGE_FROM = 9; // 가격이 이만큼 쌓이면 기간 고르기를 보여 준다.

function within(rows, days) {
  if (!days) return rows;
  const from = new Date(Date.now() - days * 86400000).toISOString().slice(0, 10);
  const kept = rows.filter((row) => row.to >= from);
  return kept.length >= 2 ? kept : rows.slice(-2);
}

function stats(book) {
  const rows = book.prices;
  const latest = rows[rows.length - 1];
  const before = rows[rows.length - 2];
  const unit = book.unit || "유로";
  const change = before ? latest.value - before.value : null;
  const next = (book.upcoming || []).filter((row) => row.published && row.published >= today()).sort((a, b) => a.published.localeCompare(b.published))[0];
  return h("div", { class: "stats" }, [
    h("div", { class: "stat stat-hero" }, [
      h("span", { class: "stat-label", text: `${latest.label} 가격` }),
      h("span", { class: "stat-value" }, [h("span", { text: price(latest.value) }), h("small", { text: unit })]),
      h("span", { class: "stat-note", text: latest.published ? `${koreanDate(latest.published)} 게시` : "" }),
    ]),
    change === null ? null : h("div", { class: "stat" }, [
      h("span", { class: "stat-label", text: `${before.label}보다` }),
      h("span", { class: "stat-value" }, [h("span", { text: signed(change) }), h("small", { text: unit })]),
      h("span", { class: "stat-note", text: `${signed((change / before.value) * 100, 1)}%. 이 사이트가 계산한 값입니다.` }),
    ]),
    next ? h("div", { class: "stat" }, [
      h("span", { class: "stat-label", text: "다음 게시 예정" }),
      h("span", { class: "stat-value", text: countdown(next.published) }),
      h("span", { class: "stat-note", text: `${koreanDate(next.published)}, ${next.label} 가격` }),
    ]) : null,
  ]);
}

function priceTable(rows, unit) {
  const newest = [...rows].reverse();
  return table(["적용 기간", { text: "게시일", num: true }, { text: `가격(${unit})`, num: true }, { text: "직전보다", num: true }], newest.map((row, index) => {
    const before = newest[index + 1];
    return h("tr", {}, [
      h("td", {}, [h("span", { text: row.label }), row.assumed ? h("span", { class: "count", text: "기간은 표의 날짜에서 추정했습니다." }) : null]),
      h("td", { class: "num", text: row.published || "" }),
      h("td", { class: "num" }, h("strong", { text: price(row.value) })),
      h("td", { class: "num", text: before ? signed(row.value - before.value) : "" }),
    ]);
  }));
}

export async function render(main) {
  const book = await data.prices();
  const rows = book.prices || [];
  const source = book.source || {};
  const head = band("CBAM 인증서 가격", "EU 집행위원회가 게시한 가격표를 그대로 읽어 보여 줍니다. 가격표가 바뀌면 평일 아침에 따라 바뀝니다.");
  if (!rows.length) {
    fill(main, head, empty("가격표를 아직 읽지 못했습니다. 원문에서 확인하세요."), safeLink(source.url, "가격 원문 보기"));
    return;
  }
  const unit = book.unit || "유로";
  const state = { range: "all" };
  const chartHolder = h("div", {});
  const buttons = RANGES.map(([key, label]) => h("button", { type: "button", text: label, "aria-pressed": String(key === state.range), onclick: () => { state.range = key; draw(); } }));
  function draw() {
    const days = RANGES.find(([key]) => key === state.range)[2];
    buttons.forEach((button, index) => button.setAttribute("aria-pressed", String(RANGES[index][0] === state.range)));
    chartHolder.replaceChildren(priceChart(within(rows, days), unit));
  }
  const upcoming = (book.upcoming || []).filter((row) => row.published);
  fill(main,
    head,
    stats(book),
    rows.length >= RANGE_FROM ? h("div", { class: "filters" }, h("div", { class: "seg", role: "group", "aria-label": "기간" }, buttons)) : null,
    h("section", { class: "chart-card", "aria-labelledby": "h-chart" }, [
      h("h2", { id: "h-chart", text: "가격 추세" }),
      h("p", { class: "sub", text: `단위는 ${unit}. 가격은 적용 기간 동안 같은 값이어서 계단 모양으로 그렸습니다.` }),
      chartHolder,
    ]),
    h("section", { class: "stack", "aria-labelledby": "h-table" }, [
      h("h2", { id: "h-table", text: "가격표" }),
      priceTable(rows, unit),
      upcoming.length ? h("p", { class: "count", text: `게시 예정: ${upcoming.map((row) => `${row.label} 가격 ${koreanDate(row.published)}`).join(", ")}` }) : null,
    ]),
    h("section", { class: "stack", "aria-labelledby": "h-method" }, [
      h("h2", { id: "h-method", text: "가격을 정하는 방법" }),
      h("ul", { class: "note-list" }, [
        h("li", { text: "가격은 경매에 나온 EU 배출권의 경매 낙찰가격을 가중평균한 값이다." }),
        h("li", { text: "2026년에는 분기 가격을 네 번 계산해 게시하고, 2027년부터는 주간 가격을 계산해 게시한다." }),
        h("li", { text: "2026년의 분기 가격은 그 분기가 끝난 다음 첫 주에 계산하며, 그 분기에 EU로 수입된 CBAM 대상 품목의 배출량에 해당하는 CBAM 인증서 판매에 적용된다." }),
        h("li", { text: "2027년 2월부터 모든 CBAM 인증서는 공통 중앙 플랫폼에서 구매한다." }),
      ]),
      h("p", { class: "count" }, [h("span", { text: "2026년 11월 10일에 확인한 원문을 옮긴 것입니다. 바뀌었을 수 있으니 원문에서 확인하세요. " }), safeLink(source.url, source.name || "가격 원문")]),
    ]),
  );
  draw();
}
