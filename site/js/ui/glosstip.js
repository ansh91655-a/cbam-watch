// 글 속 용어 풀이의 풀이 칸: 표시한 용어를 누르면 그 아래에 뜨는 작은 칸. 사이트에 하나만 두고 내용을 바꿔 가며 쓴다.
// 누르거나 Enter로 열면 초점이 칸으로 가고(Tab으로 칸 안의 링크에 닿는다), Esc나 칸 밖을 누르면 닫히며 초점이 용어로 돌아간다.
// 마우스를 올려 연 것은 초점을 옮기지 않고, 마우스가 용어와 칸을 모두 떠나면 닫힌다.
import { termHref } from "../laws/refs.js";
import { h } from "./dom.js";
import { icon } from "./icons.js";

const GAP = 8;      // 용어와 칸 사이
const EDGE = 12;    // 화면 가장자리와 칸 사이
const LEAVE_MS = 220; // 마우스가 칸을 떠난 뒤 닫기까지(용어로 돌아갈 틈)
let tip = null;
let owner = null;   // 지금 칸을 연 용어(단추)

function close(back = true) {
  if (!tip || tip.hidden) return;
  const inside = tip.contains(document.activeElement);
  tip.hidden = true;
  if (owner) {
    owner.setAttribute("aria-expanded", "false");
    delete owner.dataset.held;
  }
  if (back && inside && owner && owner.isConnected) owner.focus();
  owner = null;
}

function make() {
  tip = h("div", { class: "gloss-tip", role: "dialog", "aria-labelledby": "gloss-tip-name", tabindex: "-1", hidden: true });
  document.body.append(tip);
  document.addEventListener("keydown", (event) => { if (event.key === "Escape" && !tip.hidden) { event.preventDefault(); close(); } });
  document.addEventListener("pointerdown", (event) => { if (!tip.hidden && !tip.contains(event.target) && !(owner && owner.contains(event.target))) close(false); });
  // 마우스를 올려 연 것은 마우스가 칸을 떠나면 닫는다(눌러서 연 것은 그대로 둔다. data-held는 ui/gloss.js가 적는다)
  tip.addEventListener("pointerleave", () => window.setTimeout(() => {
    if (owner && !owner.dataset.held && !tip.matches(":hover") && !owner.matches(":hover")) close(false);
  }, LEAVE_MS));
  window.addEventListener("hashchange", () => close(false));
  window.addEventListener("resize", () => close(false));
  return tip;
}

// 용어의 아래에 놓는다. 아래에 자리가 모자라고 위에 자리가 있으면 위에 놓는다. 화면의 좌우를 넘지 않게 한다.
function place(button) {
  const rect = button.getBoundingClientRect();
  const width = tip.offsetWidth;
  const height = tip.offsetHeight;
  const page = document.documentElement.clientWidth;
  const left = Math.max(EDGE, Math.min(rect.left, page - width - EDGE));
  const below = rect.bottom + GAP + height <= window.innerHeight || rect.top - GAP - height < 0;
  tip.style.left = `${left + window.scrollX}px`;
  tip.style.top = `${(below ? rect.bottom + GAP : rect.top - GAP - height) + window.scrollY}px`;
}

export function isOpenFor(button) {
  return Boolean(tip) && !tip.hidden && owner === button;
}

// button: 글 속의 용어, term: 그 용어의 자료. focus가 참이면 초점을 칸으로 옮긴다(누르거나 자판으로 연 때)
export function openTip(button, term, focus) {
  if (!tip) make();
  if (owner && owner !== button) owner.setAttribute("aria-expanded", "false");
  owner = button;
  const names = [term.en, term.abbr].filter(Boolean).join(", ");
  tip.replaceChildren(
    h("p", { class: "gloss-tip-head" }, [h("strong", { id: "gloss-tip-name", text: term.ko || term.abbr }), names ? h("span", { lang: "en", text: names }) : null]),
    h("p", { class: "gloss-tip-text", text: term.text }),
    h("p", { class: "gloss-tip-links" }, [
      term.read ? h("a", { href: term.read }, [icon("guide", 14), h("span", { text: "해설서에서 읽기" })]) : null,
      h("a", { href: termHref(term) }, [icon("terms", 14), h("span", { text: "용어집에서 보기" })]),
    ]),
    h("button", { type: "button", class: "gloss-tip-close", "aria-label": "풀이 닫기", onclick: () => close() }, icon("close", 14)),
  );
  tip.hidden = false;
  button.setAttribute("aria-expanded", "true");
  place(button);
  if (focus) tip.focus({ preventScroll: true });
}

export function closeTip(back = true) {
  close(back);
}

// 마우스가 칸 위에 있는지(용어를 떠난 마우스가 칸으로 들어왔으면 닫지 않는다)
export function tipHovered() {
  return Boolean(tip) && !tip.hidden && tip.matches(":hover");
}
