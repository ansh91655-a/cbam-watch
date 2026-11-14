// CBAM 계수의 연도별 값. 규제 화면의 그림(ui/factorchart.js)을 그대로 쓰되, 그림이 가리키는 경로 하나만 그린다.
import * as data from "../../../data.js";
import { h } from "../../../ui/dom.js";
import { factorChart } from "../../../ui/factorchart.js";

export function factor(figure) {
  const holder = h("div", { class: "fig-factor" });
  data.factor().then((book) => {
    const paths = ((book && book.paths) || []).filter((path) => path.key === figure.path);
    if (paths.length) holder.append(factorChart({ ...book, about: "", paths }));
  }).catch(() => {});  // 그림을 그리지 못해도 같은 절의 표에 값이 있다
  return holder;
}
