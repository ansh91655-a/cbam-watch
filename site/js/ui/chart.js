// 가격 그림. 가격은 적용 기간 동안 같은 값이므로 계단 모양의 선으로 그린다.
// 값은 그림을 가리키지 않아도 아래 표에서 모두 볼 수 있다(그림 위의 풍선은 보조 수단이다).
import { fill, h } from "./dom.js";
import { price } from "./format.js";
import { s } from "./svg.js";

const DAY = 86400000;
const time = (iso) => Date.parse(`${iso}T00:00:00Z`);

// 계단의 한 칸: 기간의 시작부터 끝 다음 날까지.
function steps(rows) {
  return rows.map((row) => ({ row, start: time(row.from), end: time(row.to) + DAY, value: Number(row.value) }));
}

function niceStep(span, count) {
  const raw = span / count;
  const magnitude = 10 ** Math.floor(Math.log10(raw));
  const unit = raw / magnitude;
  return (unit <= 1 ? 1 : unit <= 2 ? 2 : unit <= 5 ? 5 : 10) * magnitude;
}

function valueAxis(values) {
  const low = Math.min(...values);
  const high = Math.max(...values);
  const pad = Math.max((high - low) * 0.3, high * 0.04);
  const step = niceStep(high - low + pad * 2, 4);
  const min = Math.floor((low - pad) / step) * step;
  const max = Math.ceil((high + pad) / step) * step;
  const ticks = [];
  for (let value = min; value <= max + step / 1000; value += step) ticks.push(Math.round(value * 100) / 100);
  return { min, max, ticks };
}

// 달의 첫날에 눈금을 둔다. 기간이 길어지면 석 달, 여섯 달, 한 해 간격으로 넓힌다.
function timeTicks(from, to) {
  const months = (to - from) / (30.44 * DAY);
  const every = months <= 8 ? 1 : months <= 30 ? 3 : months <= 72 ? 6 : 12;
  const ticks = [];
  const cursor = new Date(from);
  let year = cursor.getUTCFullYear();
  let month = cursor.getUTCMonth();
  for (let guard = 0; guard < 600; guard += 1) {
    const at = Date.UTC(year, month, 1);
    if (at > to) break;
    if (at >= from && month % every === 0) {
      const first = ticks.length === 0 || month === 0;
      ticks.push({ at, label: first ? `${year}년 ${month + 1}월` : `${month + 1}월` });
    }
    month += 1;
    if (month > 11) { month = 0; year += 1; }
  }
  return ticks;
}

// 값을 적어 둘 칸을 고른다. 칸이 몇 개 안 되면 모두, 많으면 마지막과 가장 높은 값과 가장 낮은 값만.
function labelled(list) {
  if (list.length <= 4) return new Set(list.map((_, index) => index));
  const values = list.map((step) => step.value);
  return new Set([list.length - 1, values.indexOf(Math.max(...values)), values.indexOf(Math.min(...values))]);
}

function linePath(list, x, y) {
  let path = "";
  list.forEach((step, index) => {
    const joined = index > 0 && step.start - list[index - 1].end <= DAY;
    path += `${joined ? "V" + y(step.value) : "M" + x(step.start) + " " + y(step.value)}H${x(step.end)}`;
  });
  return path;
}

function areaPath(list, x, y, floor) {
  let path = "";
  let open = null;
  list.forEach((step, index) => {
    const joined = index > 0 && step.start - list[index - 1].end <= DAY;
    if (!joined) {
      if (open !== null) path += `V${floor}H${open}Z`;
      open = x(step.start);
      path += `M${open} ${floor}V${y(step.value)}`;
    } else {
      path += `V${y(step.value)}`;
    }
    path += `H${x(step.end)}`;
  });
  return open === null ? "" : `${path}V${floor}H${open}Z`;
}

