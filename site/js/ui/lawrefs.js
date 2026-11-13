// 규정 원문으로 가는 링크의 줄: 소식, 의무 일정, 용어집의 글에 적힌 법령과 조문을 사이트의 그 조문으로 잇는다(laws/refs.js).
import { lawHref } from "../laws/refs.js";
import { h } from "./dom.js";
import { icon } from "./icons.js";

// refs는 [{ act, part, label }]. 없으면 null을 돌려준다. name은 줄 머리의 말("규정 원문에서 보기")
export function lawRefs(refs, name = "규정 원문에서 보기", attrs = {}) {
  if (!refs || !refs.length) return null;
  return h("p", { class: "ref-links", ...attrs }, [
    h("span", { class: "ref-name" }, [icon("law", 14), h("span", { text: name })]),
    ...refs.map((ref) => h("a", { href: lawHref(ref), text: ref.label })),
  ]);
}
