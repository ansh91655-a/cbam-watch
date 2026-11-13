// 문서 하나(법령이나 EU 집행위원회가 낸 문서)의 원문과 국문 번역을 문단마다 나란히 보는 화면.
// #law-<문서 id>.<조각> 꼴의 주소로 조문이나 절 하나를 바로 가리킬 수 있다.
// 보는 방식은 셋이다: 나란히, 원문만, 국문만. 아직 옮기지 않은 문단은 원문만 보인다.
import * as data from "../data.js";
import { rows as blockRows } from "../laws/blocks.js";
import { recent } from "../laws/recent.js";
import { band } from "../ui/band.js";
import { empty, fill, h, safeLink } from "../ui/dom.js";
import { count } from "../ui/format.js";
import { icon } from "../ui/icons.js";
import { libraryTabs } from "../ui/tabs.js";

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
  guide: "이 문서는 EU 집행위원회가 낸 설명 자료로 법적 구속력이 없습니다. PDF의 글과 표를 옮겨 실었습니다. 식과 그림은 원문 PDF에서 확인해 주십시오.",
  manual: "이 문서는 EU 집행위원회가 낸 등록부 이용 안내서입니다. PDF의 글과 표를 옮겨 실었습니다. 화면 그림은 원문 PDF에서 확인해 주십시오.",
  paper: "이 문서는 EU 집행위원회가 낸 자료로 법적 구속력이 없습니다. PDF의 글과 표를 옮겨 실었습니다. 그림은 원문 PDF에서 확인해 주십시오.",
};
const isAct = (act) => (act.group || "act") === "act";

function note(act, done) {
  const lead = `국문은 이 사이트가 옮긴 비공식 번역입니다(지금 ${done}%).`;
  if (!isAct(act)) return `${lead} ${NATURE[act.group] || NATURE.guide}`;
  return `${lead} 법적 효력은 유럽연합 관보에 실린 원문에 있습니다.${act.consolidated ? " 통합본은 여러 개정을 한데 모은 참고용 문서입니다." : ""}`;
}

function about(act) {
  if (!isAct(act)) return [act.official, act.pages ? `${count(act.pages)}쪽` : "", act.received ? `${act.received}에 받은 판` : ""].filter(Boolean).join(", ");
  return `${act.official}${act.consolidated ? `, ${act.consolidated} 통합본` : ""}`;
}

function heading(part) {
  const english = part.kind === "section" ? part.title : [part.label, part.title].filter(Boolean).join(" · ");  // 절의 번호는 국문 쪽에 이미 있다
  return h("h2", { class: "law-head" }, [
    h("span", { class: "law-no", text: part.ko }),
    part.titleKo ? h("span", { text: part.titleKo }) : null,
    english ? h("span", { class: "law-head-en", lang: "en", text: english }) : null,
  ]);
}

function section(part, target, needles, piece) {
  const here = part.id === target;
  const rows = blockRows(part, here ? needles : []);
  const waiting = part.blocks.length && part.blocks.every(([en, ko]) => !ko);
  if (part.kind === "division") return h("div", { class: "law-division", id: `p-${part.id}` }, heading(part));
  if (FOLDED[part.kind]) {
    return h("details", { class: "law-part law-fold", id: `p-${part.id}`, open: here || null }, [
      h("summary", {}, [h("span", { text: FOLDED[part.kind] }), h("span", { class: "count", text: `문단 ${count(part.blocks.length)}개` })]), ...rows]);
  }
  return h("section", { class: "law-part", id: `p-${part.id}`, "data-here": here ? "" : null, "data-waiting": waiting ? "" : null }, [
    heading(part), waiting ? h("p", { class: "law-wait-note", text: `이 ${piece}은 아직 국문으로 옮기지 않았습니다. 원문만 보입니다.` }) : null, ...rows]);
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

export async function render(main, arg) {
  const [actId, target = ""] = String(arg || "").split(".");
  const [act, acts] = await Promise.all([data.law(actId), data.laws()]);
  if (!act) {
    fill(main, band("규정 원문", "", libraryTabs("laws")), empty("이 문서의 원문을 찾지 못했습니다."), h("p", {}, h("a", { href: "#laws", text: "규정 원문의 목록으로" })));
    return "규정 원문";
  }
  document.body.dataset.wide = "";
  const needles = target ? recent.needles : [];
  const words = isAct(act) ? WORDS.act : WORDS.doc;
  const body = h("div", { class: "law-body", "data-mode": recent.mode }, act.parts.map((part) => section(part, target, needles, words.piece)));
  const buttons = MODES.map(([key, text]) => h("button", { type: "button", text, "aria-pressed": String(key === recent.mode), onclick: () => {
    recent.mode = key;
    body.dataset.mode = key;
    buttons.forEach((button, at) => button.setAttribute("aria-pressed", String(MODES[at][0] === key)));
  } }));
  const done = act.progress.chars ? Math.round((100 * act.progress.doneChars) / act.progress.chars) : 100;
  const picker = h("select", { id: "law-pick", onchange: (event) => { location.hash = `#law-${event.target.value}`; } },
    PICK_GROUPS.map(([key, label]) => h("optgroup", { label }, acts.filter((other) => (other.group || "act") === key)
      .map((other) => h("option", { value: other.id, selected: other.id === act.id || null, text: other.name })))));
  fill(main,
    band(act.name, about(act), libraryTabs("laws")),
    h("div", { class: "law-bar" }, [
      h("p", { class: "crumbs" }, [h("a", { href: "#laws", text: "규정 원문" }), h("span", { text: "›" }), h("span", { text: act.name })]),
      h("div", { class: "law-tools" }, [
        h("label", { class: "field", for: "law-pick" }, [h("span", { text: "문서" }), picker]),
        h("div", { class: "field" }, [h("span", { text: "보는 방식" }), h("div", { class: "seg", role: "group", "aria-label": "보는 방식" }, buttons)]),
      ]),
    ]),
    h("div", { class: "law-note" }, [
      act.remark ? h("p", { class: "law-remark", text: act.remark }) : null,
      h("p", { text: note(act, done) }),
      h("p", { class: "law-note-links" }, [
        safeLink(act.url, words.source),
        act.rule ? h("a", { href: `#rules-${act.rule}`, text: "이 규제의 진행 상황" }) : null,
        h("a", { href: "#laws", text: "전체 규정에서 찾기" }),
      ]),
    ]),
    h("div", { class: "law-layout" }, [contents(act, words.toc), body]),
    h("p", { class: "law-source", text: words.credit }),
  );
  for (const link of main.querySelectorAll(".law-note-links a[target]")) link.append(icon("out", 14));
  if (target) setTimeout(() => { const node = document.getElementById(`p-${target}`); if (node) node.scrollIntoView({ block: "start" }); }, 0);
  return act.name;
}
