// 규정 원문의 첫 화면. 전체 규정과 안내 문서(가이던스, 등록부 안내서, 보고서)에서 낱말이나 질문으로 조문을 찾고, 문서를 골라 원문과 국문 번역을 나란히 보는 화면(#law-…)으로 간다.
// #laws-<찾을 말>로 오면 그 말로 찾은 결과를 보여 준다(결과를 주소로 남겨 뒤로 가기와 공유가 되게 한다).
import * as data from "../data.js";
import { find, marks, parse } from "../laws/engine.js";
import { translation, waitLabel } from "../laws/ready.js";
import { band } from "../ui/band.js";
import { empty, fill, h, safeLink } from "../ui/dom.js";
import { count } from "../ui/format.js";
import { icon } from "../ui/icons.js";
import { corpus, guideCorpus, hitLink, understood } from "../ui/lawfind.js";
import { groupTabs } from "../ui/tabs.js";

const LIMIT = 30;
const GUIDE_LIMIT = 15;
const EXAMPLES = ["인증서는 언제까지 제출하나요", "내재배출량 검증", "기본값", "소량 면제", "제3국에서 지불한 탄소가격", "벌칙", "default values"];
// 문서의 갈래: 법령과, EU 집행위원회가 낸 문서 세 갈래(가이던스와 질의응답, 등록부 이용 안내서, 보고서와 안내 자료)
const GROUPS = [
  { key: "act", id: "h-acts", title: "법령", unit: "건",
    lead: "국문은 이 사이트가 옮긴 비공식 번역입니다. 법적 효력은 유럽연합 관보에 실린 원문에 있습니다." },
  { key: "guide", id: "h-guides", title: "가이던스와 질의응답", unit: "건",
    lead: "EU 집행위원회가 낸 안내 문서입니다. 법적 구속력이 없는 설명 자료이고, 국문은 이 사이트가 옮긴 비공식 번역입니다. 원문 PDF와 번역 PDF를 쪽마다 나란히 볼 수 있으며, 식과 그림은 PDF에서 확인해 주세요." },
  { key: "manual", id: "h-manuals", title: "등록부 이용 안내서", unit: "건",
    lead: "CBAM 등록부의 포털에 접근을 신청하고 정보를 입력하는 방법을 EU 집행위원회가 설명한 문서입니다. 화면 그림은 PDF에서 확인해 주세요." },
  { key: "paper", id: "h-papers", title: "보고서와 안내 자료", unit: "건",
    lead: "이행규정을 만들 때의 의견수렴 결과 요약과 EU 집행위원회의 안내 자료입니다. 전환기간(2023년 10월~2025년 12월)에 쓰던 자료는 이름에 적어 두었습니다." },
];
const isAct = (act) => (act.group || "act") === "act";

function facts(act) {
  const annexes = act.annexes ? `부속서 ${count(act.annexes)}개` : "";
  return isAct(act) ? [`조 ${count(act.articles)}개`, annexes] : [act.sections > 1 ? `절 ${count(act.sections)}개` : "", annexes, act.pages ? `${count(act.pages)}쪽` : ""];
}

// 카드에는 알림의 첫 문장만 싣는다(온 글은 문서의 화면에 있다)
function firstSentence(text) {
  const end = text.indexOf(". ");
  return end < 0 ? text : text.slice(0, end + 1);
}

function actCard(act) {
  const state = translation(act.progress);
  const waiting = waitLabel(act.progress);
  return h("article", { class: "law-card" }, [
    h("h3", {}, h("a", { href: `#law-${act.id}`, text: act.name })),
    h("p", { class: "law-official", lang: "en", text: `${act.official}${act.consolidated ? ` (consolidated ${act.consolidated})` : ""}` }),
    act.remark ? h("p", { class: "law-remark", text: firstSentence(act.remark) }) : null,
    act.changes ? h("p", { class: "law-changed" }, h("a", { href: `#changes-${act.id}`, text: `${act.changes.from}과 달라진 곳 ${count(act.changes.rows)}곳 보기` })) : null,
    h("p", { class: "count" }, [h("span", { text: facts(act).filter(Boolean).join(", ") }), waiting ? h("span", { class: "pill law-wait-pill", text: waiting }) : null]),
    h("p", { class: "law-card-links" }, [
      h("a", { class: "btn", href: `#law-${act.id}` }, [icon("file", 15), h("span", { text: state === "none" ? "원문 보기" : "원문과 번역 보기" })]),
      act.rule ? h("a", { href: `#rules-${act.rule}`, text: "진행 상황" }) : null,
      safeLink(act.url, isAct(act) ? "EUR-Lex" : "원문 PDF"),
    ]),
  ]);
}

