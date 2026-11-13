// 주 메뉴의 펼침 목록. 메뉴에 마우스를 올리면 그 메뉴 아래의 목록(소식의 주제, 규제의 묶음, 묶인 화면들)이 펼쳐진다.
// 마우스가 없는 기기와 자판을 위해 메뉴 옆에 펼침 단추를 둔다(index.html). 단추를 누르거나, 메뉴에서 아래 화살표 키를 누르면 펼쳐진다.
// 메뉴가 둘째 줄로 내려가는 좁은 화면에서는 쓰지 않는다(css/navmenu.css가 숨긴다). 그때는 화면 안의 탭과 목록으로 고른다.
// 목록의 내용은 화면의 묶음(js/nav/map.js)과 게시 데이터를 따른다: 주제는 topics.json, 규제 묶음과 일정이 있는 해, 국내 공지·자료의 수는 site.json의 menu(tools/publish/derive.py의 menu).
import { GROUPS, screensOf } from "../nav/map.js";
import { NOTICES, NOTICE_NAME } from "../news/notices.js";
import { h } from "./dom.js";
import { icon } from "./icons.js";
import { topicList } from "./topics.js";

const OPEN_MS = 90;    // 마우스를 올리고 이만큼 지나면 편다(지나가기만 할 때는 펴지 않는다)
const CLOSE_MS = 220;  // 마우스가 벗어나고 이만큼 지나면 접는다(목록으로 내려가는 사이에 접히지 않게)
const WIDE = "(min-width: 1001px)";
const EDGE = 16;       // 목록과 화면 오른쪽 끝 사이에 남기는 거리

// 메뉴마다의 목록: { 묶음의 이름(key): { cols, items: [{ href, name, icon, topic, about }] } }
// 화면이 여럿인 묶음은 그 화면들이 목록이고, 화면이 하나인 묶음(소식, 규제, 일정)은 그 화면 안에서 고르는 것(주제, 규제 묶음, 해)이 목록이다.
export function menuLists(site, topics) {
  const menu = (site && site.menu) || {};
  const live = Array.isArray(menu.topics) ? new Set(menu.topics) : null;  // 소식이 하나도 없는 주제는 싣지 않는다
  const lists = {
    news: { cols: 2, items: [{ href: "#news", name: "전체 소식", icon: "news" },
      ...(topics || []).filter((topic) => !live || live.has(topic.code)).map((topic) => ({ href: `#news-${topic.code}`, name: topic.name, icon: topic.code, topic: topic.code })),
      ...(menu.notices ? [{ href: `#news-${NOTICES}`, name: NOTICE_NAME, icon: "sources" }] : [])] },
    rules: { items: [{ href: "#rules", name: "전체 규제", icon: "law" },
      ...(menu.rules || []).map((group) => ({ href: `#rules-${group.code}`, name: group.name, icon: group.icon || "legis" }))] },
    calendar: { items: (menu.years || []).map((year) => ({ href: `#calendar-${year}`, name: `${year}년 일정`, icon: "calendar" })) },
  };
  for (const group of GROUPS) {
    if (group.views.length > 1) lists[group.key] = { items: screensOf(group).map((one) => ({ href: one.href, name: one.name, icon: one.icon, about: one.about })) };
  }
  return lists;
}

function panel(key, name, list) {
  return h("div", { class: "nav-drop", id: `nav-drop-${key}`, role: "group", "aria-label": `${name} 목록` },
    h("ul", { class: "nav-list", "data-cols": list.cols || null, style: list.cols ? `--rows:${Math.ceil(list.items.length / list.cols)}` : null }, list.items.map((item) => h("li", {},
      h("a", { href: item.href, "data-topic": item.topic || null }, [
        h("span", { class: "chipicon" }, icon(item.icon || "etc", 16)),
        h("span", { class: "nav-name", text: item.name }),
        item.about ? h("span", { class: "nav-about", text: item.about }) : null,
      ])))));
}

