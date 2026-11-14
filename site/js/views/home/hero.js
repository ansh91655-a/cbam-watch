// 첫 화면의 큰 머리: 제목과 단추, 한국에서 EU의 항구로 가는 길을 그린 점 지도, 새 소식 한 줄, 지금 알아 둘 수치 세 칸.
import { h } from "../../ui/dom.js";
import { heroMap } from "../../ui/heromap.js";
import { ticker } from "../../ui/ticker.js";
import { facts } from "./facts.js";

// dated는 날짜가 있는 소식(날짜 차례), ordered는 그것을 첫 화면에 먼저 보일 차례로 놓은 것(news/lead.js)
export function hero(book, events, items, dated, ordered = dated) {
  return h("section", { class: "hero bleed", "aria-label": "소개와 지금 알아 둘 것" }, h("div", { class: "hero-inner" }, [
    heroMap(),
    h("div", { class: "hero-copy" }, [
      h("p", { class: "hero-fresh", "data-fresh": "" }),
      h("h1", {}, ["EU 탄소국경조정제도", h("br"), "CBAM ", h("span", { class: "hl", text: "규제 동향" })]),
      h("div", { class: "hero-actions" }, [
        h("a", { class: "btn btn-main", href: "#news", text: "새 소식 보기" }),
        h("a", { class: "btn btn-ghost", href: "#price", text: "인증서 가격 보기" }),
      ]),
    ]),
    // 최근 소식의 제목이 한 줄씩 돌아간다(중요도가 보통 이상인 것부터). 지도에는 이름이나 설명글을 붙이지 않는다(그림의 설명은 화면 낭독기용 글에만 있다).
    h("div", { class: "hero-strip" }, ticker(ordered)),
    facts(book, events, items, dated),
  ]));
}
