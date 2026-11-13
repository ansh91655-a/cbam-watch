// 규정에서 찾기. 낱말이나 질문을 적으면 그 내용이 어느 법령의 몇 조에 있는지 알려 준다.
// 규제 화면의 오른쪽 칸(findPanel)과 규정 원문 화면의 검색 결과(hitLink)가 함께 쓴다. 찾는 일은 js/laws/engine.js가 한다.
import * as data from "../data.js";
import { find, makeIndex, marks, parse, split } from "../laws/engine.js";
import { remember } from "../laws/recent.js";
import { h } from "./dom.js";
import { icon } from "./icons.js";

const PANEL_LIMIT = 5;
let loaded = null;

// 검색에 쓰는 글과 용어집, 법령의 이름. 크므로 처음 찾을 때 한 번만 읽는다.
export function corpus() {
  if (!loaded) {
    loaded = Promise.all([data.lawRows(), data.terms(), data.laws()]).then(([rows, terms, acts]) =>
      ({ rows, index: makeIndex(terms), names: Object.fromEntries(acts.map((act) => [act.id, act.name])) }));
  }
  return loaded;
}

// 안내 문서(가이던스, 질의응답)에서 찾을 때 쓰는 글. 법령의 것보다 크므로 따로 두고, 규정 원문 화면에서 찾을 때만 읽는다.
let guides = null;
export function guideCorpus() {
  if (!guides) guides = Promise.all([data.guideRows(), corpus()]).then(([rows, base]) => ({ ...base, rows }));
  return guides;
}

// 조각의 이름: "제22조 CBAM 인증서의 제출". 국문 이름이 아직 없으면 영문 이름을 쓴다.
export function partName(row) {
  const title = row.k || row.t || "";
  return h("strong", {}, [h("span", { text: row.n }), title ? h("span", { lang: row.k ? null : "en", text: ` ${title}` }) : null]);
}

// 찾은 조문 하나: 누르면 그 조문으로 가고, 찾은 낱말이 칠해져 보인다.
export function hitLink(hit, names, needles) {
  const pieces = split(hit.snippet.text, needles).map(([text, on]) => (on ? h("mark", { text }) : text));
  return h("a", { class: "find-hit", href: `#law-${hit.row.a}.${hit.row.p}`, onclick: () => remember(needles) }, [
    h("span", { class: "find-act", text: names[hit.row.a] || hit.row.a }),
    partName(hit.row),
    hit.snippet.text ? h("span", { class: "find-snip", lang: hit.snippet.lang === "en" ? "en" : null }, pieces) : null,
  ]);
}

// 질문에서 읽어 낸 낱말을 보여 준다(용어집의 낱말이면 원문에서 찾은 영문 표기를 함께 적는다).
export function understood(parsed) {
  return h("p", { class: "find-terms" }, [h("span", { text: "찾은 낱말" }),
    ...parsed.groups.map((group) => h("span", { class: "pill", text: group.en.length && /[가-힣]/.test(group.label) ? `${group.label} · ${group.en[0]}` : group.label }))]);
}

// 오른쪽 칸: 질문을 적는 자리와 답(관련 조문 몇 개).
export function findPanel({ examples = [], lead = "" } = {}) {
  const input = h("input", { type: "search", id: "find-q", placeholder: "예: 인증서는 언제까지 제출하나요", autocomplete: "off" });
  const out = h("div", { class: "find-out", role: "status", "aria-live": "polite" });

  async function ask(query) {
    input.value = query;
    if (!query.trim()) return;
    out.replaceChildren(h("p", { class: "count", text: "규정에서 찾는 중입니다." }));
    const { rows, index, names } = await corpus();
    const parsed = parse(query, index);
    const hits = find(rows, parsed, { limit: PANEL_LIMIT });
    if (!rows.length) return out.replaceChildren(h("p", { class: "find-none", text: "규정의 글을 읽지 못했습니다. 잠시 뒤에 다시 찾아 주세요." }));
    if (!hits.length) return out.replaceChildren(h("p", { class: "find-none", text: "관련된 조문을 찾지 못했습니다. 다른 낱말로 다시 찾아 주세요." }));
    const needles = marks(parsed);
    out.replaceChildren(
      h("p", { class: "find-answer", text: `‘${parsed.groups.map((group) => group.label).join(", ")}’에 관한 내용은 아래 조문에 있습니다.` }),
      h("ol", { class: "find-list" }, hits.map((hit) => h("li", {}, hitLink(hit, names, needles)))),
      h("a", { class: "find-more", href: `#laws-${encodeURIComponent(query.trim())}` }, [h("span", { text: "찾은 조문 모두 보기" }), icon("next", 14)]),
    );
  }

  return h("section", { class: "find-panel", "aria-labelledby": "h-find" }, [
    h("h2", { id: "h-find" }, [icon("search", 17), h("span", { text: "규정에서 찾기" })]),
    h("p", { class: "find-lead", text: lead || "궁금한 내용을 적으면 어느 규정의 몇 조에 있는지 알려 드립니다." }),
    h("form", { class: "find-form", role: "search", onsubmit: (event) => { event.preventDefault(); ask(input.value); } }, [
      h("label", { class: "sr", for: "find-q", text: "찾을 내용" }), input, h("button", { class: "btn", type: "submit", text: "찾기" })]),
    examples.length ? h("p", { class: "find-examples" }, examples.map((text) => h("button", { type: "button", class: "chip", text, onclick: () => ask(text) }))) : null,
    out,
    h("p", { class: "find-note", text: "낱말이 나온 조문의 위치를 찾아 주는 기능입니다. 답은 조문에서 확인해 주세요." }),
  ]);
}
