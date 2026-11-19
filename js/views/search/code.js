// 검색 결과 맨 위에 놓는 품목 코드의 판정. 찾는 말이 CN 코드일 때 그 코드가 CBAM 대상인지를 먼저 알려 준다.
// 판정은 js/search/codes.js가 품목 코드 조회와 같은 셈으로 해 둔 것이다. 근거와 제외 품목은 품목 코드 조회에서 본다.
import { SECTOR, spaced, STATE } from "../../cn/names.js";
import { h, pill } from "../../ui/dom.js";
import { icon } from "../../ui/icons.js";

const ROWS = 2;  // 걸린 품목을 보여 주는 줄 수

export function codeCard(found) {
  const [name, tone, about] = STATE[found.state];
  const more = found.later ? "지금의 목록에는 없지만, EU 집행위원회가 낸 확대 개정안에는 든 코드입니다."
    : (found.council ? "지금의 목록과 EU 집행위원회의 개정안에는 없지만, EU 이사회의 안이 더한 코드입니다." : "");
  return h("a", { class: "search-code", href: `#cn-${found.code}` }, [
    h("span", { class: "search-code-top" }, [h("strong", { class: "cn-code", text: spaced(found.code) }), pill(name, tone)]),
    h("span", { class: "hit-text", text: [about, more].filter(Boolean).join(" ") }),
    ...found.rows.slice(0, ROWS).map((hit) => h("span", { class: "hit-text" }, [
      h("span", { class: "hit-code", text: hit.entry.shown }), h("span", { lang: "en", text: hit.entry.text }), h("span", { text: ` (${SECTOR[hit.entry.sector] || hit.entry.sector})` })])),
    h("span", { class: "search-code-go" }, [h("span", { text: "품목 코드 조회에서 근거 보기" }), icon("next", 14)]),
  ]);
}
