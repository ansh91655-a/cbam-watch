// 해설서의 절 하나. 왼쪽에 글(문단, 그림, 목록, 식, 표), 오른쪽에 곁들이는 것(용어 풀이, 알아 둘 점, 근거 조문, 관련 화면)을 둔다.
// 좁은 화면에서는 곁들이는 것이 글 아래로 내려간다(css/handbook.css).
import { lawHref } from "../../laws/refs.js";
import { h, safeLink, table } from "../../ui/dom.js";
import { gloss } from "../../ui/gloss.js";
import { icon } from "../../ui/icons.js";
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

function sheet(one, name) {
  if (!one) return null;
  return table(one.head, one.rows.map((cells) => h("tr", {}, cells.map((cell, at) => (at === 0 ? h("th", { scope: "row", text: cell }) : h("td", { text: cell }))))), `${name} 표`);
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
function basis(refs) {
  const links = (refs || []).map((ref) => {
    if (ref.act) return h("a", { href: lawHref(ref), text: ref.label });
    const link = safeLink(ref.url, ref.label);
    if (link) link.append(icon("out", 13), h("span", { class: "sr", text: " (새 창에서 열립니다)" }));
    return link;
  }).filter(Boolean);
  return links.length ? h("p", { class: "ref-links hb-refs" }, [h("span", { class: "ref-name" }, [icon("law", 14), h("span", { text: "근거" })]), ...links]) : null;
}

const see = (links) => (links && links.length
  ? h("p", { class: "ref-links hb-refs" }, [h("span", { class: "ref-name" }, [icon("next", 14), h("span", { text: "관련 화면" })]), ...links.map((link) => h("a", { href: link.href, text: link.text }))])
  : null);

// chapterId는 절의 주소(#handbook-<장>.<절>)를 만드는 데 쓴다.
export function sectionNode(chapterId, section) {
  const side = [terms(section), caveat(section.caveat), basis(section.basis), see(section.see)].filter(Boolean);
  const here = `#handbook-${chapterId}.${section.id}`;
  const node = h("section", { class: "panel hb-sec", id: `hb-${section.id}`, "aria-labelledby": `hb-h-${section.id}`, tabindex: "-1" }, [
    h("h2", { id: `hb-h-${section.id}` }, h("a", { class: "hb-anchor", href: `#handbook-${chapterId}.${section.id}`, text: section.title })),
    h("div", { class: "hb-cols" }, [
      h("div", { class: "hb-main" }, [...section.body.map((text) => h("p", { text })), figureNode(section.figure, `hb-fig-${section.id}`), list(section), formula(section.formula), sheet(section.table, section.title)]),
      side.length ? h("div", { class: "hb-aside" }, side) : null,
    ]),
  ]);
  // 문단과 목록에 나온 다른 절의 용어에 표시한다(이 절이 스스로 풀이한 용어는 바로 옆에 풀이가 있으므로 건너뛴다)
  gloss(node, ".hb-main > p, .hb-list li", { skip: (term) => term.read === here });
  return node;
}
