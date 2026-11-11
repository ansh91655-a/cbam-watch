// CBAM 계수 그림. 해마다의 값이 그해 내내 같으므로 계단 모양의 선으로 그리고, 경로(현행, 개정안)마다 한 줄이다.
// 값은 그림을 가리키지 않아도 아래 '표로 보기'에서 모두 볼 수 있다(그림 위의 풍선은 보조 수단이다).
// 선의 색은 경로를 가르는 데만 쓰고, 글은 모두 글자색 이름을 쓴다. 범례는 선과 같은 모양의 짧은 줄로 보여 준다.
import { fill, h, safeLink, table } from "./dom.js";
import { icon } from "./icons.js";
import { s } from "./svg.js";

const TICKS = [0, 25, 50, 75, 100];
const percent = (value) => `${Number(value).toLocaleString("ko-KR", { maximumFractionDigits: 1 })}%`;

// 경로의 해마다 값. 적힌 마지막 해 뒤로는 마지막 값이 이어진다(0이 된 뒤에는 0이다).
export function valueAt(path, year) {
  const years = Object.keys(path.values).map(Number).sort((a, b) => a - b);
  if (year < years[0]) return 100;  // 2025년까지는 무상할당을 줄이지 않는다
  const last = years.filter((value) => value <= year).pop();
  return Number(path.values[String(last)]);
}

export function yearsOf(paths) {
  const all = paths.flatMap((path) => Object.keys(path.values).map(Number));
  const from = Math.min(...all);
  const to = Math.max(...all);
  return Array.from({ length: to - from + 1 }, (_, index) => from + index);
}

function stepPath(values, x, y, band) {
  return values.map((value, index) => `${index ? "V" : `M${x(index)},`}${y(value)}H${Math.round((x(index) + band) * 10) / 10}`).join("");
}

function legend(paths) {
  return h("ul", { class: "chart-legend" }, paths.map((path, index) =>
    h("li", {}, [h("span", { class: `key key-${index + 1}`, "aria-hidden": "true" }), h("span", { text: path.name }), path.note ? h("small", { text: path.note }) : null])));
}

function valueTable(paths, years) {
  const rows = years.map((year) => h("tr", {}, [
    h("th", { scope: "row", text: `${year}년` }),
    ...paths.map((path) => h("td", { class: "num", text: percent(valueAt(path, year)) })),
  ]));
  return h("details", { class: "chart-table" }, [
    h("summary", { text: "값을 표로 보기" }),
    table(["연도", ...paths.map((path) => ({ text: path.name, num: true }))], rows, "연도별 CBAM 계수"),
  ]);
}

function sources(paths) {
  return h("ul", { class: "chart-sources" }, paths.map((path) => {
    const link = safeLink(path.source.url, path.source.text);
    if (link) link.append(icon("out", 13));
    return h("li", {}, [h("strong", { text: path.name }), link]);
  }));
}

