// 품목 코드로 CBAM 대상인지 바로 확인하러 가는 띠
import { h } from "../../ui/dom.js";
import { icon } from "../../ui/icons.js";
import { typeHint } from "../../ui/typehint.js";

// 입력 칸에 번갈아 보여 줄 예시. 모두 CBAM 규정 부속서 I에 드는 코드다: 나사·볼트, 가공하지 않은 알루미늄, 포틀랜드 시멘트, 질소 비료, 수소.
const HINT = "CN 코드 예: ";
const SAMPLES = ["7318 15", "7601", "2523 29", "3102 10", "2804 10"];

export function lookupBar() {
  const input = h("input", { type: "search", inputmode: "numeric", autocomplete: "off", placeholder: `${HINT}${SAMPLES[0]}`, "aria-label": "CN 코드" });
  typeHint(input, HINT, SAMPLES);
  return h("section", { class: "cn-bar", "aria-label": "품목 코드 조회" }, [
    h("div", { class: "cn-bar-text" }, [h("strong", { text: "내 제품이 CBAM 대상인지 확인하기" }), h("span", { text: "CN 코드를 넣으면 대상 여부와 법령 근거를 보여 줍니다." })]),
    h("form", { role: "search", onsubmit: (event) => { event.preventDefault(); location.hash = `#cn-${input.value.replace(/\D/g, "")}`; } }, [
      input, h("button", { class: "btn btn-primary", type: "submit" }, [icon("search", 16), h("span", { text: "확인" })]),
    ]),
  ]);
}
