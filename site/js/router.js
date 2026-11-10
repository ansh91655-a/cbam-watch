// 주소의 #이름으로 화면을 고른다. 이름 뒤에 -값을 붙여 화면에 값을 넘긴다(예: #news-price, #calendar-2027).

const VIEWS = ["home", "news", "price", "calendar", "docs", "terms", "about", "design"];

export function current() {
  const [name, ...rest] = location.hash.replace(/^#/, "").split("-");
  return VIEWS.includes(name) ? { name, arg: rest.join("-") } : { name: "home", arg: "" };
}

export function markNav(name) {
  for (const link of document.querySelectorAll(".site-nav a")) {
    if (link.dataset.view === name) link.setAttribute("aria-current", "page");
    else link.removeAttribute("aria-current");
  }
}

export function onRoute(handler) {
  window.addEventListener("hashchange", () => handler(current()));
  handler(current());
}
