// 주소의 #이름으로 화면을 고른다. 주 메뉴 하나가 화면 여럿을 묶을 수 있다(묶음은 js/nav/map.js에 있고, 주 메뉴의 링크에는 묶음의 이름을 data-key로 적는다).
// 화면의 이름이 아닌 주소(#rule, #glossary처럼 잘못 적었거나 없어진 주소)는 없는 주소를 안내하는 화면(views/missing.js)으로 보낸다.
// 이름 뒤에 -값을 붙여 화면에 값을 넘긴다(예: #news-price, #rules-uk, #calendar-2027, #calc-72081000, #item-20261110-ec-news-1a22d2, #law-32023R0956.art-7, #law-32023R0956.art-7.2, #changes-32023R0956, #pdf-guide-3.p12, #sector-steel, #handbook-defaults, #handbook-defaults.markup, #search-기본값).
// 스크롤 자리도 여기에서 맡는다. 링크를 눌러 옮겨 가면 맨 위에서 시작하고, 뒤로·앞으로 가기로 돌아오면 보던 자리로 돌려놓는다.
// 조각을 적은 주소(#law-….art-7, #handbook-….<절>, #changes-….art-7)는 돌아왔을 때에도 화면이 그 조각으로 옮겨 간다(주소가 가리키는 곳이 보던 자리보다 앞선다).
// 그 화면들은 차례에서 조각을 고르면 주소를 그 조각의 것으로 바꿔 두므로, 돌아오면 마지막에 고른 조각에서 시작한다.

import { groupOf } from "./nav/map.js";

const VIEWS = ["home", "news", "item", "rules", "price", "calc", "calendar", "docs", "laws", "law", "changes", "pdf", "terms", "cn", "sector", "handbook", "about", "design", "search"];
export const MISSING = "missing";  // 없는 주소로 왔을 때 보여 주는 화면의 이름(주소로는 쓰지 않는다)
const CLICK_MS = 800; // 링크를 누른 뒤 이 시간 안에 주소가 바뀌면 그 누름 때문에 바뀐 것으로 본다
let clickedAt = -Infinity;
let here = location.hash; // 지금 보고 있는 화면의 주소

// 링크가 아닌 것(검색 칸)이 화면을 옮길 때 쓴다. 링크를 누른 것처럼 새 화면의 맨 위에서 시작한다.
// 이미 그 주소에 있으면 아무것도 하지 않고 false를 돌려준다.
export function visit(hash) {
  if (location.hash === hash) return false;
  clickedAt = performance.now();
  location.hash = hash;
  return true;
}

// 주소의 글(# 뒤)을 화면의 이름과 넘길 값으로 가른다. 글이 없으면 첫 화면이고, 이름이 화면의 것이 아니면 없는 주소를 안내하는 화면이다
// (값으로 주소의 글을 그대로 넘긴다). main은 '본문으로 건너뛰기'가 가리키는 자리라 첫 화면으로 본다.
export function route(hash) {
  const text = String(hash || "").replace(/^#/, "");
  const [name, ...rest] = text.split("-");
  if (VIEWS.includes(name)) return { name, arg: rest.join("-") };
  return text && text !== "main" ? { name: MISSING, arg: text } : { name: "home", arg: "" };
}

export function current() {
  return route(location.hash);
}

// 주 메뉴에서 지금 화면이 든 묶음을 표시한다. 메뉴에 없는 화면(검색, 색 변형)에서는 아무것도 표시하지 않는다.
export function markNav(name) {
  const group = groupOf(name);
  for (const link of document.querySelectorAll(".site-nav > a")) {
    if (group && link.dataset.key === group.key) link.setAttribute("aria-current", "page");
    else link.removeAttribute("aria-current");
  }
}

// 화면은 그대로 두고 주소만 바꾼다(넘겨받은 값을 다 쓴 뒤에 주소에서 뗄 때). 떠날 때의 스크롤 자리도 바뀐 주소로 기억한다.
export function rename(hash) {
  history.replaceState(null, "", hash);
  here = hash;
}

export function onRoute(handler) {
  const left = new Map(); // 주소 → 그 화면을 떠날 때의 스크롤 자리
  let lastY = 0;
  let drawing = false; // 화면을 바꿔 그리는 동안의 스크롤은 사람이 한 것이 아니다
  window.addEventListener("scroll", () => { if (!drawing) lastY = window.scrollY; }, { passive: true });
  document.addEventListener("click", (event) => {
    const link = event.target instanceof Element ? event.target.closest("a[href^='#']") : null;
    if (link) clickedAt = performance.now();
  }, true);
  window.addEventListener("hashchange", async () => {
    left.set(here, lastY);
    here = location.hash;
    const byLink = performance.now() - clickedAt < CLICK_MS;
    clickedAt = -Infinity;
    const top = byLink ? 0 : (left.get(here) || 0);
    drawing = true;
    await handler(current());
    window.scrollTo(0, top);
    lastY = top;
    drawing = false;
  });
  handler(current());
}
