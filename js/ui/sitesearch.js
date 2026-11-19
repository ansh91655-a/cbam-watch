// 머리글의 검색 칸. 어느 화면에서나 찾는 말을 적으면 검색 화면(#search-찾는 말)으로 간다.
// 칸은 index.html에 있고 여기에서는 움직임만 붙인다. 좁은 화면에서는 칸을 숨기고 돋보기 단추만 두는데(css/search.css),
// 그때는 단추가 검색 화면을 열고 그 화면의 큰 입력 칸으로 간다.
import { current, visit } from "../router.js";

const FIELD = "search-q";  // 검색 화면의 큰 입력 칸(views/search.js)

export function decode(arg) {
  try { return decodeURIComponent(arg || ""); } catch (error) { return String(arg || ""); }
}

// 찾는 말의 주소.
export function target(text) {
  const query = String(text || "").trim();
  return query ? `#search-${encodeURIComponent(query)}` : "#search";
}

function toField() {
  const field = document.getElementById(FIELD);
  if (!field) return;
  field.focus();
  field.select();
}

const typing = (node) => node instanceof Element && Boolean(node.closest("input, textarea, select, [contenteditable]"));

export function siteSearch() {
  const form = document.getElementById("site-search");
  const input = document.getElementById("site-q");
  if (!form || !input) return;
  const shown = () => input.offsetParent !== null;

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    // 칸을 숨긴 너비에서 이미 검색 화면을 보고 있으면, 찾은 것을 그대로 두고 그 화면의 큰 입력 칸으로 간다
    const moved = !shown() && current().name === "search" ? false : visit(target(shown() ? input.value : ""));
    if (!moved) {  // 이미 그 결과를 보고 있을 때에도 맨 위의 큰 입력 칸으로 간다
      window.scrollTo(0, 0);
      toField();
    } else if (window.matchMedia("(pointer: coarse)").matches) {
      input.blur();  // 화면 자판이 결과를 가리지 않게 내린다
    }
  });

  // 검색 화면에 있는 동안에는 찾은 말을 칸에도 보여 주고, 다른 화면으로 가면 비운다.
  const sync = () => {
    const route = current();
    input.value = route.name === "search" ? decode(route.arg) : "";
  };
  window.addEventListener("hashchange", sync);
  sync();

  // '/' 키를 누르면 검색 칸으로 간다(글을 적는 중이거나 창이 떠 있을 때는 그대로 둔다).
  document.addEventListener("keydown", (event) => {
    if (event.key !== "/" || event.ctrlKey || event.metaKey || event.altKey || event.defaultPrevented) return;
    if (typing(event.target) || document.querySelector("dialog[open]")) return;
    event.preventDefault();
    if (shown()) {
      input.focus();
      input.select();
    } else if (!visit("#search")) {
      toField();
    }
  });
}
