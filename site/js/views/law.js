// 문서 하나(법령이나 EU 집행위원회가 낸 문서)의 원문과 국문 번역을 문단마다 나란히 보는 화면.
// #law-<문서 id>.<조각> 꼴의 주소로 조문이나 절 하나를, #law-<문서 id>.<조각>.<몇 번째> 꼴로 문단 하나를 바로 가리킬 수 있다.
// 보는 방식은 셋이다: 나란히, 원문만, 국문만. 실린 번역이 없는 문단은 원문만 보이고 번역 자리에 '번역 준비 중'이라고 적힌다(퍼센트는 보여 주지 않는다).
// 문단과 조각마다 '인용 복사'가 있다: 원문, 국문, 출처(문서·조·쪽), 주소를 한 번에 복사한다(laws/cite.js).
import * as data from "../data.js";
import { rowId, rows as blockRows } from "../laws/blocks.js";
import { citeBlock, citePart } from "../laws/cite.js";
import { translation } from "../laws/ready.js";
import { recent } from "../laws/recent.js";
import { dutyHref, linkedTo, tally, termHref } from "../laws/refs.js";
import { band } from "../ui/band.js";
import { copyText } from "../ui/copy.js";
import { empty, fill, h, safeLink } from "../ui/dom.js";
import { count, day } from "../ui/format.js";
import { icon } from "../ui/icons.js";
import { groupTabs } from "../ui/tabs.js";

const MODES = [["both", "나란히"], ["en", "원문"], ["ko", "국문"]];
const FOLDED = { front: "제목과 근거", recitals: "전문", closing: "맺음", notes: "각주", cover: "표지와 일러두기" };  // 접어 두는 조각
// 갈래마다 다른 말: 법령과, EU 집행위원회가 낸 문서(가이던스와 질의응답, 등록부 이용 안내서, 보고서와 안내 자료)
const WORDS = {
  act: { piece: "조문", toc: "이 법령의 차례", source: "EUR-Lex에서 원문 보기",
    credit: "원문: © European Union, EUR-Lex. 출처를 밝히고 재이용합니다. 번역: 이 사이트(용어집의 표기를 따릅니다)." },
  doc: { piece: "부분", toc: "이 문서의 차례", source: "원문 PDF 보기",
    credit: "원문: © European Union, EU 집행위원회 조세·관세동맹 총국. 출처를 밝히고 재이용합니다. 번역: 이 사이트(용어집의 표기를 따릅니다)." },
};
const PICK_GROUPS = [["act", "법령"], ["guide", "가이던스와 질의응답"], ["manual", "등록부 이용 안내서"], ["paper", "보고서와 안내 자료"]];
// 문서의 성격을 알리는 말(갈래마다)
const NATURE = {
  guide: "이 문서는 EU 집행위원회가 낸 설명 자료로 법적 구속력이 없습니다. PDF의 글과 표를 옮겨 실었습니다. 식과 그림은 원문 PDF에서 확인해 주세요.",
  manual: "이 문서는 EU 집행위원회가 낸 등록부 이용 안내서입니다. PDF의 글과 표를 옮겨 실었습니다. 화면 그림은 원문 PDF에서 확인해 주세요.",
  paper: "이 문서는 EU 집행위원회가 낸 자료로 법적 구속력이 없습니다. PDF의 글과 표를 옮겨 실었습니다. 그림은 원문 PDF에서 확인해 주세요.",
};
const BACK_MS = 2000;    // 복사했다는 표시를 되돌리는 시간
const FLASH_MS = 2600;   // 주소로 가리킨 문단을 표시해 두는 시간
const isAct = (act) => (act.group || "act") === "act";

