// 품목 한 장 보기의 이어 가는 곳: 다가오는 의무 일정, 근거 조문, 해설서의 절, 그 부문의 소식과 개정안.
import { dutyHref, lawHref } from "../../../laws/refs.js";
import { proposedText, upcoming } from "../../../sector/facts.js";
import { h, safeLink } from "../../../ui/dom.js";
import { day, koreanDate } from "../../../ui/format.js";
import { icon } from "../../../ui/icons.js";

const NEWS = 4; // 한 장에 싣는 소식의 수(더 보려면 부문별 보기로 간다)

function block(id, title, more, body) {
  return h("div", { class: "sheet-block", role: "group", "aria-labelledby": id }, [
    h("div", { class: "sheet-block-head" }, [h("h3", { id, text: title }), more || null]),
    ...body,
  ]);
}

function duties(list, todayIso) {
  const next = upcoming(list, todayIso, 3, "eu");
  if (!next.length) return null;
  return block("h-sheet-duties", "다가오는 의무 일정", h("a", { class: "more", href: "#calendar", text: "일정 모두 보기" }), [
    h("ul", { class: "sheet-links sheet-dates" }, next.map((duty) => h("li", {}, [
      h("time", { datetime: duty.date, text: koreanDate(duty.date) }), h("a", { href: dutyHref(duty), text: duty.title }),
    ]))),
    h("p", { class: "count", text: "의무 일정은 모든 품목에 같습니다." }),
  ]);
}

function basis(rows) {
  if (!rows.length) return null;
  return block("h-sheet-basis", "근거 조문", h("a", { class: "more", href: "#laws", text: "규정 원문 모두 보기" }), [
    h("ul", { class: "sheet-links" }, rows.map((row) => h("li", {}, [h("span", { class: "sheet-about", text: row.about }), h("a", { href: lawHref(row), text: row.label })]))),
  ]);
}

function read(rows) {
  if (!rows.length) return null;
  return block("h-sheet-read", "해설서에서 읽기", h("a", { class: "more", href: "#handbook", text: "해설서 차례" }), [
    h("ul", { class: "sheet-links" }, rows.map((row) => h("li", {}, [h("span", { class: "sheet-about", text: row.chapter }), h("a", { href: row.href, text: row.title })]))),
  ]);
}

// 다가오는 의무 일정, 근거 조문, 해설서의 절을 나란히 놓은 띠
export function guideSection(dutyList, todayIso, basisRows, readRows) {
  const blocks = [duties(dutyList, todayIso), basis(basisRows), read(readRows)].filter(Boolean);
  return blocks.length ? h("section", { class: "sheet-sec sheet-guide", "aria-label": "일정, 근거 조문, 해설서" }, blocks) : null;
}

function newsLink(item) {
  if (!item.link) return h("a", { href: `#item-${item.id}`, text: item.title });
  const link = safeLink(item.link, item.title);   // 제목만 실은 소식은 원문으로 바로 간다
  if (link) link.append(icon("out", 13));
  return link || h("span", { text: item.title });
}

// 그 부문의 소식과, 그 부문에 품목을 더하려는 개정안
export function sectorSection(sector) {
  if (!sector) return null;
  const proposed = proposedText(sector.name, sector.proposed);
  const items = (sector.items || []).slice(0, NEWS);
  return h("section", { class: "sheet-sec sheet-sector", "aria-labelledby": "h-sheet-sector" }, [
    h("div", { class: "sheet-block-head" }, [
      h("h3", { id: "h-sheet-sector", text: `${sector.name} 부문의 소식` }),
      h("a", { class: "more", href: `#sector-${sector.key}`, text: `${sector.name} 부문의 안내 문서와 소식 모아 보기` }),
    ]),
    items.length
      ? h("ul", { class: "sheet-links sheet-dates" }, items.map((item) => h("li", {}, [h("time", { datetime: item.date, text: day(item.date) }), newsLink(item)])))
      : h("p", { class: "count", text: "이 부문의 낱말이 나오는 소식이 아직 없습니다." }),
    proposed ? h("p", { class: "sheet-proposed" }, [h("span", { text: proposed }), h("a", { href: "#rules-cbam-downstream", text: "개정안의 진행 상황 보기" })]) : null,
  ]);
}
