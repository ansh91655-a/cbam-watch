// 두 쪽이 하는 일과 한쪽에서 다른 쪽으로 넘겨주는 것. 넓은 화면에서는 나란히, 좁은 화면에서는 위아래로 놓인다.
import { h } from "../../../ui/dom.js";

const lane = (one) => h("div", { class: "fig-lane" }, [
  h("p", { class: "fig-lane-head" }, h("strong", { text: one.title })),
  h("ul", {}, (one.items || []).map((text) => h("li", { text }))),
]);

export function lanes(figure) {
  const [from, to] = figure.lanes || [];
  if (!from || !to) return null;
  return h("div", { class: "fig-lanes" }, [
    lane(from),
    h("p", { class: "fig-hand" }, [h("span", { class: "sr", text: `${from.title}에서 ${to.title}(으)로 넘겨주는 것: ` }), h("span", { text: figure.handover })]),
    lane(to),
  ]);
}
