// 주소의 #이름으로 화면을 고른다. 주 메뉴 하나가 화면 여럿을 묶을 수 있다(data-group에 화면 이름들을 적는다). 이름 뒤에 -값을 붙여 화면에 값을 넘긴다(예: #news-price, #rules-uk, #calendar-2027).

const VIEWS = ["home", "news", "rules", "price", "calendar", "docs", "terms", "cn", "about", "design"];

export function current() {
  const [name, ...rest] = location.hash.replace(/^#/, "").split("-");
  return VIEWS.includes(name) ? { name, arg: rest.join("-") } : { name: "home", arg: "" };
}

export function markNav(name) {
  for (const link of document.querySelectorAll(".site-nav a")) {
    if ((link.dataset.group || link.dataset.view).split(" ").includes(name)) link.setAttribute("aria-current", "page");
    else link.removeAttribute("aria-current");
  }
}

export function onRoute(handler) {
  window.addEventListener("hashchange", () => handler(current()));
  handler(current());
}
