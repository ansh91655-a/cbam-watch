// 칸의 묶음: 아이콘과 이름, 한 줄 설명. href가 있으면 칸 전체가 그 화면으로 가는 링크다.
import { h } from "../../../ui/dom.js";
import { icon } from "../../../ui/icons.js";

export function tiles(figure) {
  const items = figure.items || [];
  // 넓은 자리에서 한 줄에 셋씩 놓는다. 둘이나 넷이면 둘씩 놓는다(넷을 셋과 하나로 가르지 않는다)
  return h("ul", { class: "fig-tiles", "data-many": items.length > 2 && items.length !== 4 ? "" : null }, items.map((item) => {
    const inside = [
      item.icon ? h("span", { class: "fig-tile-icon" }, icon(item.icon, 20)) : null,
      h("span", { class: "fig-tile-text" }, [h("strong", { text: item.title }), item.text ? h("span", { class: "fig-text", text: item.text }) : null]),
    ];
    return h("li", {}, item.href ? h("a", { class: "fig-tile", href: item.href }, inside) : h("div", { class: "fig-tile" }, inside));
  }));
}
