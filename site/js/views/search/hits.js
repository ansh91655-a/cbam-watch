// 검색 결과의 한 줄. 갈래마다 무엇을 보여 주고 어디로 보낼지를 여기에서 정한다.
// 줄의 꼴은 모두 같다: 위에 작은 글(날짜, 갈래), 이름, 낱말이 나온 문장. 찾은 낱말은 칠해 보인다.
// 소식의 출처 이름은 보여 주지 않는다.
import { SECTOR } from "../../cn/names.js";
import { dateOf } from "../../data.js";
import { split } from "../../laws/engine.js";
import { remember } from "../../laws/recent.js";
import { h, safeLink } from "../../ui/dom.js";
import { count, koreanDate } from "../../ui/format.js";
import { icon } from "../../ui/icons.js";
import { hasPage } from "../../ui/itemlink.js";
import { eventId } from "../../ui/monthgrid.js";
import { topicName, topicOf } from "../../ui/topics.js";

// 규정 원문의 문서 갈래 이름(views/laws.js의 구역 이름과 같다)
const LAW_GROUP = { act: "법령", guide: "가이던스와 질의응답", manual: "등록부 이용 안내서", paper: "보고서와 안내 자료" };

// 글에서 찾은 낱말을 칠한다.
function marked(text, needles) {
  return split(text, needles).map(([piece, on]) => (on ? h("mark", { text: piece }) : piece));
}

const facts = (values) => h("span", { class: "hit-meta" }, values.filter(Boolean).map((value) => (typeof value === "string" ? h("span", { text: value }) : value)));
const name = (children, attrs = {}) => h("strong", { class: "hit-name", ...attrs }, children);
const text = (value, needles, attrs = {}) => (value ? h("span", { class: "hit-text", ...attrs }, marked(value, needles)) : null);

// 낱말이 나온 문장. 본문에 나오지 않고 이름에만 나왔으면 대신 보여 줄 글(fallback)을 쓴다.
function passage(hit, needles, fallback) {
  const found = hit.snippet && hit.snippet.text;
  return text(found || fallback || "", needles);
}

function inside(href, children, attrs = {}) {
  return h("a", { class: "search-hit", href, ...attrs }, children);
}

function newsHit(hit, { needles }) {
  const item = hit.row.ref;
  // 낱말이 붙인 주제어에서만 나왔으면 주제어 줄 대신 요약을 보여 준다
  const found = String((hit.snippet && hit.snippet.text) || "").replace(/^… | …$/g, "");
  const tagsOnly = Boolean(found) && (item.topics || []).join(", ").includes(found);
  const summary = item.withdrawn ? "" : item.summary;
  const children = [
    facts([koreanDate(dateOf(item)), topicName(topicOf(item))]),
    name(marked(item.title, needles)),
    tagsOnly ? text(summary, needles) : passage(hit, needles, summary),
  ];
  if (hasPage(item)) return inside(`#item-${item.id}`, children);
  // 제목이 곧 내용인 한 줄 소식은 원문으로 바로 간다(바깥으로 나간다는 표시를 붙인다)
  const link = safeLink(item.link, "", { class: "search-hit" });
  if (!link) return h("div", { class: "search-hit" }, children);
  children[1].append(icon("out", 14), h("span", { class: "sr", text: " (원문이 새 창에서 열립니다)" }));
  link.append(...children.filter(Boolean));
  return link;
}

function ruleHit(hit, { needles, ruleGroups }) {
  const rule = hit.row.ref;
  return inside(`#rules-${rule.id}`, [
    facts([ruleGroups.get(rule.group), rule.stage]),
    name([...marked(rule.name, needles), rule.official ? h("span", { class: "hit-alt", lang: "en" }, marked(rule.official, needles)) : null]),
    passage(hit, needles, rule.summary),
  ]);
}

