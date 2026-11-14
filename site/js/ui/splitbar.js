// 전체를 몫으로 나눈 막대(비용 추정의 '제품 1톤의 배출량', 해설서의 계산 예).
// 몫 사이는 바탕색으로 띄우고, 색만으로 가리지 않도록 범례에 이름과 값을 함께 적는다(css/chart.css).
import { h } from "./dom.js";

// parts: [{ name, share(막대에서 차지하는 크기), note(범례에 적는 값), tone: "free"(둘째 색) | "pay"(첫째 색) }]
export function splitBar({ label, parts }) {
  return h("div", { class: "splitbar" }, [
    h("div", { class: "splitbar-track", role: "img", "aria-label": label }, parts.filter((part) => part.share > 0)
      .map((part) => h("span", { class: "splitbar-seg", "data-tone": part.tone, style: `flex-grow:${Number(part.share).toFixed(3)}` }))),
    h("ul", { class: "chart-legend" }, parts.map((part) =>
      h("li", {}, [h("span", { class: `key${part.tone === "free" ? " key-2" : ""}` }), h("span", { text: part.name }), h("small", { text: part.note })]))),
  ]);
}
