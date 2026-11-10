// 첫 화면의 옆 칸: 다가오는 일정, 인증서 가격, 규제 진행 상황
import { priceChart } from "../../ui/chart.js";
import { h, unsplit } from "../../ui/dom.js";
import { countdown, koreanDate, price, signed, today } from "../../ui/format.js";

const EVENT_ROWS = 4;
const RULE_ROWS = 5;
const OPEN_TONES = ["progress", "planned", "dispute"];

function head(id, title, href, more) {
  return h("div", { class: "panel-head" }, [h("h2", { id, text: title }), h("a", { class: "more", href, text: more })]);
}

// 날짜를 두 줄로: 위에 월과 일, 아래에 해. 날이 정해지지 않은 일정은 월만 적는다.
function dateBox(value) {
  const text = String(value);
  const month = `${Number(text.slice(5, 7))}월`;
  return h("span", { class: "date-box" }, [
    h("b", { text: text.length === 10 ? `${month} ${Number(text.slice(8, 10))}일` : month }),
    h("span", { text: `${text.slice(0, 4)}년` }),
  ]);
}

export function schedule(events) {
  const now = today().slice(0, 7);
  const upcoming = events.filter((event) => String(event.date) >= now).sort((a, b) => String(a.date).localeCompare(String(b.date))).slice(0, EVENT_ROWS);
  if (!upcoming.length) return null;
  return h("section", { class: "panel", "aria-labelledby": "h-events" }, [
    head("h-events", "다가오는 일정", "#calendar", "일정 전체"),
    h("ul", { class: "date-list" }, upcoming.map((event) => h("li", { "data-kind": event.kind || null }, [
      dateBox(event.date),
      h("span", { class: "what", text: event.title }),
      h("span", { class: "when" }, [
        event.kind ? h("span", { class: "kind", text: event.kind }) : null,
        h("span", { text: String(event.date).length === 10 ? `${koreanDate(event.date, false).replace(/^.*\(/, "(")} ${countdown(event.date)}` : "날짜 미정" }),
      ]),
    ]))),
  ]);
}

export function pricePanel(book) {
  const rows = book.prices || [];
  if (rows.length < 2) return null;
  const latest = rows[rows.length - 1];
  const before = rows[rows.length - 2];
  return h("section", { class: "panel", "aria-labelledby": "h-price" }, [
    head("h-price", "인증서 가격", "#price", "가격표 보기"),
    h("p", { class: "panel-fig" }, [
      h("b", { text: price(latest.value) }),
      h("small", { text: `${book.unit || "유로"}, ${latest.label}` }),
      h("span", { class: "delta", text: `직전보다 ${signed(latest.value - before.value)}` }),
    ]),
    priceChart(rows, book.unit || "유로"),
  ]);
}

// 아직 진행 중인 규제를, 다음 일정이 가까운 것부터 몇 건 보여 준다.
export function rulesPanel(body) {
  const all = body.regulations || [];
  const open = all.filter((rule) => OPEN_TONES.includes(rule.tone));
  if (!open.length) return null;
  const order = (rule) => (rule.nextDate && rule.nextDate >= today() ? `0${rule.nextDate}` : `1${9999 - Number(String(rule.timeline[rule.timeline.length - 1]?.date || "0").slice(0, 4))}`);
  const rows = [...open].sort((a, b) => order(a).localeCompare(order(b))).slice(0, RULE_ROWS);
  return h("section", { class: "panel", "aria-labelledby": "h-rules" }, [
    head("h-rules", "규제 진행 상황", "#rules", `${all.length}건 모두 보기`),
    h("ul", { class: "rule-rows" }, rows.map((rule) => h("li", { "data-tone": rule.tone }, [
      h("a", { href: `#rules-${rule.id}` }, unsplit(rule.name)),
      h("span", { class: "stage-chip", "data-tone": rule.tone, text: rule.stage }),
      h("small", { text: rule.nextDate && rule.nextDate >= today() ? `${koreanDate(rule.nextDate)}: ${rule.next}` : rule.status }),
    ]))),
  ]);
}