// 번역이 준비된 정도에 따라 머리의 안내가 달라진다(퍼센트는 적지 않는다)
const LEADS = {
  ready: "국문은 이 사이트가 옮긴 비공식 번역입니다.",
  partial: "국문은 이 사이트가 옮긴 비공식 번역입니다. 검수를 마친 번역만 싣고, 아직 준비하지 못한 문단은 ‘번역 준비 중’으로 표시합니다.",
  none: "이 문서의 국문 번역은 준비 중입니다. 지금은 원문만 실려 있습니다.",
};

function note(act, state) {
  const lead = LEADS[state];
  if (!isAct(act)) return `${lead} ${NATURE[act.group] || NATURE.guide}`;
  return `${lead} 법적 효력은 유럽연합 관보에 실린 원문에 있습니다.${act.consolidated ? " 통합본은 여러 개정을 한데 모은 참고용 문서입니다." : ""}`;
}

function about(act) {
  if (!isAct(act)) return [act.official, act.pages ? `${count(act.pages)}쪽` : "", act.received ? `${act.received}에 받은 판` : ""].filter(Boolean).join(", ");
  return `${act.official}${act.consolidated ? `, ${act.consolidated} 통합본` : ""}`;
}

// 조각의 머리: 이름, 그리고 오른쪽의 도구(PDF의 그 쪽으로 가는 링크, 인용 복사).
// paged는 이 문서를 PDF로 나란히 볼 수 있을 때의 문서 id다. citable이면 조각을 통째로 인용하는 단추를 단다
function heading(part, paged, citable) {
  const english = part.kind === "section" ? part.title : [part.label, part.title].filter(Boolean).join(" · ");  // 절의 번호는 국문 쪽에 이미 있다
  const name = h("h2", { class: "law-head" }, [
    h("span", { class: "law-no", text: part.ko }),
    part.titleKo ? h("span", { text: part.titleKo }) : null,
    english ? h("span", { class: "law-head-en", lang: "en", text: english }) : null,
  ]);
  const tools = [
    paged && part.page ? h("a", { class: "law-page", href: `#pdf-${paged}.p${part.page}`, text: `PDF ${count(part.page)}쪽`, title: "이 부분을 원문과 번역 PDF로 나란히 보기" }) : null,
    citable ? h("button", { class: "law-cite-part", type: "button", "data-cite": part.id, title: "이 부분의 원문과 국문, 출처, 주소를 복사합니다" }, [icon("copy", 14), h("span", { text: "인용 복사" })]) : null,
  ].filter(Boolean);
  return tools.length ? h("div", { class: "law-top" }, [name, h("div", { class: "law-head-tools" }, tools)]) : name;
}

// 문단의 줄 끝에 다는 단추: 그 문단을 인용하는 글을 복사한다. 자판의 차례에는 넣지 않는다(문단마다 멈추면 화면을 다니기 어렵다).
// 자판으로는 조각 머리의 '인용 복사'를 쓴다.
function citeTool(part) {
  return (at) => h("button", { class: "law-cite", type: "button", tabindex: "-1", "data-cite": `${part.id}.${at}`, "aria-label": "이 문단 인용 복사", title: "이 문단의 원문과 국문, 출처, 주소를 복사합니다" }, icon("copy", 14));
}

// 받아 둘 때 뒷부분을 뺀 부속서(값의 표가 아주 긴 것)의 끝에 다는 알림. 뺀 줄 수와 전체를 볼 수 있는 곳을 알린다.
function cutNote(part, source) {
  if (!part.cut) return null;
  const link = safeLink(source, "EUR-Lex의 원문");
  if (link) link.append(icon("out", 13));
  return h("p", { class: "law-cut-note" }, [
    h("span", { text: `이 부속서의 글은 앞부분만 실었습니다. 뒤의 ${count(part.cut)}줄은 싣지 않았습니다. 전체는 ` }), link || h("span", { text: "EUR-Lex의 원문" }), h("span", { text: "에서 확인하세요." }),
  ]);
}

