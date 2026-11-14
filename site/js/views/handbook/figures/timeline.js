// 때의 흐름: 기간(bands)마다 한 묶음이고, 그 안에 날짜가 붙은 일(marks)이 차례로 놓인다.
// 칸의 간격은 실제 기간의 길이와 비례하지 않는다(날짜를 글로 적어 둔다).
import { h } from "../../../ui/dom.js";

// "2027-02-01" → "2027년 2월 1일". edge("부터", "까지")가 있으면 뒤에 붙인다
export function whenText(mark) {
  if (!mark.date) return `${mark.when || ""}${mark.edge || ""}`;
  const [year, month, day] = String(mark.date).split("-").map(Number);
  return `${year}년 ${month}월 ${day}일${mark.edge || ""}`;
}

function markNode(mark) {
  const when = whenText(mark);
  return h("li", { class: "fig-mark" }, [
    mark.date ? h("time", { datetime: mark.date, text: when }) : h("span", { class: "fig-when", text: when }),
    h("strong", { text: mark.label }),
    mark.text ? h("span", { class: "fig-text", text: mark.text }) : null,
  ]);
}

export function timeline(figure) {
  return h("div", { class: "fig-time" }, (figure.bands || []).map((band) => {
    const marks = band.marks || [];
    return h("div", { class: "fig-band", style: `--marks:${Math.max(marks.length, 1)}` }, [
      h("p", { class: "fig-band-head" }, [h("strong", { text: band.label }), band.text ? h("span", { text: band.text }) : null]),
      marks.length ? h("ol", { class: "fig-marks" }, marks.map(markNode)) : null,
    ]);
  }));
}
