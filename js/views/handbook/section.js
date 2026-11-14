// 해설서의 절 하나. 왼쪽에 글(문단, 그림, 목록, 식, 표), 오른쪽에 곁들이는 것(용어 풀이, 알아 둘 점, 근거 조문, 관련 화면)을 둔다.
// 좁은 화면에서는 곁들이는 것이 글 아래로 내려간다(css/handbook.css).
import { lawHref } from "../../laws/refs.js";
import { h, safeLink, table } from "../../ui/dom.js";
import { gloss } from "../../ui/gloss.js";
import { icon } from "../../ui/icons.js";
import { stackable } from "../../ui/stack.js";
import { figureNode } from "./figure.js";
import { formulaLine } from "./figures/equation.js";

const list = (section) => (section.list ? h(section.ordered ? "ol" : "ul", { class: "hb-list" }, section.list.map((text) => h("li", { text }))) : null);

function formula(one) {
  if (!one) return null;
  return h("div", { class: "hb-formula" }, [
    formulaLine(one.text, (one.parts || []).map(([word]) => word)),
    one.parts && one.parts.length ? h("dl", { class: "hb-formula-parts" }, one.parts.flatMap(([word, text]) => [h("dt", { text: word }), h("dd", { text })])) : null,
  ]);
}

const LONG_CELL = 22;   // 칸의 글이 이보다 길면 긴 글로 본다

// 칸이 셋 이상이고 긴 글이 든 표는 좁은 화면에서 줄마다 한 칸으로 쌓는다(칸이 좁아져 낱말이 글자마다 꺾이지 않게). 짧은 값의 표는 그대로 둔다.
function sheet(one, name) {
  if (!one) return null;
  const node = table(one.head, one.rows.map((cells) => h("tr", {}, cells.map((cell, at) => (at === 0 ? h("th", { scope: "row", text: cell }) : h("td", { text: cell }))))), `${name} 표`);
  const crowded = one.head.length >= 3 && one.rows.some((cells) => cells.slice(1).some((cell) => String(cell).length > LONG_CELL));
  return crowded ? stackable(node) : node;
}

function terms(section) {
  if (!section.terms || !section.terms.length) return null;
  return h("dl", { class: "hb-terms" }, section.terms.flatMap((term) => [
    h("dt", {}, [h("span", { text: term.ko }), h("small", { lang: "en", text: [term.en, term.abbr].filter(Boolean).join(", ") })]),
    h("dd", { text: term.text }),
  ]));
}

const caveat = (text) => (text ? h("p", { class: "hb-caveat" }, [icon("limits", 16), h("span", {}, [h("b", { text: "알아 둘 점" }), h("span", { text: ` ${text}` })])]) : null);

// 근거: 사이트의 규정 원문에 있는 조문은 그 조문으로, 그 밖의 문서는 원문이 있는 바깥 주소로 잇는다.
// 바깥 문서는 문서마다 한 번만 잇고, 그 문서에 댄 조와 항(parts)은 링크 뒤에 글로 적는다(문서의 주소가 하나다).
function basis(refs) {
  const links = (refs || []).map((ref) => {
    if (ref.act) return h("a", { href: lawHref(ref), text: ref.label });
    const link = safeLink(ref.url, ref.label, ref.name ? { title: ref.name } : {});
    if (!link) return null;
    link.append(icon("out", 13), h("span", { class: "sr", text: " (새 창에서 열립니다)" }));
    return ref.parts && ref.parts.length ? h("span", { class: "hb-ref-doc" }, [link, h("span", { class: "hb-ref-parts", text: ref.parts.join(", ") })]) : link;
  }).filter(Boolean);
  return links.length ? h("p", { class: "ref-links hb-refs" }, [h("span", { class: "ref-name" }, [icon("law", 14), h("span", { text: "근거" })]), ...links]) : null;
}

const see = (links) => (links && links.length
  ? h("p", { class: "ref-links hb-refs" }, [h("span", { class: "ref-name" }, [icon("next", 14), h("span", { text: "관련 화면" })]), ...links.map((link) => h("a", { href: link.href, text: link.text }))])
  : null);

// chapterId는 절의 주소(#handbook-<장>.<절>)를 만드는 데 쓴다.
// whole이 참이면 해설서 전체를 한 화면에 놓는 자리다(views/handbook/whole.js): 제목을 한 단계 낮추고, 요소의 이름에 장을 넣어 장끼리 겹치지 않게 한다.
// scope는 장의 범위다(영국 CBAM의 장은 "uk"): 그 장의 글에는 그 범위의 용어 풀이만 단다(js/gloss/scope.js).
export function sectionNode(chapterId, section, whole = false, scope = "") {
  const side = [terms(section), caveat(section.caveat), basis(section.basis), see(section.see)].filter(Boolean);
  const here = `#handbook-${chapterId}.${section.id}`;
  const name = whole ? `${chapterId}-${section.id}` : section.id;
  const paragraphs = section.body.map((text) => h("p", { text }));
  // 그림은 문단을 모두 놓은 뒤에 놓는다. 그림에 자리(after)가 적혀 있으면 그만큼의 문단 뒤에 놓는다(목록을 가리키는 마지막 문단이 목록과 떨어지지 않게)
  const before = section.figure && Number.isInteger(section.figure.after) ? section.figure.after : paragraphs.length;
  const node = h("section", { class: "panel hb-sec", id: `hb-${name}`, "aria-labelledby": `hb-h-${name}`, tabindex: "-1" }, [
    h(whole ? "h3" : "h2", { id: `hb-h-${name}`, class: "hb-sec-title" }, h("a", { class: "hb-anchor", href: here, text: section.title })),
    h("div", { class: "hb-cols" }, [
      h("div", { class: "hb-main" }, [...paragraphs.slice(0, before), figureNode(section.figure, `hb-fig-${name}`), ...paragraphs.slice(before), list(section), formula(section.formula), sheet(section.table, section.title)]),
      side.length ? h("div", { class: "hb-aside" }, side) : null,
    ]),
  ]);
  // 문단과 목록에 나온 다른 절의 용어에 표시한다(이 절이 스스로 풀이한 용어는 바로 옆에 풀이가 있으므로 건너뛴다)
  gloss(node, ".hb-main > p, .hb-list li", { scope, skip: (term) => term.read === here });
  return node;
}
