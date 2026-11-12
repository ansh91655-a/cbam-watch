// 검색 결과의 구역들: 갈래 하나의 목록, 규정 원문 구역, 화면으로 바로 가는 길, 찾을 말의 예.
// 구역을 고쳐 그릴 때 달라지지 않은 구역은 그대로 둔다(settle). 규정의 글을 늦게 읽어 더할 때 읽고 있던 자리와 초점이 흐트러지지 않게 하려는 것이다.
import { h } from "../../ui/dom.js";
import { count } from "../../ui/format.js";
import { icon } from "../../ui/icons.js";
import { target } from "../../ui/sitesearch.js";
import { codeCard } from "./code.js";
import { hitNode } from "./hits.js";

export const NAMES = { terms: "용어집", rules: "규제", news: "소식", dates: "일정", codes: "품목 코드", files: "원문 대장", laws: "규정 원문" };
// 규정 원문 구역 안의 작은 제목
const PART_NAMES = { laws: "문서", acts: "법령의 조문", guides: "가이던스와 안내 자료" };
const PARTS = ["laws", "acts", "guides"];
const EXAMPLES = ["기본값", "검증기관 인정", "인증서 가격", "하류제품 확대", "영국 CBAM", "7208", "default values"];

function head(title, total, shown, more) {
  return h("div", { class: "search-head" }, [
    h("h2", { text: title }),
    h("span", { class: "count", text: `${count(total)}건${total > shown ? ` 가운데 ${count(shown)}건` : ""}` }),
    more || null,
  ]);
}

const list = (kind, hits, context) => h("ol", { class: "search-list" }, hits.map((hit) => h("li", {}, hitNode(kind, hit, context))));

// 갈래 하나의 구역. code는 찾는 말이 품목 코드일 때의 판정(품목 코드 구역의 맨 위에 놓는다). more는 제목 옆에 둘 것('모두 보기'), after는 목록 아래에 둘 것('더 보기').
export function section(kind, hits, limit, context, { code = null, more = null, after = null } = {}) {
  const shown = hits.slice(0, limit);
  const total = hits.length + (code ? 1 : 0);
  return h("section", { class: "search-sec", "aria-label": `${NAMES[kind]} ${count(total)}건` }, [
    head(NAMES[kind], total, shown.length + (code ? 1 : 0), more),
    code ? codeCard(code) : null,
    shown.length ? list(kind, shown, context) : null,
    after,
  ]);
}

// 규정 원문 구역: 이름으로 찾은 문서, 법령의 조문, 안내 문서의 절을 차례로 놓는다.
// 조문은 앞선 것만 보여 주고, 나머지는 규정 원문 화면에서 같은 말로 찾게 이어 준다.
export function lawSection(kept, limits, context, query, more) {
  const lists = PARTS.filter((kind) => (kept[kind] || []).length);
  const total = lists.reduce((sum, kind) => sum + kept[kind].length, 0);
  const shown = lists.reduce((sum, kind) => sum + Math.min(kept[kind].length, limits[kind]), 0);
  return h("section", { class: "search-sec", "aria-label": `${NAMES.laws} ${count(total)}건` }, [
    head(NAMES.laws, total, shown, more),
    ...lists.flatMap((kind) => [
      lists.length > 1 ? h("h3", { class: "search-sub", text: PART_NAMES[kind] }) : null,
      list(kind, kept[kind].slice(0, limits[kind]), context),
    ]),
    more ? null : h("p", { class: "search-more" }, h("a", { href: `#laws-${encodeURIComponent(query)}` }, [h("span", { text: "규정 원문 화면에서 이 말로 찾기" }), icon("next", 14)])),
  ]);
}

// 규정 원문 구역에 보이는 줄 수.
export function lawShown(kept, limits) {
  return PARTS.reduce((sum, kind) => sum + Math.min((kept[kind] || []).length, limits[kind]), 0);
}

// 찾는 말이 화면의 이름이면 그 화면으로 바로 가는 길.
export function shortcuts(pages) {
  return h("p", { class: "search-pages" }, [h("span", { text: "바로 가기" }),
    ...pages.map((page) => h("a", { class: "chip", href: page.href, title: page.about }, [h("span", { text: page.name }), icon("next", 13)]))]);
}

// 찾을 말의 예. 누르면 그 말로 찾는다.
export function examples() {
  return h("p", { class: "find-examples" }, [h("span", { class: "search-eg", text: "이렇게 찾아보세요" }),
    ...EXAMPLES.map((text) => h("a", { class: "chip", href: target(text), text }))]);
}

// 구역들을 고쳐 놓는다. wanted는 [{ key, make }]: 같은 key의 구역이 이미 있으면 그대로 두고, 없는 것만 만들어 제자리에 넣는다.
export function settle(parent, wanted) {
  const old = new Map([...parent.children].map((node) => [node.dataset.key, node]));
  let at = parent.firstElementChild;
  for (const { key, make } of wanted) {
    let node = old.get(key);
    if (node) {
      old.delete(key);
    } else {
      node = make();
      node.dataset.key = key;
    }
    if (node === at) at = at.nextElementSibling;
    else parent.insertBefore(node, at);
  }
  for (const node of old.values()) node.remove();
}
