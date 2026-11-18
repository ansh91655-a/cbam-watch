// 부문별 모아 보기의 '기본값과 벤치마크' 화면(#sector-<부문>.values): 그 부문 품목마다 법령이 정한 내재배출량의 기본값과 CBAM 벤치마크의 표.
// 줄은 js/sector/values.js가 비용 추정의 자료에서 만들고, 여기에서는 찾기, 더 보기, 줄 펼치기, 내려받기를 다룬다.
import { tonnes, percent } from "../../calc/numbers.js";
import { spaced } from "../../cn/names.js";
import { markedUp, splitByPeriod } from "../../cn/sheet.js";
import { markupText } from "../../sector/facts.js";
import { csv, filterRows, PAGE, routeRows, summary, valueRows } from "../../sector/values.js";
import { h, pill, table } from "../../ui/dom.js";
import { count } from "../../ui/format.js";
import { icon } from "../../ui/icons.js";
import { stackable } from "../../ui/stack.js";

const ORIGIN = { kr: "대한민국", other: "그 밖의 나라와 영역" };
const UNIT = "제품 1톤당 tCO2e";

const none = () => [h("span", { "aria-hidden": "true", text: "–" }), h("span", { class: "sr", text: "값 없음" })];
const num = (value) => h("td", { class: "num" }, value === null || value === undefined ? none() : tonnes(value));

// 펼친 줄: 마크업을 더한 값, 생산경로마다의 벤치마크, 이어 가는 곳
function detail(book, good, row, spans) {
  const pair = good.defaults.find((one) => String(one.row.shown).replace(/\s/g, "") === row.shown && one.route === row.route) || good.defaults[0];
  const marked = markedUp(book, good.sector, row.total);
  const routes = routeRows(book, good, pair);
  const split = splitByPeriod(routes);
  const head = split
    ? ["생산경로", ...spans.map((span) => ({ text: `기본 벤치마크(B열) ${span}`, num: true })), ...spans.map((span) => ({ text: `공정 벤치마크(A열) ${span}`, num: true }))]
    : ["생산경로", { text: "기본 벤치마크(B열)", num: true }, { text: "공정 벤치마크(A열)", num: true }];
  const cells = (values) => (split ? values : values.slice(0, 1)).map(num);
  const used = routes.filter((one) => one.used).length;
  return h("div", { class: "sv-detail" }, [
    h("div", { class: "sv-block" }, [
      h("p", { class: "sv-label", text: "품목" }),
      h("p", { class: "sv-fullname", lang: "en", text: good.text }),
      h("p", { class: "sv-label", text: "기본값 표의 줄" }),
      h("p", {}, [h("span", { class: "cn-code", text: spaced(row.shown) }), h("span", { class: "sv-origin", text: ORIGIN[row.origin] || row.origin })]),
      h("p", { class: "sv-rowtext", lang: "en", text: row.rowText }),
      marked.length ? h("p", { class: "sv-label", text: "총배출량에 마크업을 더한 값(기본값으로 신고할 때 쓰는 값)" }) : null,
      marked.length ? h("dl", { class: "sv-marked" }, marked.map((one) => h("div", {}, [h("dt", { text: `${one.year}년${one.onward ? "부터" : ""} ${percent(one.rate)}` }), h("dd", { text: tonnes(one.value) })]))) : null,
    ]),
    h("div", { class: "sv-block" }, [
      h("p", { class: "sv-label", text: "CBAM 벤치마크" }),
      table(head, routes.map((one) => h("tr", {}, [
        h("th", { scope: "row" }, [h("span", { text: one.route ? `(${one.route}) ${one.name}` : "경로를 가르지 않음" }), one.used && routes.length > 1 ? pill("기본값 신고에 쓰는 값", "ok") : null]),
        ...cells(one.b), ...cells(one.a),
      ])), `${spaced(good.code)}의 CBAM 벤치마크`),
      used > 1 ? h("p", { class: "count", text: "기본값으로 신고할 때에는 표시한 두 생산경로의 B열 값 가운데 큰 값을 씁니다." }) : null,
    ]),
    h("p", { class: "sv-links" }, [
      h("a", { class: "btn", href: `#cn-${good.code}` }, [icon("search", 15), h("span", { text: "품목 한 장 보기" })]),
      h("a", { class: "btn", href: `#calc-${good.code}` }, [icon("emissions", 15), h("span", { text: "이 품목으로 비용 추정" })]),
    ]),
  ]);
}

