// 첫 화면의 큰 머리: 한 줄 소개와 단추, 한국에서 EU의 항구로 가는 길을 그린 점 지도, 새 소식 한 줄, 지금 알아 둘 수치 세 칸.
import { h } from "../../ui/dom.js";
import { heroMap } from "../../ui/heromap.js";
import { ticker } from "../../ui/ticker.js";
import { facts } from "./facts.js";

export function hero(book, events, items, dated) {
  return h("section", { class: "hero bleed", "aria-label": "소개와 지금 알아 둘 것" }, h("div", { class: "hero-inner" }, [
    heroMap(),
    h("div", { class: "hero-copy" }, [
      h("p", { class: "hero-fresh", "data-fresh": "" }),
      h("h1", {}, ["원문과 함께 보는", h("br"), "EU CBAM ", h("span", { class: "hl", text: "규제 동향" })]),
      h("p", { class: "hero-lead", text: "EU 탄소국경조정제도의 법령, 가이던스, 인증서 가격, 일정을 평일마다 확인하여 국문으로 정리해 드립니다." }),
      h("div", { class: "hero-actions" }, [
        h("a", { class: "btn btn-main", href: "#news", text: "새 소식 보기" }),
        h("a", { class: "btn btn-ghost", href: "#price", text: "인증서 가격 보기" }),
      ]),
    ]),
    // 가장 최근 소식의 제목이 한 줄씩 돌아간다. 지도에는 이름이나 설명글을 붙이지 않는다(그림의 설명은 화면 낭독기용 글에만 있다).
    h("div", { class: "hero-strip" }, ticker(dated)),
    facts(book, events, items, dated),
  ]));
}