function group({ key, id, title, unit, lead }, acts) {
  const mine = acts.filter((act) => (act.group || "act") === key);
  if (!mine.length) return null;
  const waiting = mine.filter((act) => translation(act.progress) !== "ready").length;
  return h("section", { class: "stack", "aria-labelledby": id }, [
    h("div", { class: "sec-head" }, [h("h2", { id, text: title }), h("span", { class: "count", text: `${mine.length}${unit}${waiting ? `, 번역 준비 중 ${waiting}${unit}` : ""}` })]),
    h("p", { class: "sec-lead", text: lead }),
    h("div", { class: "law-grid" }, mine.map(actCard)),
  ]);
}

function hitList(title, hits, limit, names, needles) {
  return [
    h("div", { class: "sec-head" }, [h("h2", { text: title }), h("span", { class: "count", text: `${hits.length}건${hits.length === limit ? "(앞선 것만)" : ""}, 관련이 큰 것부터` })]),
    h("ol", { class: "find-list find-wide" }, hits.map((hit) => h("li", {}, hitLink(hit, names, needles)))),
  ];
}

async function results(holder, query) {
  holder.replaceChildren(h("p", { class: "count", text: "규정에서 찾는 중입니다." }));
  const { rows, index, names } = await corpus();
  const parsed = parse(query, index);
  if (!parsed.groups.length || !rows.length) {
    holder.replaceChildren(empty(rows.length ? "관련된 조문을 찾지 못했습니다. 다른 낱말로 다시 찾아 주세요." : "규정의 글을 읽지 못했습니다. 잠시 뒤에 다시 찾아 주세요."));
    return;
  }
  const needles = marks(parsed);
  const hits = find(rows, parsed, { limit: LIMIT });
  const more = h("div", { class: "stack" }, h("p", { class: "count", text: "가이던스와 안내 자료에서 찾는 중입니다." }));
  const jump = h("p", { class: "find-jump" });  // 법령의 결과가 길 때 안내 문서의 결과로 바로 내려가는 링크가 들어간다
  holder.replaceChildren(
    understood(parsed),
    jump,
    ...(hits.length ? hitList("찾은 조문", hits, LIMIT, names, needles) : [h("p", { class: "find-none", text: "법령에서는 관련된 조문을 찾지 못했습니다." })]),
    more,
    h("p", { class: "find-note", text: "용어집의 낱말은 원문의 영문 표기로도 찾습니다. 번역하지 않은 곳은 원문의 문장을 보여 줍니다." }),
  );
  const guides = await guideCorpus();  // 안내 문서의 글은 크므로 법령의 결과를 먼저 보여 주고 나서 읽는다
  const found = find(guides.rows, parsed, { limit: GUIDE_LIMIT });
  if (!hits.length && !found.length) {
    holder.replaceChildren(empty("관련된 내용을 찾지 못했습니다. 다른 낱말로 다시 찾아 주세요."));
    return;
  }
  more.replaceChildren(...(found.length ? hitList("가이던스와 안내 자료에서 찾은 곳", found, GUIDE_LIMIT, names, needles) : []));
  if (found.length && hits.length > 3) {
    jump.replaceChildren(h("button", { type: "button", class: "chip", onclick: () => more.scrollIntoView({ block: "start" }) },
      [h("span", { text: `가이던스와 안내 자료에서 찾은 곳 ${found.length}건 보기` }), icon("next", 14)]));
  }
}

export async function render(main, arg) {
  const acts = await data.laws();
  let query = "";
  try { query = decodeURIComponent(arg || ""); } catch (error) { query = arg || ""; }
  const input = h("input", { id: "law-q", type: "search", value: query, placeholder: "낱말이나 질문을 적어 주세요. 예: 인증서는 언제까지 제출하나요", autocomplete: "off" });
  const go = (text) => { location.hash = text.trim() ? `#laws-${encodeURIComponent(text.trim())}` : "#laws"; };
  const holder = h("div", { class: "stack" });
  fill(main,
    band("규정 원문", "CBAM 규정과 이행·위임규정, EU 집행위원회의 가이던스와 등록부 안내서를 국문 번역과 나란히 봅니다. 낱말이나 질문으로 조문을 찾을 수 있습니다.", groupTabs("laws")),
    acts.length ? null : empty("규정의 글을 읽지 못했습니다. 잠시 뒤에 다시 열어 주세요."),
    h("form", { class: "law-search", role: "search", onsubmit: (event) => { event.preventDefault(); go(input.value); } }, [
      h("label", { class: "sr", for: "law-q", text: "전체 규정에서 찾기" }), icon("search", 20), input, h("button", { class: "btn btn-main", type: "submit", text: "찾기" })]),
    h("p", { class: "find-examples" }, EXAMPLES.map((text) => h("button", { type: "button", class: "chip", text, onclick: () => go(text) }))),
    holder,
    ...GROUPS.map((entry) => group(entry, acts)),
  );
  if (query) await results(holder, query);
  return query ? `‘${query}’ 찾기` : "";
}