// 표의 한 줄과, 그 줄을 펼치는 단추. 펼친 줄은 처음 누를 때 만든다.
function line(book, row, index, columns, spans) {
  const good = book.goods.find((one) => one.code === row.code);
  const id = `sv-${row.code}-${index}`;
  const more = h("button", { type: "button", class: "sv-more", "aria-expanded": "false", "aria-controls": id, "aria-label": `${spaced(row.code)} 자세히 보기` }, [h("span", { text: "자세히" }), icon("next", 14)]);
  const main = h("tr", {}, [
    h("td", {}, [h("a", { class: "cn-code", href: `#cn-${row.code}`, title: "품목 한 장 보기", text: spaced(row.code) }),
      row.split ? h("span", { class: "count", text: `세부 품목 ${spaced(row.shown)}` }) : null]),
    h("td", {}, [h("span", { class: "sv-name", lang: "en", title: row.split ? row.rowText : row.text, text: row.split ? row.rowText : row.text }), row.origin !== "kr" ? pill("그 밖의 나라와 영역의 값", "warn") : null]),
    num(row.direct), columns.indirect ? num(row.indirect) : null, num(row.total),
    num(row.benchmark[0]), columns.periods ? num(row.benchmark[1]) : null,
    h("td", {}, row.route ? h("span", { text: `(${row.route}) ${row.routeName}` }) : none()),
    h("td", { class: "sv-open" }, more),
  ]);
  const extra = h("tr", { class: "sv-extra", id, hidden: "" }, h("td", { colspan: String(main.children.length) }));
  more.addEventListener("click", () => {
    const open = more.getAttribute("aria-expanded") !== "true";
    if (open && !extra.firstChild.firstChild) extra.firstChild.append(detail(book, good, row, spans));
    more.setAttribute("aria-expanded", String(open));
    extra.hidden = !open;
  });
  return [main, extra];
}

function download(book, sector) {
  const blob = new Blob([`﻿${csv(book, sector.key)}`], { type: "text/csv;charset=utf-8" });
  const link = h("a", { href: URL.createObjectURL(blob), download: `cbam-default-values-benchmarks-${sector.key}-${book.asOf || ""}.csv` });
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(link.href), 2000);
}

// 값의 표가 없는 부문(전력): 기본값이 품목이 아니라 나라마다 정해져 있다
function unpriced(sector) {
  return h("section", { class: "panel sv-none", "aria-labelledby": "h-sector-values" }, [
    h("h2", { id: "h-sector-values", text: "기본값과 CBAM 벤치마크" }),
    h("p", { text: `${sector.name}의 기본값은 품목마다가 아니라 나라마다 정해져 있습니다. 기본값 이행규정 (EU) 2025/2621의 부속서 III에 EU로 전력을 보내는 나라들의 값이 있고, 대한민국은 그 표에 없습니다. 무상할당 조정에 쓰는 CBAM 벤치마크도 이 부문에는 없습니다.` }),
    h("p", { class: "sv-links" }, [
      h("a", { class: "btn", href: "#pdf-32025R2621.p9" }, [icon("file", 15), h("span", { text: "부속서 III를 PDF로 보기" })]),
      h("a", { class: "btn", href: "#law-32025R2621" }, [icon("law", 15), h("span", { text: "기본값 이행규정을 글로 보기" })]),
    ]),
  ]);
}

