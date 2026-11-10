// 소식의 제목 링크. 국문 요약이 있는 소식은 이 사이트의 요약 화면(#item-…)으로 가고,
// 제목이 곧 내용인 한 줄 소식은 원문으로 바로 간다(바깥으로 나간다는 표시를 붙인다).
import { h, safeLink } from "./dom.js";
import { icon } from "./icons.js";

export function hasPage(item) {
  return Boolean(item.id) && !item.brief;
}

export function titleLink(item, attrs = {}) {
  if (hasPage(item)) return h("a", { href: `#item-${item.id}`, text: item.title || "", ...attrs });
  const link = safeLink(item.link, item.title || "원문", attrs);
  if (!link) return h("span", { text: item.title || "", ...attrs });
  link.append(icon("out", 14));
  return link;
}
