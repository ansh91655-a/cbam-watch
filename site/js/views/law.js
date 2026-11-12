// 법령 하나의 원문과 국문 번역을 문단마다 나란히 보는 화면. #law-<법령 번호>.<조각> 꼴의 주소로 조문 하나를 바로 가리킬 수 있다.
// 보는 방식은 셋이다: 나란히, 원문만, 국문만. 아직 옮기지 않은 문단은 원문만 보인다.
import * as data from "../data.js";
import { split } from "../laws/engine.js";
import { recent } from "../laws/recent.js";
import { band } from "../ui/band.js";
import { empty, fill, h, safeLink } from "../ui/dom.js";
import { count } from "../ui/format.js";
import { icon } from "../ui/icons.js";
import { libraryTabs } from "../ui/tabs.js";

const MODES = [["both", "나란히"], ["en", "원문"], ["ko", "국문"]];
const FOLDED = { front: "제목과 근거", recitals: "전문", closing: "맺음", notes: "각주" };  // 접어 두는 조각

function marked(text, needles) {
  return needles.length ? split(text, needles).map(([piece, on]) => (on ? h("mark", { text: piece }) : piece)) : text;
}

function row([en, ko], needles) {
  return h("div", { class: "law-row", "data-wait": ko ? null : "" }, [
    h("p", { class: "law-en", lang: "en" }, marked(en, needles)),
    ko ? h("p", { class: "law-ko" }, marked(ko, needles)) : h("p", { class: "law-ko law-wait", "aria-hidden": "true" }),
  ]);
}

function heading(part) {
  const english = [part.label, part.title].filter(Boolean).join(" · ");
  return h("h2", { class: "law-head" }, [
    h("span", { class: "law-no", text: part.ko }),
    part.titleKo ? h("span", { text: part.titleKo }) : null,
    english ? h("span", { class: "law-head-en", lang: "en", text: english }) : null,
  ]);
}

function section(part, target, needles) {
  const here = part.id === target;
  const rows = part.blocks.map((block) => row(block, here ? needles : []));
  const waiting = part.blocks.length && part.blocks.every(([en, ko]) => !ko);
  if (part.kind === "division") return h("div", { class: "law-division", id: `p-${part.id}` }, heading(part));
  if (FOLDED[part.kind]) {
    return h("details", { class: "law-part law-fold", id: `p-${part.id}`, open: here || null }, [
      h("summary", {}, [h("span", { text: FOLDED[part.kind] }), h("span", { class: "count", text: `문단 ${count(part.blocks.length)}개` })]), ...rows]);
  }
  return h("section", { class: "law-part", id: `p-${part.id}`, "data-here": here ? "" : null, "data-waiting": waiting ? "" : null }, [
    heading(part), waiting ? h("p", { class: "law-wait-note", text: "이 조문은 아직 국문으로 옮기지 않았습니다. 원문만 보입니다." }) : null, ...rows]);
}

function jump(event, id, href) {
  event.preventDefault();
  const node = document.getElementById(`p-${id}`);
  if (!node) return;
  if (node.tagName === "DETAILS") node.open = true;
  node.scrollIntoView({ block: "start" });
  history.replaceState(null, "", href);  // 주소만 바꾼다(화면을 다시 그리지 않는다)
}

function contents(act) {
  return h("nav", { class: "law-toc", "aria-label": "이 법령의 차례" }, h("ul", {}, act.parts.map((part) => {
    const name = part.kind in FOLDED ? FOLDED[part.kind] : [part.ko, part.titleKo || ""].filter(Boolean).join(" ");
    const href = `#law-${act.id}.${part.id}`;
    return h("li", { "data-kind": part.kind }, h("a", { href, onclick: (event) => jump(event, part.id, href) }, [
      h("span", { text: name }), !part.titleKo && part.title && !(part.kind in FOLDED) ? h("span", { class: "law-toc-en", lang: "en", text: part.title }) : null]));
  })));
}

export async function render(main, arg) {
  const [actId, target = ""] = String(arg || "").split(".");
  const [act, acts] = await Promise.all([data.law(actId), data.laws()]);
  if (!act) {
    fill(main, band("규정 원문", "", libraryTabs("laws")), empty("이 법령의 원문을 찾지 못했습니다."), h("p", {}, h("a", { href: "#laws", text: "규정 원문의 목록으로" })));
    return "규정 원문";
  }
  document.body.dataset.wide = "";
  const needles = target ? recent.needles : [];
  const body = h("div", { class: "law-body", "data-mode": recent.mode }, act.parts.map((part) => section(part, target, needles)));
  const buttons = MODES.map(([key, text]) => h("button", { type: "button", text, "aria-pressed": String(key === recent.mode), onclick: () => {
    recent.mode = key;
    body.dataset.mode = key;
    buttons.forEach((button, at) => button.setAttribute("aria-pressed", String(MODES[at][0] === key)));
  } }));
  const done = act.progress.chars ? Math.round((100 * act.progress.doneChars) / act.progress.chars) : 100;
  const picker = h("select", { id: "law-pick", onchange: (event) => { location.hash = `#law-${event.target.value}`; } },
    acts.map((other) => h("option", { value: other.id, selected: other.id === act.id || null, text: other.name })));
  fill(main,
    band(act.name, `${act.official}${act.consolidated ? `, ${act.consolidated} 통합본` : ""}`, libraryTabs("laws")),
    h("div", { class: "law-bar" }, [
      h("p", { class: "crumbs" }, [h("a", { href: "#laws", text: "규정 원문" }), h("span", { text: "›" }), h("span", { text: act.name })]),
      h("div", { class: "law-tools" }, [
        h("label", { class: "field", for: "law-pick" }, [h("span", { text: "법령" }), picker]),
        h("div", { class: "field" }, [h("span", { text: "보는 방식" }), h("div", { class: "seg", role: "group", "aria-label": "보는 방식" }, buttons)]),
      ]),
    ]),
    h("div", { class: "law-note" }, [
      h("p", { text: `국문은 이 사이트가 옮긴 비공식 번역입니다(지금 ${done}%). 법적 효력은 유럽연합 관보에 실린 원문에 있습니다.${act.consolidated ? " 통합본은 여러 개정을 한데 모은 참고용 문서입니다." : ""}` }),
      h("p", { class: "law-note-links" }, [
        safeLink(act.url, "EUR-Lex에서 원문 보기"),
        act.rule ? h("a", { href: `#rules-${act.rule}`, text: "이 규제의 진행 상황" }) : null,
        h("a", { href: "#laws", text: "전체 규정에서 찾기" }),
      ]),
    ]),
    h("div", { class: "law-layout" }, [contents(act), body]),
    h("p", { class: "law-source", text: "원문: © European Union, EUR-Lex. 출처를 밝히고 재이용합니다. 번역: 이 사이트(용어집의 표기를 따릅니다)." }),
  );
  for (const link of main.querySelectorAll(".law-note-links a[target]")) link.append(icon("out", 14));
  if (target) setTimeout(() => { const node = document.getElementById(`p-${target}`); if (node) node.scrollIntoView({ block: "start" }); }, 0);
  return act.name;
}