// 이 조각에 이어진 것(접어 둔다): 이 조를 풀어 쓴 해설서의 절, 이 조가 근거인 의무 일정, 이 조를 적은 소식, 이 조에서 나온 용어.
// 글에 법령과 조문이 또렷이 적힌 것만 이어져 있다(laws/refs.js). row가 없으면 null.
function linkedBlock(row, name) {
  if (!row) return null;
  const itemLink = (item) => {
    if (!item.link) return h("a", { href: `#item-${item.id}`, text: item.title });
    const link = safeLink(item.link, item.title);   // 제목만 실은 소식은 원문으로 바로 간다
    if (link) link.append(icon("out", 13));
    return link || h("span", { text: item.title });
  };
  const dated = (date, link) => h("li", {}, [h("time", { datetime: date, text: day(date) }), link]);
  return h("details", { class: "law-linked" }, [
    h("summary", {}, [h("span", { text: name }), h("span", { class: "count", text: tally(row) })]),
    row.handbook.length ? h("div", { class: "law-linked-row" }, [h("b", { text: "해설서" }),
      h("ul", {}, row.handbook.map((one) => h("li", {}, [h("span", { class: "count", text: one.chapter }), h("a", { href: one.href, text: one.title })])))]) : null,
    row.duties.length ? h("div", { class: "law-linked-row" }, [h("b", { text: "의무 일정" }),
      h("ul", {}, row.duties.map((duty) => dated(duty.date, h("a", { href: dutyHref(duty), text: duty.title }))))]) : null,
    row.items.length ? h("div", { class: "law-linked-row" }, [h("b", { text: "소식" }),
      h("ul", {}, [...row.items.map((item) => dated(item.date, itemLink(item))), row.more ? h("li", { class: "count", text: `이 밖에 ${count(row.more)}건이 더 있습니다.` }) : null])]) : null,
    row.terms.length ? h("div", { class: "law-linked-row" }, [h("b", { text: "용어" }),
      h("p", { class: "law-linked-terms" }, row.terms.map((term) => h("a", { href: termHref(term), text: term.ko || term.en })))]) : null,
  ]);
}

const LINKED_NAMES = { article: "이 조와 이어진 내용", annex: "이 부속서와 이어진 내용" };

// 법령의 수식은 원문에 그림으로 실려 있어 받아 둔 글에는 번호만 남는다. 그런 조각의 머리에 원문에서 보라고 알린다.
function formulaNote(part, source) {
  if (!part.formulas) return null;
  const link = safeLink(source, "EUR-Lex의 원문");
  if (link) link.append(icon("out", 13));
  return h("p", { class: "law-cut-note" }, [
    h("span", { text: `이 ${part.kind === "annex" ? "부속서" : "부분"}의 수식 ${count(part.formulas)}개는 원문에 그림으로 실려 있어, 여기에는 식의 번호((Equation 4) 같은 줄)만 보입니다. 식은 ` }),
    link || h("span", { text: "EUR-Lex의 원문" }), h("span", { text: "에서 확인하세요." }),
  ]);
}

function section(part, target, needles, piece, paged, source, linked) {
  const here = part.id === target;
  const rows = blockRows(part, here ? needles : [], citeTool(part));
  const missing = part.blocks.filter(([en, ko]) => !ko).length;
  const waiting = part.blocks.length && missing === part.blocks.length;
  const some = missing > 0 && !waiting;
  if (part.kind === "division") return h("div", { class: "law-division", id: `p-${part.id}` }, heading(part));
  if (FOLDED[part.kind]) {
    // 접어 둔 조각에는 머리가 없다. 펼친 안쪽에 조각을 통째로 인용하는 단추를 둔다(문단의 단추는 자판의 차례에 없다)
    const citeAll = part.blocks.length ? h("div", { class: "law-head-tools law-fold-tools" },
      h("button", { class: "law-cite-part", type: "button", "data-cite": part.id, title: "이 부분의 원문과 국문, 출처, 주소를 복사합니다" }, [icon("copy", 14), h("span", { text: "인용 복사" })])) : null;
    return h("details", { class: "law-part law-fold", id: `p-${part.id}`, open: here || null }, [
      h("summary", {}, [h("span", { text: FOLDED[part.kind] }), h("span", { class: "count", text: `문단 ${count(part.blocks.length)}개` })]), citeAll, ...rows]);
  }
  return h("section", { class: "law-part", id: `p-${part.id}`, "data-here": here ? "" : null, "data-waiting": waiting ? "" : null }, [
    heading(part, paged, part.blocks.length > 0),
    waiting ? h("p", { class: "law-wait-note", text: `이 ${piece}의 국문 번역은 준비 중입니다. 원문만 보입니다.` }) : null,
    some ? h("p", { class: "law-wait-note", text: `이 ${piece}의 일부 문단은 번역 준비 중입니다. 그 문단은 원문만 보입니다.` }) : null,
    formulaNote(part, source), ...rows,
    cutNote(part, source), linkedBlock(linked, LINKED_NAMES[part.kind] || "이 부분과 이어진 내용")]);
}

