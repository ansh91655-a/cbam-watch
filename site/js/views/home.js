// 첫 화면. 맨 위에 지금 알아야 할 세 가지(가격, 다음 일정, 새 소식)를 띠로 두고,
// 왼쪽에 중요한 소식과 새로 오른 소식, 오른쪽에 주제별 보기와 일정과 주간 요약을 둔다.
import * as data from "../data.js";
import { card } from "../ui/card.js";
import { sparkline } from "../ui/chart.js";
import { empty, fill, h, safeLink } from "../ui/dom.js";
import { countdown, daysSince, koreanDate, price, signed, today } from "../ui/format.js";
import { topicList, topicOf } from "../ui/topics.js";

const IMPORTANT_DAYS = 45;
const RECENT_COUNT = 6;
const NEW_DAYS = 7;

function priceFact(book) {
  const rows = book.prices || [];
  if (!rows.length) return null;
  const latest = rows[rows.length - 1];
  const before = rows[rows.length - 2];
  const change = before ? latest.value - before.value : null;
  return h("a", { class: "fact", href: "#price" }, [
    h("span", { class: "fact-label", text: "CBAM 인증서 가격" }),
    h("span", { class: "fact-value" }, [h("span", { text: price(latest.value) }), h("small", { text: book.unit || "유로" })]),
    sparkline(rows),
    h("span", { class: "fact-note", text: `${latest.label}${change === null ? "" : `, 직전보다 ${signed(change)}`}` }),
  ]);
}

function nextFact(events) {
  const now = today();
  const next = events.filter((event) => String(event.date).length === 10 && event.date >= now).sort((a, b) => a.date.localeCompare(b.date))[0];
  if (!next) return null;
  return h("a", { class: "fact", href: `#calendar-${next.date.slice(0, 4)}` }, [
    h("span", { class: "fact-label", text: "다음 일정" }),
    h("span", { class: "fact-value", text: countdown(next.date) }),
    h("span", { class: "fact-note", text: `${koreanDate(next.date)} ${next.title}` }),
  ]);
}

function newsFact(items) {
  const fresh = items.filter((item) => (daysSince(item.listed) ?? 999) <= NEW_DAYS).length;
  return h("a", { class: "fact", href: "#news" }, [
    h("span", { class: "fact-label", text: `최근 ${NEW_DAYS}일 동안 오른 소식` }),
    h("span", { class: "fact-value" }, [h("span", { text: fresh }), h("small", { text: "건" })]),
    h("span", { class: "fact-note", text: `지금까지 모두 ${items.length}건` }),
  ]);
}

function topicPanel(items) {
  const rows = topicList().map((topic) => {
    const mine = items.filter((item) => topicOf(item) === topic.code);
    return mine.length ? h("li", {}, h("a", { href: `#news-${topic.code}` }, [
      h("span", { class: "t-name", text: topic.name }),
      h("span", { class: "t-count", text: `${mine.length}건` }),
      h("span", { class: "t-last", text: mine[0].title }),
    ])) : null;
  });
  return h("section", { class: "panel", "aria-labelledby": "h-topics" }, [
    h("h2", { id: "h-topics", text: "주제별 소식" }),
    h("ul", { class: "topic-list" }, rows),
  ]);
}

function eventsPanel(events) {
  const now = today().slice(0, 7);
  const upcoming = events.filter((event) => String(event.date) >= now).sort((a, b) => String(a.date).localeCompare(String(b.date))).slice(0, 4);
  if (!upcoming.length) return null;
  return h("section", { class: "panel", "aria-labelledby": "h-events" }, [
    h("h2", { id: "h-events", text: "다가오는 일정" }),
    h("ul", { class: "plain-list" }, upcoming.map((event) => h("li", {}, [
      h("time", { class: "when", datetime: event.date, text: event.date }),
      h("span", { text: event.title }),
      String(event.date).length === 10 ? h("span", { class: "dday", text: countdown(event.date) }) : null,
    ]))),
    h("a", { class: "more", href: "#calendar", text: "일정 전체 보기" }),
  ]);
}

function digestPanel(digests) {
  if (!digests.length) return null;
  const latest = [...digests].sort((a, b) => String(b.to).localeCompare(String(a.to)))[0];
  return h("section", { class: "panel", "aria-labelledby": "h-digest" }, [
    h("h2", { id: "h-digest", text: "주간 요약" }),
    h("p", { class: "count", text: `${latest.from} ~ ${latest.to}` }),
    h("p", {}, h("strong", { text: latest.title })),
    ...(latest.paragraphs || []).slice(0, 2).map((text) => h("p", { text })),
  ]);
}

export async function render(main) {
  const [all, events, digests, book] = await Promise.all([data.items(), data.events(), data.digests(), data.prices()]);
  const items = data.newestFirst(all).filter((item) => !item.withdrawn);
  const important = items.filter((item) => item.importance === "높음" && (daysSince(item.published || item.listed) ?? 999) <= IMPORTANT_DAYS).slice(0, 4);
  const taken = new Set(important.map((item) => item.id));
  const recent = data.newestListedFirst(items).filter((item) => !taken.has(item.id)).slice(0, RECENT_COUNT);

  const now = h("section", { class: "now", "aria-label": "지금 알아 둘 것" }, [priceFact(book), nextFact(events), newsFact(items)]);
  const left = h("div", { class: "stack-l" }, [
    important.length ? h("section", { class: "stack", "aria-labelledby": "h-important" }, [h("h2", { id: "h-important", text: "중요 소식" }), ...important.map(card)]) : null,
    h("section", { class: "stack", "aria-labelledby": "h-recent" }, [
      h("div", { class: "sec-head" }, [h("h2", { id: "h-recent", text: "새로 오른 소식" }), h("a", { href: "#news", text: `소식 ${items.length}건 모두 보기` })]),
      ...(recent.length ? recent.map(card) : [empty(items.length ? "다른 최근 소식이 없습니다." : "아직 게시된 소식이 없습니다. 자동 수집이 새 소식을 찾으면 여기에 나타납니다.")]),
    ]),
  ]);
  const right = h("div", { class: "stack-l" }, [topicPanel(items), eventsPanel(events), digestPanel(digests)]);
  fill(main, now, h("div", { class: "cols" }, [left, right]));
}