export function navMenu(nav, site) {
  if (!nav) return;
  const lists = menuLists(site, topicList());
  const wide = window.matchMedia(WIDE);
  const menus = new Map();  // 메뉴 이름 → { link, button, drop }
  let open = "";
  let timer = 0;

  for (const button of nav.querySelectorAll(":scope > .nav-more")) {
    const key = button.dataset.menu;
    const link = nav.querySelector(`:scope > a[data-menu="${key}"]`);
    const list = lists[key];
    if (!link || !list || !list.items.length) {
      button.hidden = true;  // 목록에 실을 것이 없으면 단추도 두지 않는다
      continue;
    }
    const drop = panel(key, link.textContent.trim(), list);
    drop.inert = true;  // 접혀 있는 동안에는 초점이 들어가지 않는다(접히는 움직임이 끝나기 전에도)
    button.setAttribute("aria-controls", drop.id);
    button.after(drop);
    menus.set(key, { link, button, drop });
  }
  if (!menus.size) return;

  const inside = (key, node) => {
    const menu = menus.get(key);
    return Boolean(menu) && node instanceof Node && (menu.link === node || menu.button.contains(node) || menu.drop.contains(node));
  };

  function close() {
    clearTimeout(timer);
    const menu = menus.get(open);
    if (!menu) return;
    // 초점이 목록 안에 있으면 접기 전에 메뉴로 돌려놓는다(목록을 못 쓰게 하면서 초점이 문서 맨 위로 떨어지지 않게).
    // 펼침 단추가 보이지 않는 너비로 바뀐 때에는 메뉴 이름으로 간다.
    if (menu.drop.contains(document.activeElement)) (menu.button.offsetParent ? menu.button : menu.link).focus();
    menu.drop.removeAttribute("data-open");
    menu.drop.inert = true;
    menu.button.setAttribute("aria-expanded", "false");
    open = "";
  }

  // 목록을 그 메뉴 바로 아래에 놓는다. 화면 오른쪽으로 넘치면 왼쪽으로 당긴다.
  function place(menu) {
    const room = document.documentElement.clientWidth - EDGE - nav.getBoundingClientRect().left - menu.drop.offsetWidth;
    menu.drop.style.left = `${Math.max(Math.min(menu.link.offsetLeft, room), 0)}px`;
  }

  function show(key) {
    clearTimeout(timer);
    if (open === key || !wide.matches) return;
    close();
    const menu = menus.get(key);
    const here = location.hash || "#home";
    for (const link of menu.drop.querySelectorAll("a")) {  // 지금 보고 있는 화면을 표시한다
      if (link.getAttribute("href") === here) link.setAttribute("aria-current", "page");
      else link.removeAttribute("aria-current");
    }
    place(menu);
    menu.drop.inert = false;
    menu.drop.setAttribute("data-open", "");
    menu.button.setAttribute("aria-expanded", "true");
    open = key;
  }

  const later = (work, ms) => { clearTimeout(timer); timer = setTimeout(work, ms); };
  const first = (key) => menus.get(key).drop.querySelector("a");

  for (const [key, menu] of menus) {
    for (const node of [menu.link, menu.button, menu.drop]) {
      // 마우스일 때만 올려놓기로 편다(손가락으로 누를 때에도 같은 일이 생기는데, 그때는 메뉴가 화면을 바로 옮긴다)
      node.addEventListener("pointerenter", (event) => { if (event.pointerType === "mouse") later(() => show(key), open ? 0 : OPEN_MS); });
      // 자판으로 목록 안을 다니는 동안에는 마우스가 벗어났다고 접지 않는다
      node.addEventListener("pointerleave", (event) => { if (event.pointerType === "mouse" && !menu.drop.contains(document.activeElement)) later(close, CLOSE_MS); });
    }
    menu.button.addEventListener("click", (event) => {
      if (open === key) return close();
      show(key);
      if (event.detail === 0) first(key).focus();  // 자판으로 열었으면 목록의 첫 줄로 간다
      return undefined;
    });
    for (const node of [menu.link, menu.button]) {
      node.addEventListener("keydown", (event) => {
        if (event.key !== "ArrowDown" || !wide.matches) return;
        event.preventDefault();
        show(key);
        first(key).focus();
      });
    }
    menu.drop.addEventListener("keydown", (event) => {
      if (event.key !== "ArrowDown" && event.key !== "ArrowUp") return;
      const links = [...menu.drop.querySelectorAll("a")];
      const at = links.indexOf(document.activeElement);
      if (at < 0) return;
      event.preventDefault();
      links[(at + (event.key === "ArrowDown" ? 1 : links.length - 1)) % links.length].focus();
    });
    menu.drop.addEventListener("click", (event) => { if (event.target instanceof Element && event.target.closest("a")) close(); });
  }

  // 초점이 그 메뉴 밖으로 나가면 접는다. Esc로도 접고, 그때는 펼침 단추로 돌아간다.
  nav.addEventListener("focusout", (event) => { if (open && !inside(open, event.relatedTarget)) later(close, 0); });
  document.addEventListener("keydown", (event) => { if (event.key === "Escape" && open) close(); });
  document.addEventListener("pointerdown", (event) => { if (open && !inside(open, event.target)) close(); });
  window.addEventListener("hashchange", close);
  window.addEventListener("resize", close, { passive: true });
}