function termHit(hit, { needles }) {
  const term = hit.row.ref;
  return inside(`#terms-${encodeURIComponent(term.en || term.ko)}`, [
    facts([term.category]),
    name([...marked(term.ko, needles), h("span", { class: "hit-alt", lang: "en" }, marked([term.en, term.abbr ? `(${term.abbr})` : ""].filter(Boolean).join(" "), needles))]),
    text([term.alt ? `달리 쓰는 표기: ${term.alt}.` : "", term.note || ""].filter(Boolean).join(" "), needles),
  ]);
}

function dateHit(hit, { needles }) {
  const one = hit.row.ref;
  const duty = hit.row.form === "duty";
  const year = String(one.date).slice(0, 4);
  return inside(`#calendar-${year}.${duty ? `duty-${one.id}` : eventId(one)}`, [
    facts([koreanDate(one.date), duty ? "의무 일정" : one.kind, duty ? one.schemeName : ""]),
    name(marked(one.title, needles)),
    passage(hit, needles, duty ? one.text : one.note),
  ]);
}

function codeHit(hit, { needles }) {
  const entry = hit.row.ref;
  return inside(`#cn-${entry.codes[0]}`, [
    facts([SECTOR[entry.sector] || entry.sector, hit.row.form === "proposed" ? "확대 개정안의 품목" : "부속서 I의 품목"]),
    name([h("span", { class: "hit-code", text: entry.shown }), h("span", { lang: "en" }, marked(entry.text, needles))]),
  ]);
}

function fileHit(hit, { needles, actNames }) {
  const doc = hit.row.ref;
  return inside(`#docs-${encodeURIComponent(doc.title)}`, [
    facts([doc.format, doc.pages ? `${count(doc.pages)}쪽` : "", doc.date ? `${doc.date} 기준` : ""]),
    name(marked(doc.title, needles), { lang: "en" }),
    text(actNames[hit.row.act] || "", needles),
  ]);
}

// 해설서의 절 하나. 누르면 그 장을 열고 그 절로 간다.
function bookHit(hit, { needles }) {
  const section = hit.row.ref;
  return inside(`#handbook-${section.chapter}.${section.id}`, [
    facts([`해설서 ${section.chapterNo}장`, section.chapterTitle]),
    name(marked(section.title, needles)),
    passage(hit, needles, (section.body || [])[0]),
  ]);
}

// 규정 원문의 문서(법령, 가이던스) 하나
function lawHit(hit, { needles }) {
  const act = hit.row.ref;
  const done = act.progress && act.progress.chars ? Math.round((100 * act.progress.doneChars) / act.progress.chars) : null;
  return inside(`#law-${act.id}`, [
    facts([LAW_GROUP[act.group || "act"], done === null ? "" : `국문 번역 ${done}%`]),
    name(marked(act.name, needles)),
    text(act.official || "", needles, { lang: "en" }),
  ]);
}

// 규정 원문의 조문이나 절 하나. 누르면 그 자리로 가고, 찾은 낱말이 칠해져 보인다.
function partHit(hit, { needles, actNames }) {
  const row = hit.row;
  const title = row.k || row.t || "";
  return inside(`#law-${row.a}.${row.p}`, [
    facts([actNames[row.a] || row.a]),
    name([h("span", { text: row.n }), title ? h("span", { lang: row.k ? null : "en" }, marked(` ${title}`, needles)) : null]),
    hit.snippet.text ? text(hit.snippet.text, needles, { lang: hit.snippet.lang === "en" ? "en" : null }) : null,
  ], { onclick: () => remember(needles) });
}

const DRAW = { news: newsHit, rules: ruleHit, terms: termHit, book: bookHit, dates: dateHit, codes: codeHit, files: fileHit, laws: lawHit, acts: partHit, guides: partHit };

// 찾은 것 하나를 그린다. kind는 갈래(js/search/find.js의 KINDS와 조문의 acts, guides).
export function hitNode(kind, hit, context) {
  return DRAW[kind](hit, context);
}
