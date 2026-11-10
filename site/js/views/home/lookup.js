// 품목 코드로 CBAM 대상인지 바로 확인하러 가는 띠
import { h } from "../../ui/dom.js";
import { icon } from "../../ui/icons.js";

export function lookupBar() {
  const input = h("input", { type: "search", inputmode: "numeric", autocomplete: "off", placeholder: "CN 코드 예: 7318 15", "aria-label": "CN 코드" });
  return h("section", { class: "cn-bar", "aria-label": "품목 코드 조회" }, [
    h("div", { class: "cn-bar-text" }, [h("strong", { text: "내 제품이 CBAM 대상인지 확인하기" }), h("span", { text: "CN 코드를 넣으면 대상 여부와 법령 근거를 보여 줍니다." })]),
    h("form", { role: "search", onsubmit: (event) => { event.preventDefault(); location.hash = `#cn-${input.value.replace(/\D/g, "")}`; } }, [
      input, h("button", { class: "btn btn-primary", type: "submit" }, [icon("search", 16), h("span", { text: "확인" })]),
    ]),
  ]);
}
