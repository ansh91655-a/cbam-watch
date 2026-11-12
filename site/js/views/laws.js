// 규정 원문의 첫 화면. 전체 규정에서 낱말이나 질문으로 조문을 찾고, 법령을 골라 원문과 국문 번역을 나란히 보는 화면(#law-…)으로 간다.
// #laws-<찾을 말>로 오면 그 말로 찾은 결과를 보여 준다(결과를 주소로 남겨 뒤로 가기와 공유가 되게 한다).
import * as data from "../data.js";
import { find, marks, parse } from "../laws/engine.js";
import { band } from "../ui/band.js";
import { empty, fill, h, safeLink } from "../ui/dom.js";
import { count } from "../ui/format.js";
import { icon } from "../ui/icons.js";
import { corpus, hitLink, understood } from "../ui/lawfind.js";
import { libraryTabs } from "../ui/tabs.js";

const LIMIT = 30;
const EXAMPLES = ["인증서는 언제까지 제출하나요", "내재배출량 검증", "기본값", "소량 면제", "제3국에서 지불한 탄소가격", "벌칙", "default values"];

function percent(progress) {
  return progress.chars ? Math.round((100 * progress.doneChars) / progress.chars) : 100;
}

function actCard(act) {
  const done = percent(act.progress);
  return h("article", { class: "law-card" }, [
    h("h3", {}, h("a", { href: `#law-${act.id}`, text: act.name })),
    h("p", { class: "law-official", lang: "en", text: `${act.official}${act.consolidated ? ` (consolidated ${act.consolidated})` : ""}` }),
    h("p", { class: "count", text: [`조 ${count(act.articles)}개`, act.annexes ? `부속서 ${count(act.annexes)}개` : "", `국문 번역 ${done}%`].filter(Boolean).join(", ") }),
    h("div", { class: "law-progress", role: "img", "aria-label": `국문 번역 ${done}%` }, h("span", { style: `width:${done}%` })),
    h("p", { class: "law-card-links" }, [
      h("a", { class: "btn", href: `#law-${act.id}` }, [icon("file", 15), h("span", { text: "원문과 번역 보기" })]),
      act.rule ? h("a", { href: `#rules-${act.rule}`, text: "진행 상황" }) : null,
      safeLink(act.url, "EUR-Lex"),
    ]),
  ]);
}

async function results(holder, query) {
  holder.replaceChildren(h("p", { class: "count", text: "규정에서 찾는 중입니다." }));
  const { rows, index, names } = await corpus();
  const parsed = parse(query, index);
  const hits = find(rows, parsed, { limit: LIMIT });
  if (!parsed.groups.length || !hits.length) {
    holder.replaceChildren(empty(rows.length ? "관련된 조문을 찾지 못했습니다. 다른 낱말로 다시 찾아 주십시오." : "규정의 글을 읽지 못했습니다. 잠시 뒤에 다시 찾아 주십시오."));
    return;
  }
  const needles = marks(parsed);
  holder.replaceChildren(
    h("div", { class: "sec-head" }, [h("h2", { text: "찾은 조문" }), h("span", { class: "count", text: `${hits.length}건${hits.length === LIMIT ? "(앞선 것만)" : ""}, 관련이 큰 것부터` })]),
    understood(parsed),
    h("ol", { class: "find-list find-wide" }, hits.map((hit) => h("li", {}, hitLink(hit, names, needles)))),
    h("p", { class: "find-note", text: "용어집의 낱말은 원문의 영문 표기로도 찾습니다. 번역하지 않은 조문은 원문의 문장을 보여 줍니다." }),
  );
}

export async function render(main, arg) {
  const acts = await data.laws();
  let query = "";
  try { query = decodeURIComponent(arg || ""); } catch (error) { query = arg || ""; }
  const input = h("input", { id: "law-q", type: "search", value: query, placeholder: "낱말이나 질문을 적어 주십시오. 예: 인증서는 언제까지 제출하나요", autocomplete: "off" });
  const go = (text) => { location.hash = text.trim() ? `#laws-${encodeURIComponent(text.trim())}` : "#laws"; };
  const holder = h("div", { class: "stack" });
  const total = acts.reduce((sum, act) => ({ chars: sum.chars + act.progress.chars, doneChars: sum.doneChars + act.progress.doneChars }), { chars: 0, doneChars: 0 });
  fill(main,
    band("규정 원문", "CBAM 규정과 이행·위임규정의 원문을 국문 번역과 나란히 봅니다. 전체 규정에서 낱말이나 질문으로 조문을 찾을 수 있습니다.", libraryTabs("laws")),
    acts.length ? null : empty("규정의 글을 읽지 못했습니다. 잠시 뒤에 다시 열어 주세요."),
    h("form", { class: "law-search", role: "search", onsubmit: (event) => { event.preventDefault(); go(input.value); } }, [
      h("label", { class: "sr", for: "law-q", text: "전체 규정에서 찾기" }), icon("search", 20), input, h("button", { class: "btn btn-main", type: "submit", text: "찾기" })]),
    h("p", { class: "find-examples" }, EXAMPLES.map((text) => h("button", { type: "button", class: "chip", text, onclick: () => go(text) }))),
    holder,
    h("section", { class: "stack", "aria-labelledby": "h-acts" }, [
      h("div", { class: "sec-head" }, [h("h2", { id: "h-acts", text: "법령" }), h("span", { class: "count", text: `${acts.length}건, 국문 번역 ${percent(total)}%` })]),
      h("p", { class: "sec-lead", text: "국문은 이 사이트가 옮긴 비공식 번역이고, 평일마다 조금씩 더해집니다. 법적 효력은 유럽연합 관보에 실린 원문에 있습니다." }),
      h("div", { class: "law-grid" }, acts.map(actCard)),
    ]),
  );
  if (query) await results(holder, query);
  return query ? `‘${query}’ 찾기` : "";
}
