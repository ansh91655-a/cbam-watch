// 묶음별 막대(예: 해마다의 비율). 값은 막대 위에 적고, 계열이 둘이면 범례를 단다. 같은 값이 절의 표에도 있다.
import { h } from "../../../ui/dom.js";
import { s } from "../../../ui/svg.js";

const text = (number, unit) => `${Number(number).toLocaleString("ko-KR", { maximumFractionDigits: 1 })}${unit}`;

export function bars(figure) {
  const groups = figure.groups || [];
  const series = (figure.series || []).slice(0, 2);
  const unit = figure.unit || "";
  const holder = h("div", { class: "chart fig-bars" });
  const top = Math.max(1, ...series.flatMap((one) => one.values));
  let drawn = 0;

  function draw() {
    const width = Math.min(Math.max(holder.clientWidth, 260), 620);
    if (width === drawn) return;
    drawn = width;
    const height = 220;
    const box = { top: 26, right: 8, bottom: 30, left: 8 };
    const band = (width - box.left - box.right) / groups.length;
    const floor = height - box.bottom;
    const bar = Math.min(54, (band - 24) / series.length - 6);
    const y = (value) => Math.round((floor - (value / top) * (floor - box.top)) * 10) / 10;
    const svg = s("svg", { width, height, viewBox: `0 0 ${width} ${height}`, role: "img",
      "aria-label": groups.map((group, at) => `${group}: ${series.map((one) => `${one.name} ${text(one.values[at], unit)}`).join(", ")}`).join(". ") }, [
      s("g", { class: "axis" }, [
        s("line", { class: "base", x1: box.left, x2: width - box.right, y1: floor, y2: floor }),
        ...groups.map((group, at) => s("text", { x: box.left + band * (at + 0.5), y: floor + 20, "text-anchor": "middle", text: group })),
      ]),
      ...groups.flatMap((group, at) => series.flatMap((one, order) => {
        const x = box.left + band * (at + 0.5) - (series.length * (bar + 6) - 6) / 2 + order * (bar + 6);
        const high = Math.max(floor - y(one.values[at]), 2);  // 아주 작은 값도 막대가 보이게 한다
        return [
          s("rect", { class: `fig-bar fig-bar-${order + 1}`, x: Math.round(x * 10) / 10, y: floor - high, width: Math.round(bar * 10) / 10, height: high, rx: 4 }),
          s("text", { class: "label", x: x + bar / 2, y: floor - high - 7, "text-anchor": "middle", text: text(one.values[at], unit) }),
        ];
      })),
    ]);
    holder.replaceChildren(svg);
  }

  new ResizeObserver(draw).observe(holder);
  return h("div", { class: "fig-bars-wrap" }, [
    series.length > 1 ? h("ul", { class: "chart-legend" }, series.map((one, order) =>
      h("li", {}, [h("span", { class: `key key-${order + 1} fig-key-box`, "aria-hidden": "true" }), h("span", { text: one.name })]))) : null,
    holder,
  ]);
}
