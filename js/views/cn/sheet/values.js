// 품목 한 장 보기의 값: 품목 하나의 기본값과 CBAM 벤치마크, 또는 코드 아래 여러 품목의 목록.
import { euros, percent, tonnes } from "../../../calc/numbers.js";
import { benchmarks, LIST_LIMIT, markedUp, splitByPeriod } from "../../../cn/sheet.js";
import { spaced } from "../../../cn/names.js";
import { h, pill, table } from "../../../ui/dom.js";

const ORIGIN = { kr: "대한민국", other: "그 밖의 나라와 영역" };
const num = (value) => (value === null || value === undefined ? h("td", { class: "num" }, [h("span", { "aria-hidden": "true", text: "–" }), h("span", { class: "sr", text: "값 없음" })]) : h("td", { class: "num", text: tonnes(value) }));

const cell = (name, value, strong) => h("div", { class: strong ? "sheet-cell-strong" : null }, [h("dt", { text: name }),
  value === null || value === undefined ? h("dd", {}, [h("span", { "aria-hidden": "true", text: "–" }), h("span", { class: "sr", text: "값 없음" })]) : h("dd", { text: tonnes(value) })]);

// 기본값 표의 줄(세부 품목) 하나: 그 줄의 이름과 생산경로 표시, 직접·간접·총배출량, 총배출량에 마크업을 더한 값(신고에 쓰는 값)
function defaultBlock(book, good, pair) {
  const route = pair.route ? (book.routes.find((one) => one.key === pair.route) || { name: pair.route }).name : "";
  const marked = markedUp(book, good.sector, pair.row.total);
  return h("div", { class: "sheet-default" }, [
    h("p", { class: "sheet-rowhead" }, [
      h("span", { class: "cn-code", text: spaced(String(pair.row.shown).replace(/\s/g, "")) }), h("span", { class: "sheet-origin", text: ORIGIN[pair.row.origin] || pair.row.origin }),
      route ? h("span", { class: "sheet-origin", text: `생산경로 표시 (${pair.route}) ${route}` }) : null,
    ]),
    h("p", { class: "sheet-rowtext", lang: "en", text: pair.row.text }),
    h("dl", { class: "sheet-cells" }, [cell("직접배출량", pair.row.direct), cell("간접배출량", pair.row.indirect), cell("총배출량", pair.row.total, true)]),
    marked.length ? h("p", { class: "sheet-sublabel", text: "총배출량에 마크업을 더한 값" }) : null,
    marked.length ? h("dl", { class: "sheet-cells" }, marked.map((one) => cell(`${one.year}년${one.onward ? "부터" : ""} ${percent(one.rate)}`, one.value, true))) : null,
  ]);
}

// 생산경로마다의 CBAM 벤치마크. used: 기본값으로 신고할 때 쓰는 경로(들)
function benchmarkTable(book, good, used) {
  const rows = benchmarks(book, good);
  const split = splitByPeriod(rows);
  const spans = (book.periods || []).map((one) => `${one.from}~${one.to}년`);
  const head = split
    ? ["생산경로", ...spans.map((span) => ({ text: `기본 벤치마크(B열) ${span}`, num: true })), ...spans.map((span) => ({ text: `공정 벤치마크(A열) ${span}`, num: true }))]
    : ["생산경로", { text: "기본 벤치마크(B열)", num: true }, { text: "공정 벤치마크(A열)", num: true }];
  const cells = (values) => (split ? values : values.slice(0, 1)).map(num);
  return table(head, rows.map((row) => h("tr", {}, [
    h("th", { scope: "row" }, [h("span", { text: row.route ? `(${row.route}) ${row.name}` : "경로를 가르지 않음" }), used.includes(row.route) && rows.length > 1 ? pill("기본값 신고에 쓰는 값", "ok") : null]),
    ...cells(row.b), ...cells(row.a),
  ])), "CBAM 벤치마크");
}