// book은 비용 추정의 자료를 편 것(js/calc/compute.js의 unpack), sector는 부문별 자료의 한 부문
export function valuesView(book, sector) {
  const all = valueRows(book, sector.key);
  if (!all.length) return unpriced(sector);
  const facts = summary(book, sector.key);
  const spans = (book.periods || []).map((one) => `${one.from}~${one.to}년`);
  const short = (book.periods || []).map((one) => `${one.from}~${String(one.to).slice(2)}년`);   // 표의 머리에 적는 짧은 꼴(2026~27년)
  const columns = { indirect: facts.indirect > 0, periods: all.some((row) => row.benchmark[0] !== row.benchmark[1]) };
  const state = { text: "", shown: PAGE };

  const body = h("tbody");
  const head = ["CN 코드", "품목", { text: "직접배출 기본값", num: true }, columns.indirect ? { text: "간접배출 기본값", num: true } : null, { text: "총배출 기본값", num: true },
    { text: columns.periods ? `벤치마크 ${short[0]}` : "벤치마크", num: true }, columns.periods ? { text: `벤치마크 ${short[1]}`, num: true } : null, "생산경로", { text: "펼치기" }].filter(Boolean);
  const wrap = stackable(table(head, [], `${sector.name} 품목의 기본값과 CBAM 벤치마크`), { wideLast: true });
  wrap.querySelector("tbody").replaceWith(body);
  wrap.classList.add("sv-table");
  const tally = h("p", { class: "count sv-tally", role: "status" });
  const moreButton = h("button", { type: "button", class: "btn sv-next" });
  const allButton = h("button", { type: "button", class: "btn sv-next", text: "모두 보기" });
  const pager = h("p", { class: "sv-pager" }, [moreButton, allButton]);

  function draw() {
    const found = filterRows(all, state.text);
    const visible = found.slice(0, state.shown);
    body.replaceChildren(...visible.flatMap((row, index) => line(book, row, index, columns, spans)));
    // 좁은 화면에서 칸마다 이름을 붙인다(ui/stack.js가 하는 일을 새로 그린 줄에도 한다)
    const labels = [...wrap.querySelectorAll("thead th")].map((cell) => cell.textContent);
    for (const row of body.querySelectorAll("tr:not(.sv-extra)")) [...row.children].forEach((cell, index) => cell.setAttribute("data-label", labels[index] || ""));
    tally.textContent = state.text
      ? (found.length ? `찾은 줄 ${count(found.length)}개 가운데 ${count(visible.length)}개를 보고 있습니다.` : "찾는 품목이 없습니다. 코드의 앞자리나 품목 이름의 영문 낱말로 찾아 보세요.")
      : `모두 ${count(found.length)}줄 가운데 ${count(visible.length)}줄을 보고 있습니다.`;
    const left = found.length - visible.length;
    pager.hidden = left <= 0;
    moreButton.textContent = `${count(Math.min(PAGE, left))}줄 더 보기`;
  }
  moreButton.addEventListener("click", () => { state.shown += PAGE; draw(); });
  allButton.addEventListener("click", () => { state.shown = all.length; draw(); });

  let waiting = 0;
  const find = h("input", { id: "sv-find", type: "search", placeholder: "예: 7208, stainless, 전기로", autocomplete: "off", spellcheck: "false", oninput: (event) => {
    clearTimeout(waiting);
    waiting = setTimeout(() => { state.text = event.target.value; state.shown = PAGE; draw(); }, 160);
  } });

  const markups = markupText(facts.markups);
  const section = h("section", { class: "stack sector-sec sv", "aria-labelledby": "h-sector-values" }, [
    h("div", { class: "sec-head" }, [h("h2", { id: "h-sector-values", text: "기본값과 CBAM 벤치마크" }), h("a", { href: `#calc`, text: "인증서 비용 추정" })]),
    h("p", { class: "sector-lead", text: `${sector.name} 품목 ${count(facts.goods)}개(8자리 CN 코드)에 법령이 정한 내재배출량의 기본값과 CBAM 벤치마크입니다. 값은 모두 ${UNIT}이고 법령의 표 그대로입니다. 품목 이름은 법령의 원문대로 적었습니다.` }),
    h("dl", { class: "sector-facts sv-facts" }, [
      h("div", {}, [h("dt", { text: "기본값의 나라" }), h("dd", { text: facts.other ? `대한민국 ${count(facts.korea)}줄, 그 밖의 나라와 영역 ${count(facts.other)}줄` : "대한민국" })]),
      markups ? h("div", {}, [h("dt", { text: "기본값에 더하는 마크업" }), h("dd", { text: markups })]) : null,
      h("div", {}, [h("dt", { text: "벤치마크의 생산 연도" }), h("dd", { text: spans.join(", ") })]),
      h("div", {}, [h("dt", { text: "생산경로를 가르는 품목" }), h("dd", { text: facts.routed ? `${count(facts.routed)}개` : "없음" })]),
    ]),
    h("div", { class: "sv-tools" }, [
      h("label", { class: "field sv-find", for: "sv-find" }, [h("span", { text: "표에서 찾기" }), find]),
      tally,
      h("button", { type: "button", class: "btn sv-save", onclick: () => download(book, sector) }, [icon("download", 15), h("span", { text: "표 내려받기(CSV)" })]),
    ]),
    wrap,
    pager,
    h("div", { class: "sv-notes" }, [
      h("p", { text: "기본값은 대한민국의 값입니다. 대한민국의 값이 없는 줄은 법령이 정한 대로 '그 밖의 나라와 영역'의 값을 실었고 줄에 표시했습니다. 기본값으로 신고할 때에는 총배출 기본값에 그해의 마크업을 더한 값을 씁니다." }),
      h("p", { text: `표의 벤치마크는 기본값으로 신고할 때 쓰는 값(B열에서 기본값 표의 줄에 적힌 생산경로의 값)입니다. 줄을 펼치면 생산경로마다의 B열과 A열 값을 모두 볼 수 있습니다. A열은 실제 배출량으로 신고할 때 그 제품을 만드는 공정의 벤치마크입니다.${columns.indirect ? "" : " 이 부문은 직접배출량만 넣으므로 간접배출 기본값의 칸을 두지 않았습니다."}` }),
      columns.indirect ? h("p", {}, [h("span", { text: "간접배출량을 실제 전력 사용량으로 산정할 때 쓰는 전력 배출계수의 기본값은 나라마다 따로 정해져 있습니다(기본값 이행규정 부속서 II). " }), h("a", { href: "#pdf-32025R2621.p5", text: "부속서 II를 PDF로 보기" })]) : null,
      h("p", { class: "sv-sources" }, [
        h("span", { text: "근거: " }),
        h("a", { href: "#law-32026R1740", text: "기본값 이행규정 부속서 I(정정 규정 (EU) 2026/1740의 표)" }), h("span", { text: " · " }),
        h("a", { href: "#pdf-32026R1740.p5", text: "대한민국의 표를 PDF로 보기" }), h("span", { text: " · " }),
        h("a", { href: "#law-32025R2620", text: "무상할당 조정 이행규정 (EU) 2025/2620 부속서" }), h("span", { text: " · " }),
        h("a", { href: "#pdf-32025R2620", text: "PDF로 보기" }),
        book.asOf ? h("span", { text: ` · 자료 기준일 ${book.asOf}` }) : null,
      ]),
    ]),
  ]);
  draw();
  return section;
}
