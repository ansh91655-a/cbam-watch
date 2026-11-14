// 주 메뉴 하나 아래에 묶인 화면들 사이를 오가는 탭. 화면 머리 띠 안에 둔다. 묶음과 이름은 js/nav/map.js를 따른다.
import { groupOf, screensOf, UNDER } from "../nav/map.js";
import { h } from "./dom.js";
import { icon } from "./icons.js";

// 그 화면이 든 묶음의 탭. 화면이 하나뿐인 묶음(소식, 규제, 일정)과 메뉴에 없는 화면에는 탭이 없다(null).
export function groupTabs(view) {
  const group = groupOf(view);
  if (!group || group.views.length < 2) return null;
  const now = UNDER[view] || view;
  return h("nav", { class: "tabs", "aria-label": `${group.name}에서 볼 것 고르기` }, screensOf(group).map((one) =>
    h("a", { href: one.href, "aria-current": one.view === now ? "page" : null }, [icon(one.icon, 16), h("span", { text: one.name })])));
}
