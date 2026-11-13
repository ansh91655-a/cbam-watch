// 해설서의 차례: 알아 둘 점 한 줄, 장의 목록, 용어로 찾기.
import { h } from "../../ui/dom.js";
import { count, koreanDate } from "../../ui/format.js";
import { icon } from "../../ui/icons.js";

// 어디에서나 같은 한 줄: 무엇을 풀어 쓴 글이고 어디까지 믿을 수 있는지
export function notice(book) {
  return h("p", { class: "hb-note" }, [
    icon("limits", 16),
    h("span", { text: `법령과 EU 집행위원회의 안내 자료를 풀어 쓴 비공식 해설입니다. 법적 효력은 원문에만 있으니, 절마다 이어 둔 조문에서 확인해 주세요.${book.asOf ? ` ${koreanDate(book.asOf)} 기준입니다.` : ""}` }),
  ]);
}

function chapterCard(chapter, at) {
  return h("li", {}, h("a", { class: "hb-card", href: `#handbook-${chapter.id}` }, [
    h("span", { class: "hb-no", "aria-hidden": "true", text: String(at + 1) }),
    h("span", { class: "hb-card-text" }, [
      h("h3", {}, [h("span", { class: "sr", text: `${at + 1}장 ` }), chapter.title]),
      h("p", { text: chapter.lead }),
      h("span", { class: "count", text: `절 ${count(chapter.sections.length)}개` }),
    ]),
  ]));
}

// 용어로 찾기: 해설서가 풀이한 용어를 누르면 그 용어를 풀이한 절로 간다.
function termIndex(terms) {
  if (!terms.length) return null;
  const sorted = [...terms].sort((a, b) => a.ko.localeCompare(b.ko, "ko"));
  return h("section", { class: "stack", "aria-labelledby": "h-hb-terms" }, [
    h("div", { class: "sec-head" }, [h("h2", { id: "h-hb-terms", text: "용어로 찾기" }), h("a", { href: "#terms", text: "용어집 전체 보기" })]),
    h("p", { class: "sec-lead", text: "용어를 누르면 그 용어를 풀이한 절로 갑니다." }),
    h("div", { class: "chips hb-term-chips" }, sorted.map((term) => h("a", { class: "chip", href: `#handbook-${term.chapter}.${term.section}` }, [
      h("span", { text: term.ko }), term.abbr ? h("small", { lang: "en", text: term.abbr }) : null,
    ]))),
  ]);
}

// missing: 주소가 가리킨 장이 없을 때 그렇다고 알린다.
export function contents(book, missing) {
  return [
    notice(book),
    missing ? h("p", { class: "empty", text: "찾으시는 장이 없습니다. 아래 차례에서 골라 주세요." }) : null,
    h("section", { class: "stack", "aria-labelledby": "h-hb-chapters" }, [
      h("div", { class: "sec-head" }, [h("h2", { id: "h-hb-chapters", text: "차례" }), h("span", { class: "count", text: `${count(book.chapters.length)}개 장` })]),
      h("ol", { class: "hb-chapters" }, book.chapters.map(chapterCard)),
    ]),
    termIndex(book.terms || []),
  ];
}