function jump(event, id, href) {
  event.preventDefault();
  const node = document.getElementById(`p-${id}`);
  if (!node) return;
  if (node.tagName === "DETAILS") node.open = true;
  node.scrollIntoView({ block: "start" });
  history.replaceState(null, "", href);  // 주소만 바꾼다(화면을 다시 그리지 않는다)
}

function contents(act, label) {
  return h("nav", { class: "law-toc", "aria-label": label }, h("ul", {}, act.parts.map((part) => {
    const name = part.kind in FOLDED ? FOLDED[part.kind] : [part.ko, part.titleKo || ""].filter(Boolean).join(" ");
    const href = `#law-${act.id}.${part.id}`;
    return h("li", { "data-kind": part.kind, "data-level": part.level || null }, h("a", { href, onclick: (event) => jump(event, part.id, href) }, [
      h("span", { text: name }), !part.titleKo && part.title && !(part.kind in FOLDED) ? h("span", { class: "law-toc-en", lang: "en", text: part.title }) : null]));
  })));
}

// 인용 복사: 본문 안의 단추(data-cite가 "<조각>"이면 조각 전체, "<조각>.<차례>"이면 문단 하나)를 한곳에서 듣는다.
function wireCite(body, act, said) {
  const base = `${location.origin}${location.pathname}`;
  body.addEventListener("click", async (event) => {
    const button = event.target instanceof Element ? event.target.closest("[data-cite]") : null;
    if (!button) return;
    const [partId, at] = button.dataset.cite.split(".");
    const part = act.parts.find((one) => one.id === partId);
    if (!part) return;
    const done = await copyText(at === undefined ? citePart(act, part, base) : citeBlock(act, part, Number(at), base));
    said.textContent = done ? "인용할 글을 복사했습니다." : "복사하지 못했습니다.";
    button.dataset.state = done ? "done" : "failed";
    const words = button.querySelector("span");
    if (words) words.textContent = done ? "복사했습니다" : "복사하지 못했습니다";
    setTimeout(() => {
      delete button.dataset.state;
      if (words) words.textContent = "인용 복사";
      said.textContent = "";
    }, BACK_MS);
  });
}

// 주소가 가리킨 조각이나 문단으로 옮겨 간다. 문단이면 잠깐 표시한다.
function reach(target, at) {
  const part = document.getElementById(`p-${target}`);
  if (!part) return;
  if (part.tagName === "DETAILS") part.open = true;
  const row = /^\d+$/.test(at) ? document.getElementById(rowId(target, Number(at) - 1)) : null;
  (row || part).scrollIntoView({ block: row ? "center" : "start" });
  if (!row) return;
  row.dataset.flash = "true";
  setTimeout(() => { delete row.dataset.flash; }, FLASH_MS);
}

