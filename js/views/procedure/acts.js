// 입법 절차 화면의 '법령의 종류'. 규정·지침·결정의 차이, 법률과 하위 법령(위임규정, 이행규정)의 차이, 문서 번호 읽는 법을 적는다.
import { cites } from "../../procedure/parts.js";
import { h, table } from "../../ui/dom.js";
import { stackable } from "../../ui/stack.js";

export function acts(book) {
  const codes = book.codes || [];
  const rows = codes.map((one) => h("tr", {}, [h("th", { scope: "row" }, h("code", { text: one.code })), h("td", {}, [h("p", { text: one.text }), cites(book, one.basis)])]));
  return h("section", { class: "stack proc-sec", id: "pr-acts", tabindex: "-1", "aria-labelledby": "h-pr-acts" }, [
    h("div", { class: "sec-head" }, [h("h2", { id: "h-pr-acts", text: "법령의 종류" }), h("span", { class: "count", text: `${book.acts.length}가지` })]),
    h("p", { class: "sec-lead", text: "EU의 법령은 꼴에 따라 구속하는 범위가 다르고, 누가 어떤 절차로 만들었는지에 따라 법률과 하위 법령으로 나뉩니다." }),
    h("dl", { class: "act-list" }, book.acts.map((one) => h("div", { class: "act", id: `pr-acts-${one.key}`, tabindex: "-1" }, [
      h("dt", {}, [h("span", { text: one.name }), h("span", { class: "act-en", lang: "en", text: one.en })]),
      h("dd", {}, [h("p", { text: one.text }), cites(book, one.basis)]),
    ]))),
    rows.length ? h("div", { class: "stack code-guide" }, [
      h("h3", { id: "h-pr-codes", text: "문서 번호 읽는 법" }),
      stackable(table(["번호의 예", "뜻"], rows, "문서 번호 읽는 법")),
    ]) : null,
  ]);
}
