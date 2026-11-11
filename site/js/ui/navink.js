// 주 메뉴의 '지금 화면' 표시(밑줄)가 메뉴 사이를 미끄러져 옮겨 가게 한다.
// 이 표시를 만들지 못하면(오래된 브라우저) 메뉴마다의 밑줄(layout.css)이 그대로 쓰인다.
import { h } from "./dom.js";

export function navInk(nav) {
  if (!nav || typeof ResizeObserver !== "function") return () => {};
  const ink = h("span", { class: "nav-ink", "aria-hidden": "true" });
  nav.append(ink);
  nav.classList.add("has-ink");
  let placed = false;
  const place = () => {
    const now = nav.querySelector('a[aria-current="page"]');
    if (!now) {
      ink.style.opacity = "0";
      return;
    }
    const pad = parseFloat(getComputedStyle(now).paddingLeft) || 0;
    ink.style.width = `${Math.max(now.offsetWidth - pad * 2, 0)}px`;
    ink.style.transform = `translateX(${now.offsetLeft + pad}px)`;
    ink.style.opacity = "1";
    if (!placed) {
      // 처음 자리를 잡을 때는 미끄러지지 않는다. 한 번 그려진 뒤부터 움직인다.
      placed = true;
      requestAnimationFrame(() => requestAnimationFrame(() => ink.setAttribute("data-live", "")));
    }
  };
  new ResizeObserver(place).observe(nav);
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(place);
  return place;
}
