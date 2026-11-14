// 전체를 두 몫으로 나눈 막대(비용 추정 화면의 막대와 같은 모양). 색만으로 가리지 않도록 이름과 값을 함께 적는다.
import { h } from "../../../ui/dom.js";
import { splitBar } from "../../../ui/splitbar.js";

const value = (number) => Number(number).toLocaleString("ko-KR", { minimumFractionDigits: 3, maximumFractionDigits: 3 });

export function split(figure) {
  const [first, second] = figure.parts || [];
  if (!first || !second || !figure.whole) return null;
  const unit = figure.unit || "";
  return h("div", { class: "fig-split" }, [
    h("p", { class: "fig-whole" }, [h("span", { text: figure.whole.label }), h("b", { text: `${value(figure.whole.value)} ${unit}` })]),
    splitBar({
      label: `${figure.whole.label} ${value(figure.whole.value)} ${unit} 가운데 ${first.label} ${value(first.value)}, ${second.label} ${value(second.value)}`,
      parts: [{ name: first.label, share: first.value, note: `${value(first.value)} ${unit}`, tone: "free" }, { name: second.label, share: second.value, note: `${value(second.value)} ${unit}`, tone: "pay" }],
    }),
  ]);
}
