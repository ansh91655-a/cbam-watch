// 규제에 딸린 그림. 규제 자료의 figure 값으로 고른다. 그림에 쓰는 자료는 그 화면을 열 때에만 읽는다.
import * as data from "../../data.js";
import { h } from "../../ui/dom.js";
import { factorChart } from "../../ui/factorchart.js";

const FIGURES = {
  "cbam-factor": {
    title: "CBAM 계수: 현행과 개정안",
    draw: async () => {
      const book = await data.factor();
      return book.paths.length ? factorChart(book) : null;
    },
  },
};

// 그림이 든 구역을 돌려준다. 그림이 없는 규제거나 자료를 읽지 못했으면 null이다.
// 화면을 그리기 전에 기다려 받는다(그림이 처음부터 화면에 있어야 들어올 때의 움직임이 붙는다).
export async function figure(rule) {
  const kind = FIGURES[rule.figure];
  if (!kind) return null;
  const node = await kind.draw();
  return node ? h("section", { class: "stack rule-figure", "aria-labelledby": "h-fig" }, [h("h2", { id: "h-fig", text: kind.title }), node]) : null;
}
