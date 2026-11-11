// 큰 머리 아래쪽의 수치 세 칸: 인증서 가격, 다음 일정, 최근 소식. 칸을 누르면 그 화면으로 간다.
// 수치는 화면에 들어올 때 올라간다(data-count, ui/motion.js). 가격은 직전 가격에서 지금 가격으로 올라가 바뀐 만큼을 보여 준다.
import * as data from "../../data.js";
import { caveatMark, splitCaveat } from "../../ui/caveat.js";
import { sparkline } from "../../ui/chart.js";
import { h } from "../../ui/dom.js";
import { countdown, daysSince, koreanDate, price, signed, today } from "../../ui/format.js";
import { icon } from "../../ui/icons.js";

const NEW_DAYS = 30;

function priceFact(book) {
  const rows = book.prices || [];
  if (!rows.length) return null;
  const latest = rows[rows.length - 1];
  const before = rows[rows.length - 2];
  return h("a", { class: "fact", href: "#price" }, [
    h("span", { class: "fact-label" }, [icon("price", 16), h("span", { text: "CBAM 인증서 가격" })]),
    h("span", { class: "fact-value" }, [h("span", { text: price(latest.value), "data-count": "", "data-count-from": before ? before.value : null }), h("small", { text: book.unit || "유로" })]),
    sparkline(rows),
    h("span", { class: "fact-note", text: `${latest.label}${before ? `, 직전보다 ${signed(latest.value - before.value)}` : ""}` }),
  ]);
}

// 다음 일정. 보도로만 아는 날짜나 잠정 일정이면 그 단서를 설명 뒤에 작은 표시로 따로 적는다.
function nextFact(events) {
  const now = today();
  const next = events.filter((event) => String(event.date).length === 10 && event.date >= now).sort((a, b) => a.date.localeCompare(b.date))[0];
  if (!next) return null;
  const { name, flag } = splitCaveat(next.title);
  return h("a", { class: "fact", href: `#calendar-${next.date.slice(0, 4)}` }, [
    h("span", { class: "fact-label" }, [icon("calendar", 16), h("span", { text: "다음 일정" })]),
    h("span", { class: "fact-value", text: countdown(next.date), "data-count": "" }),
    h("span", { class: "fact-note" }, [`${koreanDate(next.date)} ${name}`, caveatMark(flag)]),
  ]);
}

function newsFact(items, dated) {
  const fresh = dated.filter((item) => (daysSince(data.dateOf(item)) ?? 999) <= NEW_DAYS).length;
  return h("a", { class: "fact", href: "#news" }, [
    h("span", { class: "fact-label" }, [icon("news", 16), h("span", { text: `최근 ${NEW_DAYS}일 소식` })]),
    h("span", { class: "fact-value" }, [h("span", { text: fresh, "data-count": "" }), h("small", { text: "건" })]),
    h("span", { class: "fact-note", text: `지금까지 모두 ${items.length}건` }),
  ]);
}

export function facts(book, events, items, dated) {
  return h("div", { class: "hero-stats" }, [priceFact(book), nextFact(events), newsFact(items, dated)]);
}
