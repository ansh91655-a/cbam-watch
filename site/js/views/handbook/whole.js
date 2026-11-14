// 해설서 전체를 한 화면에 놓는다(#handbook-all). 인쇄하거나 PDF로 저장해 돌려 보려는 사람을 위한 화면이다.
// 맨 위에 차례를 두고, 장마다 제목과 절들을 차례로 놓는다. 인쇄할 때에는 장마다 새 쪽에서 시작한다(css/handbook-print.css).
import { h } from "../../ui/dom.js";
import { count } from "../../ui/format.js";
import { icon } from "../../ui/icons.js";
import { notice } from "./contents.js";
import { sectionNode } from "./section.js";

// 이 화면 안에서 그 자리로 옮긴다(주소를 바꾸면 다른 화면으로 넘어간다)
function goTo(event, id) {
  const node = document.getElementById(id);
  if (!node) return;
  event.preventDefault();
  node.scrollIntoView({ block: "start" });
  node.focus({ preventScroll: true });
}

function toc(book) {
  return h("nav", { class: "panel hb-whole-toc", "aria-labelledby": "h-hbw-toc" }, [
    h("h2", { id: "h-hbw-toc", text: "차례" }),
    h("ol", {}, book.chapters.map((chapter, at) => h("li", {}, [
      h("a", { href: `#handbook-${chapter.id}`, onclick: (event) => goTo(event, `hbw-${chapter.id}`) }, [h("span", { class: "hb-toc-no", "aria-hidden": "true", text: String(at + 1) }), h("span", { text: chapter.title })]),
      h("ul", {}, chapter.sections.map((section) => h("li", {}, h("a", { href: `#handbook-${chapter.id}.${section.id}`, onclick: (event) => goTo(event, `hb-${chapter.id}-${section.id}`), text: section.title })))),
    ]))),
  ]);
}

export function wholeBook(book) {
  const sections = book.chapters.reduce((sum, chapter) => sum + chapter.sections.length, 0);
  return h("div", { class: "stack-l hb-whole" }, [
    notice(book),
    h("div", { class: "hb-whole-bar" }, [
      h("p", { text: `${count(book.chapters.length)}개 장, ${count(sections)}개 절을 한 화면에 놓았습니다. 인쇄하면 장마다 새 쪽에서 시작합니다.` }),
      h("p", { class: "hb-whole-actions" }, [
        h("button", { type: "button", class: "btn btn-main", onclick: () => window.print() }, [icon("download", 15), h("span", { text: "인쇄하거나 PDF로 저장" })]),
        h("a", { class: "btn", href: "#handbook" }, [icon("back", 15), h("span", { text: "해설서 차례로" })]),
      ]),
    ]),
    toc(book),
    ...book.chapters.map((chapter, at) => h("section", { class: "stack hb-whole-chapter", id: `hbw-${chapter.id}`, "aria-labelledby": `h-hbw-${chapter.id}`, tabindex: "-1" }, [
      h("div", { class: "hb-whole-head" }, [
        h("h2", { id: `h-hbw-${chapter.id}` }, [h("span", { class: "hb-whole-no", text: `${at + 1}장` }), h("span", { text: chapter.title })]),
        h("p", { class: "sec-lead", text: chapter.lead }),
      ]),
      ...chapter.sections.map((section) => sectionNode(chapter.id, section, true)),
    ])),
  ]);
}
