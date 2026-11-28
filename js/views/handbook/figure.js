// 해설서의 그림. 절의 글을 한눈에 보이게 한 것이고, 종류마다 그리는 모듈이 따로 있다(figures/).
// 그림에만 있는 사실은 없다: 수와 날짜는 같은 절의 글과 표에도 있다(tools/publish/handbook_figures.py).
import { h } from "../../ui/dom.js";
import { bars } from "./figures/bars.js";
import { equation } from "./figures/equation.js";
import { factor } from "./figures/factor.js";
import { flow } from "./figures/flow.js";
import { lanes } from "./figures/lanes.js";
import { matrix } from "./figures/matrix.js";
import { split } from "./figures/split.js";
import { tiles } from "./figures/tiles.js";
import { timeline } from "./figures/timeline.js";

const DRAW = { bars, equation, factor, flow, lanes, matrix, split, tiles, timeline };

// id는 그림의 이름표를 가리키는 데 쓴다(절마다 그림은 하나다)
export function figureNode(figure, id) {
  const draw = figure && DRAW[figure.kind];
  if (!draw) return null;
  return h("figure", { class: "hb-fig", "data-kind": figure.kind, "aria-labelledby": `${id}-cap` }, [
    h("figcaption", { class: "hb-fig-cap", id: `${id}-cap` }, [h("span", { class: "hb-fig-mark", text: "그림" }), h("span", { text: figure.title })]),
    draw(figure),
    figure.note ? h("p", { class: "hb-fig-note", text: figure.note }) : null,
  ]);
}