// 품목 하나의 값. now: 그 품목의 올해 값(js/cn/sheet.js의 line)
export function valuesSection(book, good, now) {
  const origins = [...new Set(good.defaults.map((pair) => pair.row.origin))];
  const directOnly = good.defaults.every((pair) => pair.row.indirect === null);
  // 세부 품목이 여럿이면 줄마다 쓰는 경로가 다르므로 표에 표시하지 않는다(줄마다 생산경로 표시를 적어 두었다)
  const used = now && good.defaults.length === 1 ? [now.route, now.routeAlt].filter(Boolean) : [];
  const usedNote = used.length > 1
    ? "기본값으로 신고할 때에는 표시한 두 생산경로의 B열 값 가운데 큰 값을 씁니다."
    : "기본값으로 신고할 때에는 B열에서 기본값 표의 줄에 적힌 생산경로의 값을 씁니다.";
  return h("section", { class: "sheet-sec sheet-values", "aria-labelledby": "h-sheet-values" }, [
    h("h3", { id: "h-sheet-values", text: "기본값과 CBAM 벤치마크" }),
    h("p", { class: "sheet-name", lang: "en", text: good.text }),
    h("div", { class: "sheet-two" }, [
      h("div", { class: "sheet-block" }, [
        h("p", { class: "sheet-label" }, [h("span", { text: "내재배출량의 기본값" }), h("small", { text: "제품 1톤당 tCO2e" })]),
        ...good.defaults.map((pair) => defaultBlock(book, good, pair)),
        h("p", { class: "count", text: [
          origins.includes("other") ? "대한민국의 기본값이 없는 줄은 법령이 정한 대로 '그 밖의 나라와 영역'의 값입니다." : "법령이 대한민국에 정한 기본값입니다.",
          "기본값으로 신고할 때에는 총배출량에 그해의 마크업을 더한 값을 씁니다.",
          directOnly ? "이 품목은 직접배출량만 넣으므로 간접배출량의 값이 없습니다." : "",
        ].filter(Boolean).join(" ") }),
      ]),
      h("div", { class: "sheet-block" }, [
        h("p", { class: "sheet-label" }, [h("span", { text: "CBAM 벤치마크" }), h("small", { text: "제품 1톤당 tCO2e" })]),
        benchmarkTable(book, good, used),
        h("p", { class: "count", text: `${usedNote} A열은 실제 배출량으로 신고할 때 그 제품을 만드는 공정의 벤치마크이며, 전구물질에 내재된 무상할당을 따로 더합니다.` }),
      ]),
    ]),
  ]);
}

// 코드 아래의 여러 품목. lines: 품목마다의 올해 값(어림할 수 없는 품목은 빠져 있다), total: 그 코드 아래의 품목 수,
// priceText: 비용에 쓴 인증서 가격을 적은 말("2026년 3분기 가격 82.32유로"). 공개된 가격이 없으면 ""이고, 그때는 비용을 적지 않는다
export function goodsSection(query, lines, total, year, priceText) {
  return h("section", { class: "sheet-sec sheet-list", "aria-labelledby": "h-sheet-values" }, [
    h("div", { class: "sheet-sec-head" }, [
      h("h3", { id: "h-sheet-values", text: `${spaced(query)} 아래의 품목 ${total}개` }),
      h("p", { class: "count", text: "8자리 코드를 누르면 그 품목의 값과 비용을 자세히 봅니다." }),
    ]),
    h("ul", { class: "sheet-goods" }, lines.slice(0, LIST_LIMIT).map((one) => h("li", {}, [
      h("a", { class: "cn-code", href: `#cn-${one.code}`, text: spaced(one.code) }),
      h("span", { class: "sheet-good-text", lang: "en", text: one.text }),
      h("dl", { class: "sheet-good-nums" }, [
        h("div", {}, [h("dt", { text: "기본값" }), h("dd", { text: tonnes(one.value) })]),
        h("div", {}, [h("dt", { text: "인증서" }), h("dd", { text: `${tonnes(one.perTonne)}개` })]),
        priceText ? h("div", {}, [h("dt", { text: "비용" }), h("dd", { text: `${euros(one.costPerTonne)}유로` })]) : null,
      ]),
    ]))),
    total > LIST_LIMIT ? h("p", { class: "count", text: `이 밖에 ${total - LIST_LIMIT}개가 더 있습니다. 코드를 더 길게 넣으면 좁혀집니다.` }) : null,
    h("p", { class: "count", text: `${year}년 수입분을 기본값으로 신고할 때의 제품 1톤당 값입니다. 기본값은 총배출량(tCO2e)이고, 인증서는 마크업과 무상할당 조정을 반영한 수입니다.${priceText ? ` 비용에는 ${priceText}를 썼습니다.` : ""}` }),
  ]);
}
