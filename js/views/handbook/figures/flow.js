// 차례나 흐름: 칸을 화살표로 잇는다. numbered이면 칸마다 차례의 번호를 붙이고, links가 있으면 화살표에 그 말을 적는다.
// 넓은 화면에서는 가로로, 좁은 화면에서는 세로로 놓인다(css/handbook-figures.css).
import { h } from "../../../ui/dom.js";

export function flow(figure) {
  const steps = figure.steps || [];
  const links = figure.links || [];
  return h("div", { class: "fig-flow", role: "list", "data-links": links.length ? "" : null }, steps.map((step, at) => h("div", { class: "fig-step", role: "listitem" }, [
    // 앞 칸에서 이 칸으로 오는 화살표. 말이 적힌 화살표만 읽어 준다
    at ? h("span", { class: "fig-join", "aria-hidden": links[at - 1] ? null : "true" }, links[at - 1] ? h("span", { text: links[at - 1] }) : null) : null,
    h("div", { class: "fig-card" }, [
      figure.numbered ? h("span", { class: "fig-no", "aria-hidden": "true", text: at + 1 }) : null,
      h("strong", { text: step.title }),
      step.text ? h("span", { class: "fig-text", text: step.text }) : null,
      step.tag ? h("span", { class: "fig-tag", text: step.tag }) : null,
    ]),
  ])));
}
