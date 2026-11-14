// 해설서의 장 하나: 옆에 이 장의 절과 다른 장의 목록, 가운데에 절들, 맨 아래에 앞 장과 다음 장.
import { rename } from "../../router.js";
import { h } from "../../ui/dom.js";
import { icon } from "../../ui/icons.js";
import { notice } from "./contents.js";
import { sectionNode } from "./section.js";

const FLASH_MS = 1800;

// 그 절로 옮겨 가 잠깐 표시한다. focus가 참이면 초점도 옮긴다(주소로 바로 왔을 때 화면 낭독기가 그 절부터 읽는다).
export function reach(sectionId, focus = false) {
  const node = document.getElementById(`hb-${sectionId}`);
  if (!node) return;
  node.scrollIntoView({ block: "start" });
  if (focus) node.focus({ preventScroll: true });
  node.dataset.flash = "true";
  setTimeout(() => { delete node.dataset.flash; }, FLASH_MS);
}

// 이 장 안의 절로 갈 때에는 화면을 다시 그리지 않고 자리만 옮긴다(주소는 바꿔 둔다: 그 주소를 남에게 줄 수 있게).
function jump(event, sectionId, href) {
  event.preventDefault();
  reach(sectionId, true);
  rename(href);
}

function sideList(book, at) {
  const chapter = book.chapters[at];
  return h("aside", { class: "side hb-side" }, [
    h("a", { class: "hb-back", href: "#handbook" }, [icon("back", 14), h("span", { text: "해설서 차례" })]),
    h("nav", { class: "hb-toc", "aria-label": "이 장의 절" }, [
      h("h2", { text: "이 장의 절" }),
      h("ol", {}, chapter.sections.map((section) => {
        const href = `#handbook-${chapter.id}.${section.id}`;
        return h("li", {}, h("a", { href, onclick: (event) => jump(event, section.id, href), text: section.title }));
      })),
    ]),
    h("nav", { class: "hb-toc hb-others", "aria-label": "해설서의 장" }, [
      h("h2", { text: "해설서의 장" }),
      h("ol", {}, book.chapters.map((one, index) => h("li", {}, h("a", { href: `#handbook-${one.id}`, "aria-current": index === at ? "page" : null }, [
        h("span", { class: "hb-toc-no", "aria-hidden": "true", text: String(index + 1) }), h("span", {}, [h("span", { class: "sr", text: `${index + 1}장 ` }), one.title]),
      ])))),
    ]),
  ]);
}

function pager(book, at) {
  const link = (index, way) => {
    const one = book.chapters[index];
    if (!one) return h("span", {});
    return h("a", { class: "hb-turn", "data-way": way, href: `#handbook-${one.id}` }, [
      h("small", { text: way === "prev" ? "앞 장" : "다음 장" }),
      h("b", { text: `${index + 1}장 ${one.title}` }),
    ]);
  };
  return h("nav", { class: "hb-pager", "aria-label": "앞 장과 다음 장" }, [link(at - 1, "prev"), link(at + 1, "next")]);
}

export function chapterPage(book, at) {
  const chapter = book.chapters[at];
  return h("div", { class: "with-side hb-page" }, [
    sideList(book, at),
    h("div", { class: "stack-l hb-body" }, [
      notice(book),
      ...chapter.sections.map((section) => sectionNode(chapter.id, section, false, chapter.scope)),
      pager(book, at),
    ]),
  ]);
}
