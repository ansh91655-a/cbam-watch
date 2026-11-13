// 전체 메뉴: 사이트의 모든 화면과 그 안에서 고를 수 있는 것(소식의 주제, 규제의 묶음, 일정의 해, 해설서의 장)을 한 창에 펼쳐 보여 준다.
// 머리글 오른쪽 끝의 단추로 연다. 주 메뉴의 펼침 목록을 쓰지 않는 좁은 화면에서는 이 창이 모든 화면으로 가는 길이다.
// 화면의 묶음과 이름은 js/nav/map.js를, 그 안의 목록은 주 메뉴의 펼침 목록(js/ui/navmenu.js의 menuLists)을 따른다.
import { GROUPS, screensOf } from "../nav/map.js";
import { closeDialog, openDialog } from "./dialog.js";
import { h } from "./dom.js";
import { icon } from "./icons.js";
import { menuLists } from "./navmenu.js";
import { topicList } from "./topics.js";

// 창의 세 단에 놓는 묶음(넓은 창에서의 차례). 좁은 창에서는 이 차례대로 한 줄로 내려간다.
const COLUMNS = [["home", "news", "rules", "calendar"], ["goods", "library"], ["handbook"]];

// 화면 하나: 아이콘, 이름, 한 줄 설명
function row(one) {
  return h("a", { class: "am-row", href: one.href }, [
    h("span", { class: "chipicon" }, icon(one.icon, 18)),
    h("span", { class: "am-name", text: one.name }),
    one.about ? h("span", { class: "am-about", text: one.about }) : null,
  ]);
}

// 화면 안에서 고를 수 있는 것들. kind가 "list"이면 한 줄에 하나씩(해설서의 장), 아니면 알약 단추로 늘어놓는다.
function sub(items, kind = "") {
  return items.length ? h("ul", { class: "am-sub", "data-kind": kind || null }, items.map((item) => h("li", {}, h("a", { href: item.href, text: item.name })))) : null;
}

function block(group, lists, chapters) {
  const screens = screensOf(group);
  const single = screens.length === 1;
  // 화면이 하나인 묶음에는 그 화면 안에서 고르는 것을 붙인다(목록 첫 줄의 '전체 …'는 화면 자체와 같으므로 뺀다)
  const inner = single ? ((lists[group.key] || {}).items || []).filter((item) => item.href !== screens[0].href) : [];
  return h("section", { class: "am-group", "aria-label": group.name }, [
    single ? null : h("h3", {}, [h("span", { text: group.name }), group.about ? h("small", { text: group.about }) : null]),
    ...screens.flatMap((one) => [row(one), one.view === "handbook" ? sub(chapters, "list") : null]),
    sub(inner),
  ]);
}

export function menuBody(site) {
  const lists = menuLists(site, topicList());
  const chapters = (((site || {}).menu || {}).handbook || []).map((chapter, at) => ({ href: `#handbook-${chapter.id}`, name: `${at + 1}장 ${chapter.title}` }));
  const placed = new Set(COLUMNS.flat());
  const columns = [...COLUMNS, GROUPS.filter((group) => !placed.has(group.key)).map((group) => group.key)].filter((keys) => keys.length);  // 표에 새로 생긴 묶음은 마지막 단에
  const body = h("nav", { class: "allmenu", "aria-label": "전체 메뉴" }, columns.map((keys) =>
    h("div", { class: "am-col" }, keys.map((key) => GROUPS.find((group) => group.key === key)).filter(Boolean).map((group) => block(group, lists, chapters)))));
  const here = location.hash || "#home";
  for (const link of body.querySelectorAll("a")) {
    if (link.getAttribute("href") === here) link.setAttribute("aria-current", "page");
  }
  // 지금 화면의 링크를 눌러도(주소가 바뀌지 않아도) 창은 닫는다
  body.addEventListener("click", (event) => { if (event.target instanceof Element && event.target.closest("a")) closeDialog(); });
  return body;
}

// 창을 연다. 창을 띄울 수 없는 오래된 브라우저에서는 화면들을 소개하는 안내 화면으로 보낸다.
export function openAllMenu(site) {
  if (!openDialog("전체 메뉴", menuBody(site), "menu")) location.hash = "#about";
}

export function allMenu(button, site) {
  if (!button) return;
  button.addEventListener("click", () => openAllMenu(site));
  // 화면 안의 다른 단추(첫 화면의 길잡이)도 같은 창을 연다
  document.addEventListener("click", (event) => {
    if (event.target instanceof Element && event.target.closest("[data-open='menu']")) openAllMenu(site);
  });
  window.addEventListener("hashchange", closeDialog);
}
