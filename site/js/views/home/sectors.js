// 부문별 보기로 가는 칸. 부문마다 그림이 있는 칸을 짙은 띠에 놓는다.
// 누르면 그 부문의 대상 품목, 가이던스, 기본값, 소식을 모은 화면(#sector-<부문>)으로 간다. 가이던스의 원문과 국문은 그 화면에서 연다.
import { h } from "../../ui/dom.js";
import { icon } from "../../ui/icons.js";

// CBAM 대상 부문과 EU 집행위원회의 부문별 가이던스 번호
const SECTORS = [["steel", "철강", "5d"], ["aluminium", "알루미늄", "5e"], ["cement", "시멘트", "5a"], ["fertilisers", "비료", "5c"], ["hydrogen", "수소", "5b"], ["electricity", "전력", "5f"]];

function tile([key, name, no]) {
  return h("a", { class: "sector", "data-sector": key, href: `#sector-${key}`, title: `${name} 부문의 대상 품목, 가이던스, 기본값, 소식 모아 보기` }, [
    h("span", { class: "sector-art", "aria-hidden": "true" }, icon(key, 92)),
    h("span", { class: "sector-body" }, [
      h("span", { class: "tile-name", text: name }),
      h("span", { class: "tile-sub", text: `대상 품목, 가이던스 ${no}, 소식` }),
      h("span", { class: "get" }, [icon("next", 15), h("span", { text: "모아 보기" })]),
    ]),
  ]);
}

export function sectors() {
  return h("section", { class: "showcase bleed", "aria-labelledby": "h-sectors" }, h("div", { class: "showcase-inner" }, [
    h("div", { class: "sec-head" }, [h("h2", { id: "h-sectors", text: "부문별로 보기" }), h("a", { href: "#laws", text: "규정 원문 전체 보기" })]),
    h("p", { class: "sec-lead", text: "CBAM 대상 부문마다 대상 품목과 EU 집행위원회의 가이던스, 기본값, 소식을 한곳에 모았습니다." }),
    h("div", { class: "sectors" }, SECTORS.map(tile)),
  ]));
}
