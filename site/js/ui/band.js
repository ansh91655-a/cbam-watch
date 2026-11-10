// 화면 머리 띠(첫 화면이 아닌 화면). 화면 너비 끝까지 가는 띠에 제목과 한 줄 설명, 마지막 갱신 시각을 둔다(시각은 app.js가 채운다).
// 오른쪽에는 첫 화면의 점 지도를 옅게 깔아 모든 화면이 한 사이트로 보이게 한다. 지도는 꾸밈이라 읽어 주지 않는다.
import { h } from "./dom.js";
import { heroMap } from "./heromap.js";

// extra에는 머리 띠 안에 함께 둘 것(묶인 화면을 고르는 탭)을 넘긴다.
export function band(title, lead, extra) {
  const art = heroMap({ tags: false });
  art.className = "band-map";
  art.setAttribute("aria-hidden", "true");
  return h("div", { class: "view-head bleed" }, h("div", { class: "band-inner" }, [
    art,
    extra || null,
    h("h1", { text: title }),
    lead ? h("p", { class: "lead", text: lead }) : null,
    h("p", { class: "fresh", "data-fresh": "" }),
  ]));
}