export function priceChart(rows, unit = "유로") {
  const holder = h("div", { class: "chart" });
  const tip = h("div", { class: "tip", hidden: true });
  const list = steps(rows);
  let drawn = 0;

  function showTip(step, cx, cy) {
    fill(tip,
      h("b", { text: `${price(step.value)} ${unit}` }),
      h("span", { text: step.row.label }),
      step.row.published ? h("span", { text: ` (${step.row.published} 게시)` }) : null,
    );
    tip.hidden = false;
    const half = tip.offsetWidth / 2;
    tip.style.left = `${Math.min(Math.max(cx, half), holder.clientWidth - half)}px`;
    tip.style.top = `${cy - 14}px`;
  }

  function draw() {
    const width = Math.max(holder.clientWidth, 280);
    if (width === drawn) return;
    drawn = width;
    const height = width < 520 ? 240 : 310;
    const box = { top: 30, right: list.length > 4 ? 62 : 22, bottom: 32, left: 46 };
    const from = list[0].start;
    const to = list[list.length - 1].end;
    const axis = valueAxis(list.map((step) => step.value));
    const x = (at) => Math.round((box.left + ((at - from) / (to - from)) * (width - box.left - box.right)) * 10) / 10;
    const y = (value) => Math.round((box.top + (1 - (value - axis.min) / (axis.max - axis.min)) * (height - box.top - box.bottom)) * 10) / 10;
    const floor = height - box.bottom;
    const marks = labelled(list);
    const last = list[list.length - 1];

    const cross = s("line", { class: "cross", y1: box.top, y2: floor, visibility: "hidden" });
    const svg = s("svg", { width, height, viewBox: `0 0 ${width} ${height}`, role: "group", "aria-label": `CBAM 인증서 가격 추세. ${list[0].row.label}부터 ${last.row.label}까지 ${list.length}개 기간. 값은 아래 표에 있습니다.` }, [
      s("g", { class: "grid" }, axis.ticks.map((tick) => s("line", { x1: box.left, x2: width - box.right, y1: y(tick), y2: y(tick) }))),
      s("g", { class: "axis" }, [
        ...axis.ticks.map((tick) => s("text", { x: box.left - 8, y: y(tick) + 4, "text-anchor": "end", text: tick })),
        s("line", { class: "base", x1: box.left, x2: width - box.right, y1: floor, y2: floor }),
        ...timeTicks(from, to).map((tick) => s("text", { x: x(tick.at), y: floor + 20, "text-anchor": x(tick.at) < box.left + 30 ? "start" : "middle", text: tick.label })),
      ]),
      s("path", { class: "area", d: areaPath(list, x, y, floor) }),
      s("path", { class: "line", d: linePath(list, x, y) }),
      cross,
      s("circle", { class: "dot", cx: x(last.end), cy: y(last.value), r: 5 }),
      s("g", {}, list.map((step, index) => {
        if (!marks.has(index)) return null;
        const atEnd = index === list.length - 1 && list.length > 4;
        return atEnd
          ? s("text", { class: "label", x: x(step.end) + 10, y: y(step.value) + 4, text: price(step.value) })
          : s("text", { class: "label", x: (x(step.start) + x(step.end)) / 2, y: y(step.value) - 9, "text-anchor": "middle", text: price(step.value) });
      })),
      // 가리키는 자리는 선보다 넓게 잡는다: 칸의 너비 전체, 그림의 높이 전체
      s("g", {}, list.map((step) => {
        const left = x(step.start);
        const wide = Math.max(x(step.end) - left, 4);
        const middle = left + wide / 2;
        const hit = s("rect", { class: "hit", x: left, y: box.top, width: wide, height: floor - box.top, tabindex: 0, role: "img", "aria-label": `${step.row.label} ${price(step.value)} ${unit}${step.row.published ? `, ${step.row.published} 게시` : ""}` });
        const on = () => { cross.setAttribute("x1", middle); cross.setAttribute("x2", middle); cross.setAttribute("visibility", "visible"); showTip(step, middle, y(step.value)); };
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

  if (!list.length) return holder;
  new ResizeObserver(draw).observe(holder);
  return holder;
}

// 첫 화면의 작은 그림. 축과 글 없이 흐름만 보여 준다.
export function sparkline(rows, width = 112, height = 36) {
  const list = steps(rows);
  if (list.length < 2) return null;
  const values = list.map((step) => step.value);
  const low = Math.min(...values);
  const high = Math.max(...values);
  const from = list[0].start;
  const to = list[list.length - 1].end;
  const x = (at) => Math.round((3 + ((at - from) / (to - from)) * (width - 12)) * 10) / 10;
  const y = (value) => Math.round((6 + (1 - (value - low) / ((high - low) || 1)) * (height - 12)) * 10) / 10;
  const last = list[list.length - 1];
  return s("svg", { class: "spark", width, height, viewBox: `0 0 ${width} ${height}`, "aria-hidden": "true" }, [
    s("path", { class: "line", d: linePath(list, x, y) }),
    s("circle", { class: "dot", cx: x(last.end), cy: y(last.value), r: 4 }),
  ]);
}
