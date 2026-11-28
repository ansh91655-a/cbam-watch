// 넣는지 아닌지의 표: 줄마다 칸에 찬 점(넣음)이나 빈 고리(넣지 않음)를 그린다. 점의 뜻은 글로도 읽힌다.
import { h } from "../../../ui/dom.js";

const dot = (on) => h("span", { class: "fig-dot", "data-on": on ? "" : null, "aria-hidden": "true" });

export function matrix(figure) {
  const cols = figure.cols || [];
  return h("div", { class: "fig-matrix" }, [
    h("table", {}, [
      h("thead", {}, h("tr", {}, [h("td"), ...cols.map((col) => h("th", { scope: "col", text: col }))])),
      h("tbody", {}, (figure.rows || []).map((row) => h("tr", {}, [
        h("th", { scope: "row" }, [h("span", { text: row.title }), row.text ? h("small", { text: row.text }) : null]),
        ...(row.cells || []).map((cell) => h("td", {}, [dot(cell), h("span", { class: "sr", text: cell ? figure.yes : figure.no })])),
      ]))),
    ]),
    h("p", { class: "fig-key", "aria-hidden": "true" }, [dot(true), h("span", { text: figure.yes }), dot(false), h("span", { text: figure.no })]),
  ]);
}