export async function render(main, arg) {
  const [actId, target = "", at = ""] = String(arg || "").split(".");
  const [act, acts, pdfs, refs] = await Promise.all([data.law(actId), data.laws(), data.pdfs(), data.refs()]);
  if (!act) {
    fill(main, band("규정 원문", "", groupTabs("laws")), empty("이 문서의 원문을 찾지 못했습니다."), h("p", {}, h("a", { href: "#laws", text: "규정 원문의 목록으로" })));
    return "규정 원문";
  }
  document.body.dataset.wide = "";
  const needles = target ? recent.needles : [];
  const words = isAct(act) ? WORDS.act : WORDS.doc;
  const state = translation(act.progress);
  const mode = state === "none" ? "en" : recent.mode;   // 실린 번역이 없으면 원문만 본다(보는 방식을 고르는 단추도 두지 않는다)
  const body = h("div", { class: "law-body", "data-mode": mode }, act.parts.map((part) => section(part, target, needles, words.piece, pdfs[act.id] ? act.id : "", act.url, linkedTo(refs, act.id, part.id))));
  const said = h("p", { class: "sr", role: "status", "aria-live": "polite" });  // 복사했는지를 화면 낭독기에 알린다
  wireCite(body, act, said);
  const buttons = MODES.map(([key, text]) => h("button", { type: "button", text, "aria-pressed": String(key === mode), onclick: () => {
    recent.mode = key;
    body.dataset.mode = key;
    buttons.forEach((button, index) => button.setAttribute("aria-pressed", String(MODES[index][0] === key)));
  } }));
  const picker = h("select", { id: "law-pick", onchange: (event) => { location.hash = `#law-${event.target.value}`; } },
    PICK_GROUPS.map(([key, label]) => h("optgroup", { label }, acts.filter((other) => (other.group || "act") === key)
      .map((other) => h("option", { value: other.id, selected: other.id === act.id || null, text: other.name })))));
  const changed = act.changes && act.changes.rows ? h("a", { href: `#changes-${act.id}`, text: `앞선 판과 달라진 곳 ${count(act.changes.rows)}곳 보기` }) : null;
  fill(main,
    band(act.name, about(act), groupTabs("laws")),
    h("div", { class: "law-bar" }, [
      h("p", { class: "crumbs" }, [h("a", { href: "#laws", text: "규정 원문" }), h("span", { text: "›" }), h("span", { text: act.name })]),
      h("div", { class: "law-tools" }, [
        h("label", { class: "field", for: "law-pick" }, [h("span", { text: "문서" }), picker]),
        state === "none" ? null : h("div", { class: "field" }, [h("span", { text: "보는 방식" }), h("div", { class: "seg", role: "group", "aria-label": "보는 방식" }, buttons)]),
      ]),
    ]),
    h("div", { class: "law-note" }, [
      act.remark ? h("p", { class: "law-remark", text: act.remark }) : null,
      h("p", { text: note(act, state) }),
      h("p", { class: "law-note-links" }, [
        pdfs[act.id] ? h("a", { href: `#pdf-${act.id}`, text: "원문과 번역을 PDF로 나란히 보기" }) : null,
        changed,
        safeLink(act.url, words.source),
        act.rule ? h("a", { href: `#rules-${act.rule}`, text: "이 규제의 진행 상황" }) : null,
        h("a", { href: "#laws", text: "전체 규정에서 찾기" }),
      ]),
      linkedBlock(linkedTo(refs, act.id), "이 문서와 이어진 내용"),
      h("p", { class: "law-cite-tip", text: `문단 오른쪽의 복사 표시나 ${words.piece} 머리의 ‘인용 복사’를 누르면 원문과 국문, 출처, 주소가 함께 복사됩니다.` }),
    ]),
    h("div", { class: "law-layout" }, [contents(act, words.toc), body]),
    said,
    h("p", { class: "law-source", text: words.credit }),
  );
  for (const link of main.querySelectorAll(".law-note-links a[target]")) link.append(icon("out", 14));
  if (target) setTimeout(() => reach(target, at), 0);
  return act.name;
}
