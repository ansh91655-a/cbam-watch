// 움직임. 내용이 화면에 들어오는 순간에 한 번 나타나게 하고, 그때 그림을 그리거나 수치를 올린다.
// 무엇이 움직이는지는 이 파일 한 곳에 모아 둔다. 화면을 그리는 모듈은 움직임을 모른다(수치 올리기만 data-count로 알린다).
//
//   올라오기(RISE): 한 덩어리씩 아래에서 올라오며 나타난다. 한꺼번에 들어온 것들은 차례를 두고 나타난다.
//   그려지기(DRAW): 숨기지 않는다. 화면에 들어오면 표시(data-in)만 붙이고, 선이 그려지는 모양은 motion.css가 맡는다.
//   수치(COUNT):   data-count가 붙은 글의 숫자가 화면에 들어올 때 올라간다(ui/countup.js).
//
// 화면을 옮겨 새로 그릴 때에만 건다. 걸러 보기를 바꿔 목록만 다시 그릴 때는 움직이지 않는다(글자를 칠 때마다 목록이 깜박이면 방해가 된다).
// 움직임 줄이기를 켠 사람과 IntersectionObserver가 없는 브라우저에서는 아무것도 숨기지 않고 그대로 보여 준다.
// 나타나기가 끝나면 붙였던 표시를 모두 뗀다. 그래야 그 뒤의 가리킴(hover) 반응이 제 빠르기로 움직인다.
import { countUp } from "./countup.js";

const RISE = [
  ".quote", ".feature", ".panel", ".cn-bar", ".card", ".sec-head", ".month-head", ".sector",
  ".rule-card", ".rule-now", ".rule-summary", ".rule-analysis", ".rule-soon", ".tl > li", ".rule-links > li",
  ".stat", ".chart-card", ".table-wrap", ".yearline-card", ".cal-month", ".doc", ".step",
  ".date-list > li", ".rule-rows > li", ".tile", ".item-cols > *", ".cn-result", ".cn-box", ".filters", ".side-nav", ".duty",
].join(", ");
const DRAW = ".chart, .stepper, .spark, .yl-track";
const COUNT = "[data-count]";

const STEP_MS = 55;       // 한꺼번에 들어온 것들 사이의 간격
const MAX_STEPS = 9;      // 간격을 이만큼까지만 벌린다(긴 목록의 끝이 너무 늦지 않게)
const RISE_MS = 900;      // 올라오기가 끝났다고 보는 시간
const DRAW_MS = 2600;     // 그려지기가 끝났다고 보는 시간
const HERO_WAIT_MS = 480; // 큰 머리의 글이 올라온 뒤에 수치를 올린다
const MARKS = { rise: "data-rv", draw: "data-draw" };

let observer = null;
const kinds = new WeakMap();

export function moving() {
  return typeof matchMedia === "function" && matchMedia("(prefers-reduced-motion: no-preference)").matches;
}

function finish(node) {
  for (const name of ["data-rv", "data-draw", "data-in"]) node.removeAttribute(name);
  node.style.removeProperty("--rv-d");
}

function reveal(node, order) {
  const kind = kinds.get(node);
  const wait = Math.min(order, MAX_STEPS) * STEP_MS;
  if (kind === "count") {
    countUp(node, { delay: wait + (node.closest(".hero") ? HERO_WAIT_MS : 120) });
    return;
  }
  node.style.setProperty("--rv-d", `${wait}ms`);
  node.setAttribute("data-in", "");
  window.setTimeout(() => finish(node), wait + (kind === "rise" ? RISE_MS : DRAW_MS));
}

function seen(entries) {
  let order = 0;
  for (const entry of entries) {
    const node = entry.target;
    if (entry.isIntersecting) {
      reveal(node, order);
      order += 1;
    } else if (entry.boundingClientRect.bottom <= 0) {
      finish(node); // 뒤로 가기로 돌아와 이미 지나친 자리에 있는 것: 움직이지 않고 바로 보여 준다
    } else {
      continue;
    }
    observer.unobserve(node);
  }
}

// 화면을 새로 그린 뒤에 부른다. 앞 화면의 것은 놓고, 새 화면에서 움직일 것들을 지켜본다.
export function watch(root) {
  if (observer) observer.disconnect();
  observer = null;
  if (!moving() || typeof IntersectionObserver !== "function") return;
  observer = new IntersectionObserver(seen, { rootMargin: "0px 0px -7% 0px" });
  for (const [selector, kind] of [[RISE, "rise"], [DRAW, "draw"], [COUNT, "count"]]) {
    for (const node of root.querySelectorAll(selector)) {
      if (kinds.has(node)) continue;
      kinds.set(node, kind);
      if (MARKS[kind]) node.setAttribute(MARKS[kind], "");
      observer.observe(node);
    }
  }
}
