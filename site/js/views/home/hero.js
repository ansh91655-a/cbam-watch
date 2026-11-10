// 첫 화면의 큰 머리: 한 줄 소개와 단추, 한국에서 EU의 항구로 가는 길을 그린 점 지도, 지금 알아 둘 수치 세 칸.
import { h } from "../../ui/dom.js";
import { heroMap } from "../../ui/heromap.js";
import { facts } from "./facts.js";

export function hero(book, events, items, dated) {
  return h("section", { class: "hero bleed", "aria-label": "소개와 지금 알아 둘 것" }, h("div", { class: "hero-inner" }, [
    heroMap(),
    h("div", { class: "hero-copy" }, [
      h("p", { class: "hero-fresh", "data-fresh": "" }),
      h("h1", {}, ["CBAM 규제,", h("br"), h("span", { class: "hl", text: "달라진 것" }), "부터 봅니다"]),
      h("p", { class: "hero-lead", text: "EU 탄소국경조정제도의 법령, 가이던스, 인증서 가격, 일정을 평일마다 확인해 원문과 함께 국문으로 정리합니다." }),
      h("div", { class: "hero-actions" }, [
        h("a", { class: "btn btn-main", href: "#news", text: "새 소식 보기" }),
        h("a", { class: "btn btn-ghost", href: "#price", text: "인증서 가격 보기" }),
      ]),
    ]),
    // EU 회원국과 한국의 이름은 지도 위에 적혀 있다(ui/heromap.js). 여기에는 선의 뜻만 적는다.
    h("p", { class: "hero-legend", "aria-hidden": "true" }, [h("i", { class: "route" }), "한국에서 EU 주요 항구로 가는 길을 나타낸 그림"]),
    facts(book, events, items, dated),
  ]));
}