export function factorChart(book) {
  const paths = (book.paths || []).slice(0, 2);
  const years = yearsOf(paths);
  const series = paths.map((path) => years.map((year) => valueAt(path, year)));
  const holder = h("div", { class: "chart" });
  const tip = h("div", { class: "tip tip-rows", hidden: true });
  let drawn = 0;

  function showTip(index, cx, cy) {
    fill(tip, h("span", { class: "tip-head", text: `${years[index]}년` }),
      ...paths.map((path, order) => h("span", { class: "tip-row" }, [
        h("span", { class: `key key-${order + 1}`, "aria-hidden": "true" }), h("b", { text: percent(series[order][index]) }), h("span", { text: path.name })])));
    tip.hidden = false;
    const half = tip.offsetWidth / 2;
    tip.style.left = `${Math.min(Math.max(cx, half), holder.clientWidth - half)}px`;
    tip.style.top = `${cy - 14}px`;
  }

  function draw() {
    const width = Math.max(holder.clientWidth, 280);
    if (width === drawn) return;
    drawn = width;
    const height = width < 520 ? 250 : 310;
    const box = { top: 18, right: 12, bottom: 34, left: 40 };
    const band = (width - box.left - box.right) / years.length;
    const x = (index) => Math.round((box.left + index * band) * 10) / 10;
    const y = (value) => Math.round((box.top + (1 - value / 100) * (height - box.top - box.bottom)) * 10) / 10;
    const floor = height - box.bottom;
    const every = band >= 44 ? 1 : band >= 24 ? 2 : 3;  // 좁으면 해를 건너뛰어 적는다
    const roomy = band >= 46;
    // 두 선이 가장 벌어져 있고 둘레가 비어 있는 해에 이름을 적는다(넓은 화면에서만. 좁으면 범례가 맡는다)
    const at = years.indexOf(2031) >= 0 ? years.indexOf(2031) : Math.floor(years.length / 2);
    const upper = series.length > 1 && series[1][at] >= series[0][at] ? 1 : 0;

    const cross = s("line", { class: "cross", y1: box.top, y2: floor, visibility: "hidden" });
    const svg = s("svg", { width, height, viewBox: `0 0 ${width} ${height}`, role: "group",
      "aria-label": `CBAM 계수의 연도별 값. ${years[0]}년부터 ${years[years.length - 1]}년까지, ${paths.map((path) => path.name).join("와 ")}. 값은 아래 표에서도 볼 수 있습니다.` }, [
      s("g", { class: "grid" }, TICKS.map((tick) => s("line", { x1: box.left, x2: width - box.right, y1: y(tick), y2: y(tick) }))),
      s("g", { class: "axis" }, [
        ...TICKS.map((tick) => s("text", { x: box.left - 8, y: y(tick) + 4, "text-anchor": "end", text: tick })),
        s("line", { class: "base", x1: box.left, x2: width - box.right, y1: floor, y2: floor }),
        ...years.map((year, index) => (index % every ? null : s("text", { x: x(index) + band / 2, y: floor + 20, "text-anchor": "middle", text: year }))),
      ]),
      ...series.map((values, order) => s("path", { class: `line line-${order + 1}`, d: stepPath(values, x, y, band), pathLength: 1 })),
      cross,
      roomy && series.length > 1 ? s("g", {}, [
        s("text", { class: "label", x: x(at) + band / 2, y: y(series[upper][at]) - 9, "text-anchor": "middle", text: paths[upper].name }),
        s("text", { class: "label", x: x(at) + band / 2, y: y(series[1 - upper][at]) + 18, "text-anchor": "middle", text: paths[1 - upper].name }),
      ]) : null,
      // 가리키는 자리는 선보다 넓게 잡는다: 그해의 칸 전체
      s("g", {}, years.map((year, index) => {
        const middle = x(index) + band / 2;
        const top = Math.min(...series.map((values) => y(values[index])));
        const hit = s("rect", { class: "hit", x: x(index), y: box.top, width: band, height: floor - box.top, tabindex: 0, role: "img",
          "aria-label": `${year}년: ${paths.map((path, order) => `${path.name} ${percent(series[order][index])}`).join(", ")}` });
        const on = () => { cross.setAttribute("x1", middle); cross.setAttribute("x2", middle); cross.setAttribute("visibility", "visible"); showTip(index, middle, top); };
        const off = () => { cross.setAttribute("visibility", "hidden"); tip.hidden = true; };
        hit.addEventListener("pointerenter", on);
        hit.addEventListener("pointerleave", off);
        hit.addEventListener("focus", on);
        hit.addEventListener("blur", off);
        return hit;
      })),
    ]);
    holder.replaceChildren(svg, tip);
  }

  if (!paths.length) return holder;
  new ResizeObserver(draw).observe(holder);
  return h("div", { class: "chart-card factor-card" }, [
    h("p", { class: "sub", text: book.about || "" }),
    legend(paths),
    holder,
    h("p", { class: "chart-unit", text: "세로축: CBAM 계수(%). 한 해 동안 같은 값이 적용됩니다." }),
    valueTable(paths, years),
    sources(paths),
  ]);
}
