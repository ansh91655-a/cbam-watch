// 부문별 모아 보기의 '안내 문서': 그 부문만 다루는 EU 집행위원회 문서와 그 큰 절, 그리고 모든 부문에 함께 적용되는 문서.
import { count } from "../../ui/format.js";
import { h } from "../../ui/dom.js";
import { icon } from "../../ui/icons.js";

function docCard(doc) {
  const meta = [doc.pages ? `PDF ${count(doc.pages)}쪽` : "", doc.received ? `${doc.received}에 받은 판` : ""].filter(Boolean).join(", ");
  return h("article", { class: "panel sector-doc" }, [
    h("h3", {}, h("a", { href: `#law-${doc.id}`, text: doc.name })),
    h("p", { class: "count", lang: "en", text: doc.official }),
    meta ? h("p", { class: "count", text: meta }) : null,
    doc.remark ? h("p", { class: "sector-remark", text: doc.remark }) : null,
    doc.sections.length > 1 ? h("ul", { class: "sector-toc" }, [
      ...doc.sections.map((part) => h("li", {}, h("a", { href: `#law-${doc.id}.${part.id}` }, [h("span", { class: "no", text: part.ko }), h("span", { text: part.titleKo || part.title })]))),
      doc.more ? h("li", { class: "count", text: `이 밖에 ${count(doc.more)}개 절` }) : null,
    ]) : null,
    h("p", { class: "sector-doc-links" }, [
      h("a", { class: "btn", href: `#law-${doc.id}` }, [icon("law", 15), h("span", { text: "원문과 국문 나란히 읽기" })]),
      doc.pdf ? h("a", { class: "btn", href: `#pdf-${doc.id}` }, [icon("file", 15), h("span", { text: "PDF로 나란히 보기" })]) : null,
    ]),
  ]);
}

export function docsSection(sector) {
  if (!sector.docs.length) return null;
  return h("section", { class: "stack sector-sec", "aria-labelledby": "h-sector-docs" }, [
    h("div", { class: "sec-head" }, [h("h2", { id: "h-sector-docs", text: "안내 문서" }), h("a", { href: "#laws", text: "규정 원문 전체" })]),
    h("p", { class: "sector-lead", text: `EU 집행위원회가 ${sector.name} 부문에 관해 낸 문서입니다. 국문은 이 사이트가 옮긴 비공식 번역입니다.` }),
    h("div", { class: "sector-docs" }, sector.docs.map(docCard)),
  ]);
}

const GROUPS = { act: "법령", guide: "가이던스", manual: "안내서", paper: "자료" };

export function commonSection(common) {
  if (!common || !common.length) return null;
  return h("section", { class: "stack sector-sec", "aria-labelledby": "h-sector-common" }, [
    h("div", { class: "sec-head" }, h("h2", { id: "h-sector-common", text: "모든 부문에 함께 적용되는 문서" })),
    h("ul", { class: "sector-common" }, common.map((doc) => h("li", {}, h("a", { href: `#law-${doc.id}` }, [h("span", { class: "pill", text: GROUPS[doc.group] || "문서" }), h("span", { text: doc.name })])))),
  ]);
}
