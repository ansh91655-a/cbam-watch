// 스크롤에 따라 바뀌는 것: 머리글의 그림자, 긴 글 화면의 읽는 자리 표시, 맨 위로 가는 단추.
// 머리글의 높이도 여기에서 재어 --head-h에 적는다(머리글 아래에 붙는 것들이 그 값을 쓴다).
// 읽는 자리 표시는 화면이 data-reading을 단 요소를 그렸을 때만 보인다(규제 하나, 소식 하나의 화면).
import { h } from "./dom.js";
import { icon } from "./icons.js";
import { moving } from "./motion.js";

const SHADOW_FROM = 8;   // 이만큼 내려오면 머리글에 그림자를 준다
const TOP_FROM = 1100;   // 이만큼 내려오면 맨 위로 가는 단추를 보인다

export function scrollCue() {
  const root = document.documentElement;
  const head = document.querySelector(".site-head");
  if (!head) return () => {};
  const bar = h("span", { class: "read-bar", "aria-hidden": "true", hidden: true });
  head.append(bar);
  const up = h("button", { class: "to-top", type: "button", "aria-label": "맨 위로", title: "맨 위로",
    onclick: () => window.scrollTo({ top: 0, behavior: moving() ? "smooth" : "auto" }) }, icon("next", 20));
  document.body.append(up);
  let queued = false;
  let reading = false;
  const update = () => {
    queued = false;
    const y = window.scrollY;
    root.toggleAttribute("data-scrolled", y > SHADOW_FROM);
    up.toggleAttribute("data-show", y > TOP_FROM);  // 보이지 않는 동안에는 초점도 받지 않는다(motion.css의 visibility)
    if (reading) {
      const room = root.scrollHeight - window.innerHeight;
      bar.style.transform = `scaleX(${room > 0 ? Math.min(Math.max(y / room, 0), 1) : 0})`;
    }
  };
  const ask = () => {
    if (queued) return;
    queued = true;
    requestAnimationFrame(update);
  };
  window.addEventListener("scroll", ask, { passive: true });
  window.addEventListener("resize", ask, { passive: true });
  if (typeof ResizeObserver === "function") {
    new ResizeObserver(() => root.style.setProperty("--head-h", `${head.offsetHeight}px`)).observe(head);
  }
  // 화면을 새로 그린 뒤에 부른다: 읽는 자리 표시를 쓸 화면인지 다시 본다.
  return () => {
    reading = Boolean(document.querySelector("#main [data-reading]"));
    bar.hidden = !reading;
    ask();
  };
}
