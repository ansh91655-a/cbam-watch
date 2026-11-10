// 첫 화면의 칸들: 다가오는 일정, 인증서 가격 추세, 주제별 소식, 규제 진행 상황.
import { caveatMark, splitCaveat } from "../../ui/caveat.js";
import { priceChart } from "../../ui/chart.js";
import { h, unsplit } from "../../ui/dom.js";
import { countdown, koreanDate, price, signed, today } from "../../ui/format.js";
import { icon } from "../../ui/icons.js";
import { topicList, topicOf } from "../../ui/topics.js";

const RULE_ROWS = 5;
const EVENT_ROWS = 5;
const OPEN_TONES = ["progress", "planned", "dispute"];

function head(id, name, title, href, more) {
  return h("div", { class: "panel-head" }, [h("h2", { id }, [icon(name), h("span", { text: title })]), h("a", { class: "more", href, text: more })]);
}

function dateBox(value) {
  const text = String(value);
  return text.length === 10
    ? h("span", { class: "date-box" }, [h("span", { text: `${text.slice(0, 4)}.${Number(text.slice(5, 7))}` }), h("b", { text: Number(text.slice(8, 10)) })])
    : h("span", { class: "date-box" }, [h("span", { text: text.slice(0, 4) }), h("b", { text: `${Number(text.slice(5, 7))}월` })]);
}

// 일정 한 줄. "보도 기준", "잠정" 같은 단서는 이름에서 떼어 작은 표시로 적는다.
function eventRow(event) {
  const { name, flag } = splitCaveat(event.title);
  const dated = String(event.date).length === 10;
  return h("li", { "data-kind": event.kind || null }, [
    dateBox(event.date),
    h("span", { class: "what" }, [name, caveatMark(flag)]),
    h("span", { class: "when", text: dated ? `${koreanDate(event.date)}, ${countdown(event.date)}` : `${koreanDate(event.date)}부터` }),
  ]);
}

export function schedule(events) {
  const now = today().slice(0, 7);
  const upcoming = events.filter((event) => String(event.date) >= now).sort((a, b) => String(a.date).localeCompare(String(b.date))).slice(0, EVENT_ROWS);
  if (!upcoming.length) return null;
  return h("section", { class: "panel b-5", "aria-labelledby": "h-events" }, [
    head("h-events", "calendar", "다가오는 일정", "#calendar", "일정 전체"),
    h("ul", { class: "date-list" }, upcoming.map(eventRow)),
  ]);
}

export function pricePanel(book) {
  const rows = book.prices || [];
  if (rows.length < 2) return null;
  const latest = rows[rows.length - 1];
  const before = rows[rows.length - 2];
  return h("section", { class: "panel b-5", "aria-labelledby": "h-price" }, [
    head("h-price", "trend", "인증서 가격 추세", "#price", "가격표 보기"),
    h("p", { class: "panel-fig" }, [
      h("b", { text: price(latest.value) }),
      h("small", { text: `${book.unit || "유로"}, ${latest.label}` }),
      h("span", { class: "delta", text: `직전보다 ${signed(latest.value - before.value)}` }),
    ]),
    priceChart(rows, book.unit || "유로"),
  ]);
}

// 주제마다 소식이 몇 건인지와 가장 최근 소식의 제목. 소식이 없는 주제도 흐리게 보여 줘서 무엇을 다루는 사이트인지 알 수 있게 한다.
export function topicsPanel(items) {
  return h("section", { class: "panel b-7", "aria-labelledby": "h-topics" }, [
    head("h-topics", "news", "주제별 소식", "#news", "소식 전체"),
    h("div", { class: "tiles tiles-compact" }, topicList().map((topic) => {
      const mine = items.filter((item) => topicOf(item) === topic.code);
      if (!mine.length && topic.code === "etc") return null;
      return h("a", { class: "tile", href: `#news-${topic.code}`, "data-topic": topic.code, "data-empty": mine.length ? null : "true" }, [
        h("span", { class: "chipicon" }, icon(topic.code, 19)),
        h("span", { class: "tile-name" }, [h("span", { text: topic.name }), h("span", { class: "tile-n", text: mine.length })]),
        h("span", { class: "tile-sub", text: mine.length ? mine[0].title : "아직 소식이 없습니다" }),
      ]);
    })),
  ]);
}

// 규제 진행 상황: 아직 진행 중인 규제를, 다음 일정이 가까운 것부터 몇 건 보여 준다.
export function rulesPanel(body) {
  const open = (body.regulations || []).filter((rule) => OPEN_TONES.includes(rule.tone));
  if (!open.length) return null;
  const order = (rule) => (rule.nextDate && rule.nextDate >= today() ? `0${rule.nextDate}` : `1${9999 - Number(String(rule.timeline[rule.timeline.length - 1]?.date || "0").slice(0, 4))}`);
  const rows = [...open].sort((a, b) => order(a).localeCompare(order(b))).slice(0, RULE_ROWS);
  return h("section", { class: "panel", "aria-labelledby": "h-rules" }, [
    head("h-rules", "legis", "규제 진행 상황", "#rules", `규제 ${(body.regulations || []).length}건 모두 보기`),
    h("ul", { class: "rule-rows" }, rows.map((rule) => h("li", { "data-tone": rule.tone }, [
      h("a", { href: `#rules-${rule.id}` }, unsplit(rule.name)),
      h("span", { class: "stage-chip", "data-tone": rule.tone, text: rule.stage }),
      h("small", { text: rule.nextDate && rule.nextDate >= today() ? `${koreanDate(rule.nextDate)}: ${rule.next}` : rule.status }),
    ]))),
  ]);
}
