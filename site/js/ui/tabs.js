// 주 메뉴 하나 아래에 묶인 화면들 사이를 오가는 탭. 화면 머리 띠 안에 둔다.
import { h } from "./dom.js";
import { icon } from "./icons.js";

// '자료·안내' 아래의 화면: [화면 이름, 보이는 이름, 아이콘]
const LIBRARY = [["docs", "원문 대장", "file"], ["terms", "용어집", "terms"], ["about", "안내", "who"]];

export function libraryTabs(current) {
  return h("nav", { class: "tabs", "aria-label": "자료·안내에서 볼 것 고르기" }, LIBRARY.map(([view, name, key]) =>
    h("a", { href: `#${view}`, "aria-current": view === current ? "page" : null }, [icon(key, 16), h("span", { text: name })])));
}
