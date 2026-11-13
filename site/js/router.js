// 주소의 #이름으로 화면을 고른다. 주 메뉴 하나가 화면 여럿을 묶을 수 있다(data-group에 화면 이름들을 적는다).
// 이름 뒤에 -값을 붙여 화면에 값을 넘긴다(예: #news-price, #rules-uk, #calendar-2027, #calc-72081000, #item-20261110-ec-news-1a22d2, #law-32023R0956.art-7, #pdf-guide-3.p12, #search-기본값).
// 스크롤 자리도 여기에서 맡는다. 링크를 눌러 옮겨 가면 맨 위에서 시작하고, 뒤로·앞으로 가기로 돌아오면 보던 자리로 돌려놓는다.

const VIEWS = ["home", "news", "item", "rules", "price", "calc", "calendar", "docs", "laws", "law", "pdf", "terms", "cn", "about", "design", "search"];
// 메뉴에 없는 화면이 어느 메뉴 아래인지: 소식 하나를 보는 화면은 '소식' 아래로 본다.
const UNDER = { item: "news", law: "laws", pdf: "laws" };
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

export function current() {
  const [name, ...rest] = location.hash.replace(/^#/, "").split("-");
  return VIEWS.includes(name) ? { name, arg: rest.join("-") } : { name: "home", arg: "" };
}

export function markNav(name) {
  const key = UNDER[name] || name;
  for (const link of document.querySelectorAll(".site-nav > a")) {
    if ((link.dataset.group || link.dataset.view).split(" ").includes(key)) link.setAttribute("aria-current", "page");
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
