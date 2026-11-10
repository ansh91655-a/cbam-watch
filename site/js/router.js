// 주소의 #이름으로 화면을 고른다. 이름은 영문 소문자만 쓴다.

const VIEWS = ["home", "news", "docs", "calendar", "terms", "sources", "about"];

export function currentView() {
  const name = location.hash.replace(/^#/, "");
  return VIEWS.includes(name) ? name : "home";
}

export function markNav(name) {
  for (const link of document.querySelectorAll(".site-nav a")) {
    if (link.dataset.view === name) link.setAttribute("aria-current", "page");
    else link.removeAttribute("aria-current");
  }
}

export function onRoute(handler) {
  window.addEventListener("hashchange", () => handler(currentView()));
  handler(currentView());
}
