// 셈의 틀: 값의 칸을 셈 기호로 잇는다. = 뒤의 칸이 결과다.
// 식 한 줄(절의 formula)도 같은 모양으로 그린다(tokens): 풀이에 이름이 있는 말은 칸으로, 기호는 기호로.
import { h } from "../../../ui/dom.js";

const SIGNS = /(\s[=−×÷+]\s|[()])/;

export function equation(figure) {
  const terms = figure.terms || [];
  const ops = figure.ops || [];
  const result = ops.indexOf("=") + 1;
  return h("div", { class: "fig-eq" }, terms.flatMap((term, at) => [
    h("span", { class: "fig-term", "data-result": at === result && result ? "" : null }, [h("strong", { text: term.label }), term.text ? h("span", { class: "fig-text", text: term.text }) : null]),
    at < ops.length ? h("span", { class: "fig-op", text: ops[at] }) : null,
  ]));
}

// 식 한 줄을 칸과 기호로 나눈다: [["term", "고유 내재배출량"], ["op", "−"], …]
export function tokens(text) {
  return String(text || "").split(SIGNS).map((piece) => piece.trim()).filter(Boolean)
    .map((piece) => [/^[=−×÷+()]$/.test(piece) ? "op" : "term", piece]);
}

// 식 한 줄의 그림. names(풀이가 있는 말)에 든 말만 칸으로 그리고, 나머지 글은 그대로 둔다. = 앞의 말이 결과다
export function formulaLine(text, names = []) {
  const found = tokens(text);
  const equals = found.findIndex(([kind, piece]) => kind === "op" && piece === "=");
  return h("p", { class: "fig-eq fig-eq-line" }, found.map(([kind, piece], at) => {
    if (kind === "op") return h("span", { class: "fig-op", "data-paren": piece === "(" || piece === ")" ? "" : null, text: piece });
    const result = equals > 0 && at < equals;
    return h("span", { class: "fig-term", "data-result": result ? "" : null, "data-plain": names.includes(piece) || result ? null : "" }, h("strong", { text: piece }));
  }));
}
