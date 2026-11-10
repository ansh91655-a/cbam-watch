// 연간 일정선. 한 해를 왼쪽 1월 1일에서 오른쪽 12월 31일까지 한 줄로 그리고, 일정을 날짜 자리에 점으로 찍는다.
// 이름표는 선 위에 겹치지 않게 단을 나눠 놓는다. 자리가 없는 일정은 점만 찍고 아래 달력에서 보게 한다.
import { caveatMark, splitCaveat } from "./caveat.js";
import { fill, h } from "./dom.js";
import { koreanDate } from "./format.js";

const LABEL_WIDTH = 164;
const LABEL_GAP = 14;
const LANE_HEIGHT = 62;
const MAX_LANES = 3;

function place(year, value) {
  const [y, m, d] = String(value).split("-").map(Number);
  const start = Date.UTC(year, 0, 1);
  return (Date.UTC(y, (m || 1) - 1, d || 1) - start) / (Date.UTC(year + 1, 0, 1) - start);
}

export function yearLine(events, year, todayIso, onPick) {
  const mine = events.filter((event) => String(event.date).startsWith(`${year}-`));
  const labels = h("div", { class: "yl-labels" });
  const track = h("div", { class: "yl-track" }, h("div", { class: "yl-line" }));
  const months = h("div", { class: "yl-months", "aria-hidden": "true" }, Array.from({ length: 12 }, (_, index) => h("span", { text: `${index + 1}월` })));
  const root = h("div", { class: "yearline" }, [labels, track, months]);
  const hidden = h("p", { class: "count", hidden: true });
  const wrap = h("div", { class: "yearline-wrap" });
  let centered = false;

  // 좁은 화면에서는 한 해가 다 보이지 않아 옆으로 민다. 처음에 오늘이 가운데에 오게 밀어 둔다(한 번만).
  function centerToday() {
    if (centered || !todayIso.startsWith(`${year}-`)) return;
    const over = wrap.scrollWidth - wrap.clientWidth;
    if (over <= 0) return;
    centered = true;
    wrap.scrollLeft = Math.max(0, Math.min(over, root.offsetLeft + place(year, todayIso) * root.clientWidth - wrap.clientWidth / 2));
  }

  if (todayIso.startsWith(`${year}-`)) {
    const at = place(year, todayIso) * 100;
    track.append(h("div", { class: "yl-done", style: `width:${at}%` }), h("div", { class: "yl-today", style: `left:${at}%`, title: `오늘 ${koreanDate(todayIso, false)}` }));
  } else if (todayIso > `${year}-12-31`) {
    track.append(h("div", { class: "yl-done", style: "width:100%" }));
  }
  for (const event of mine) {
    const monthOnly = String(event.date).length === 7;
    track.append(h("button", {
      class: "yl-dot", type: "button", style: `left:${place(year, event.date) * 100}%`, "data-kind": event.kind || null, "data-month": monthOnly ? "true" : null,
      "aria-label": `${koreanDate(event.date)} ${event.title}`, title: `${koreanDate(event.date, false)} ${event.title}`, onclick: () => onPick(event),
    }));
  }

  function layout() {
    const width = root.clientWidth;
    if (!width) return;
    // 늦은 일정부터 아래 단에 놓는다. 그러면 이른 일정의 기둥이 늦은 일정의 이름표를 가로지르지 않는다.
    const lanes = [];
    const placed = [];
    for (const event of [...mine].reverse()) {
      const center = place(year, event.date) * width;
      const flipped = center + LABEL_WIDTH > width;
      const left = flipped ? center - LABEL_WIDTH : center;
      let lane = 0;
      while (lane < MAX_LANES && (lanes[lane] || []).some((box) => left < box.right + LABEL_GAP && box.left < left + LABEL_WIDTH + LABEL_GAP)) lane += 1;
      if (lane === MAX_LANES) continue;
      (lanes[lane] = lanes[lane] || []).push({ left, right: left + LABEL_WIDTH });
      placed.push({ event, center, left, lane, flipped });
    }
    const height = Math.max(lanes.length, 1) * LANE_HEIGHT;
    labels.style.height = `${height}px`;
    fill(labels, placed.flatMap(({ event, center, left, lane, flipped }) => {
      const top = height - (lane + 1) * LANE_HEIGHT;
      const { name, flag } = splitCaveat(event.title);  // 이름이 두 줄에서 잘려도 '보도 기준' 같은 단서는 날짜 옆에 보인다
      return [
        h("div", { class: "yl-stem", style: `left:${center}px; top:${top}px; height:${height - top + 10}px` }),
        h("button", { class: "yl-label", type: "button", "data-flipped": flipped ? "true" : null, style: `left:${left}px; top:${top}px`, onclick: () => onPick(event) }, [
          h("span", { class: "d" }, [String(event.date).length === 7 ? `${koreanDate(event.date, false)}부터` : koreanDate(event.date, false), caveatMark(flag)]),
          h("span", { class: "t", text: name }),
        ]),
      ];
    }));
    const left = mine.length - placed.length;
    hidden.hidden = left === 0;
    hidden.textContent = left ? `이름표를 놓을 자리가 없는 일정 ${left}건은 점으로만 표시했습니다. 아래 달력에 모두 있습니다.` : "";
    centerToday();
  }

  new ResizeObserver(layout).observe(root);
  const legend = h("div", { class: "yl-legend", "aria-hidden": "true" }, [
    h("span", {}, [h("i", { class: "yl-dot" }), "시행, 행사"]),
    h("span", {}, [h("i", { class: "yl-dot", "data-kind": "기한" }), "기한"]),
    h("span", {}, [h("i", { class: "yl-dot", "data-kind": "가격" }), "가격 게시"]),
    h("span", {}, [h("i", { class: "yl-dot", "data-month": "true" }), "달만 정해진 일정"]),
    todayIso.startsWith(`${year}-`) ? h("span", { text: `세로선은 오늘(${koreanDate(todayIso, false)})` }) : null,
  ]);
  wrap.append(root, legend, hidden);
  return wrap;
}
