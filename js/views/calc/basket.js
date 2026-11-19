// 여러 품목 모아 보기. 지금의 추정을 목록에 담아 두고, 담은 추정들의 인증서 수와 비용을 더해 보여 준다.
// 품목마다 따로 셈해 더한다(한 품목에서 남은 무상할당 조정이나 차감을 다른 품목에서 빼지 않는다).
import { basketRows } from "../../calc/export.js";
import { euros, fixed, pieces } from "../../calc/numbers.js";
import { csvText } from "../../ui/csv.js";
import { h, table } from "../../ui/dom.js";
import { icon } from "../../ui/icons.js";
import { saveCsv } from "../../ui/save.js";
import { spaced } from "./picker.js";

// 담은 추정을 이르는 말: 신고 방법과 넣은 것
function method(input, row) {
  if (input.mode !== "actual") return row.deduction ? "기본값, 탄소가격 차감" : "기본값";
  const more = [input.pre === "listed" && row.lines.length ? `전구물질 ${row.lines.length}개` : null, row.deduction ? "탄소가격 차감" : null].filter(Boolean);
  return ["실제 배출량", ...more].join(", ");
}

// ctx: { book, items([{ input, path }]: 담아 둔 추정들), canAdd(지금의 추정을 담을 수 있는지), onAdd(), onLoad(자리), onDrop(자리) }
export function basketPanel(ctx) {
  const { book, items, canAdd, onAdd, onLoad, onDrop } = ctx;
  const found = basketRows(book, items);
  const add = h("button", { type: "button", class: "btn calc-basket-add", disabled: !canAdd, onclick: onAdd }, [icon("check", 15), h("span", { text: "이 추정 담기" })]);
  const head = h("div", { class: "sec-head" }, [h("h2", { id: "h-calc-basket", text: "여러 품목 모아 보기" }), add]);
  if (!items.length) {
    return h("section", { class: "panel calc-basket", "aria-labelledby": "h-calc-basket" }, [
      head,
      h("p", { class: "count", text: "지금의 추정을 목록에 담아 두고 다른 품목을 이어서 추정하면, 담은 추정들의 인증서 수와 비용을 더해 볼 수 있습니다." }),
    ]);
  }
  const rows = found.lines.map(({ input, row }, index) => {
    const name = `${spaced(input.good.code)} ${input.year}년`;
    return h("tr", {}, [
      h("td", {}, h("div", { class: "calc-basket-good" }, [h("span", { class: "cn-code", text: spaced(input.good.code) }), h("span", { class: "calc-good-text", lang: "en", text: input.good.text })])),
      h("td", { text: row ? method(input, row) : "추정할 수 없음" }),
      h("td", { class: "num", text: `${input.year}년` }),
      h("td", { class: "num", text: fixed(input.tonnes || 0, 0) }),
      h("td", { class: "num", text: row ? pieces(row.certificates) : "" }),
      h("td", { class: "num", text: row ? euros(row.cost) : "" }),
      h("td", {}, h("div", { class: "calc-basket-acts" }, [
        h("button", { type: "button", class: "btn", "aria-label": `${name} 추정 불러오기`, text: "불러오기", onclick: () => onLoad(index) }),
        h("button", { type: "button", class: "btn", "aria-label": `${name} 추정 빼기`, text: "빼기", onclick: () => onDrop(index) }),
      ])),
    ]);
  });
  rows.push(h("tr", { class: "calc-basket-sum" }, [
    h("th", { scope: "row", colspan: "4", text: `합계(${items.length}개)` }),
    h("td", { class: "num", text: pieces(found.certificates) }),
    h("td", { class: "num", text: euros(found.cost) }),
    h("td", {}),
  ]));
  return h("section", { class: "panel calc-basket", "aria-labelledby": "h-calc-basket" }, [
    head,
    table(["품목", "신고 방법", { text: "수입 연도", num: true }, { text: "물량(톤)", num: true }, { text: "인증서(개)", num: true }, { text: "비용(유로)", num: true }, "다루기"], rows, "담아 둔 추정"),
    h("p", { class: "count", text: "품목마다 따로 계산해 더했습니다. 한 품목에서 무상할당 조정이나 탄소가격 차감이 남아도 다른 품목의 인증서 수에서 빼지 않습니다." }),
    h("p", {}, h("button", { type: "button", class: "btn", onclick: () => saveCsv("cbam-estimates.csv", csvText(found.rows)) }, [icon("download", 15), h("span", { text: "목록 내려받기(CSV)" })])),
  ]);
}
