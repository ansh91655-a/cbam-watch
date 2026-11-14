// 계산에 나오는 용어의 풀이(내재배출량, 기본값, 마크업, 무상할당 조정, CBAM 벤치마크, CBAM 계수, 부문 간 보정계수, CBAM 인증서).
// 글은 자료(data/calc.json의 glossary)에서 오고, 풀이마다 근거가 된 법령의 원문을 가리킨다. 해설서에 그 용어를 다루는 장이 있으면 그리로도 잇는다.
import { h } from "../../ui/dom.js";
import { sourceLink } from "./notes.js";

const MORE = { href: "#handbook-certificates", text: "해설서에서 차례로 읽기" };

// handbook: 해설서가 실려 있으면 참(그때만 해설서로 가는 길을 보여 준다)
export function termsPanel(book, handbook = false) {
  const terms = book.glossary || [];
  if (!terms.length) return null;
  return h("section", { class: "panel calc-terms", "aria-labelledby": "h-calc-terms" }, [
    h("div", { class: "sec-head" }, [h("h2", { id: "h-calc-terms", text: "용어 풀이" }), handbook ? h("a", { href: MORE.href, text: MORE.text }) : null]),
    h("dl", { class: "calc-term-list" }, terms.flatMap((term) => [
      h("dt", {}, [h("span", { text: term.ko }), h("small", { lang: "en", text: [term.en, term.abbr].filter(Boolean).join(", ") })]),
      h("dd", {}, [h("span", { text: term.text }), h("span", { class: "calc-term-src" }, [h("span", { text: "근거" }), ...term.sources.map(sourceLink)])]),
    ])),
  ]);
}
