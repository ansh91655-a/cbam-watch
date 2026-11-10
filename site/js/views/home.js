// 첫 화면. 중요한 소식과 최근 소식을 왼쪽에, 가격과 일정과 주간 요약을 오른쪽에 둔다.
import * as data from "../data.js";
import { card } from "../ui/card.js";
import { empty, h, safeLink } from "../ui/dom.js";
import { day, daysSince } from "../ui/format.js";

const IMPORTANT_DAYS = 45;
const RECENT_COUNT = 8;

function pricePanel(items) {
  const priced = items.filter((item) => item.kind === "가격" && item.price && item.price.value);
  if (!priced.length) return null;
  const latest = priced[0];
  const history = priced.slice(1, 4);
  return h("section", { class: "panel", "aria-labelledby": "h-price" }, [
    h("h2", { id: "h-price", text: "CBAM 인증서 가격" }),
    h("div", { class: "figure" }, [
      h("p", { class: "value" }, [h("span", { text: latest.price.value }), h("small", { text: ` ${latest.price.unit || "유로"}` })]),
      h("p", { class: "label", text: `${latest.price.period} · ${day(latest.published)} 게시` }),
    ]),
    history.length ? h("ul", { class: "plain-list" }, history.map((item) =>
      h("li", {}, [h("span", { class: "when", text: item.price.period }), h("span", { class: "num", text: `${item.price.value} ${item.price.unit || "유로"}` })]))) : null,
    safeLink(latest.link, "가격 원문 보기"),
  ]);
}

function eventsPanel(events) {
  const today = new Date(Date.now() + 9 * 3600000).toISOString().slice(0, 10);
  const upcoming = events.filter((event) => String(event.date) >= today).sort((a, b) => String(a.date).localeCompare(String(b.date))).slice(0, 5);
  if (!upcoming.length) return null;
  return h("section", { class: "panel", "aria-labelledby": "h-events" }, [
    h("h2", { id: "h-events", text: "다가오는 일정" }),
    h("ul", { class: "plain-list" }, upcoming.map((event) =>
      h("li", {}, [h("time", { datetime: event.date, text: event.date }), safeLink(event.link, event.title) || h("span", { text: event.title })]))),
    h("a", { href: "#calendar", text: "일정 전체 보기" }),
  ]);
}

function digestPanel(digests) {
  if (!digests.length) return null;
  const latest = [...digests].sort((a, b) => String(b.to).localeCompare(String(a.to)))[0];
  return h("section", { class: "panel", "aria-labelledby": "h-digest" }, [
    h("h2", { id: "h-digest", text: "주간 요약" }),
    h("p", { class: "meta", text: `${latest.from} ~ ${latest.to}` }),
    h("p", { text: latest.title }),
    ...(latest.paragraphs || []).slice(0, 2).map((text) => h("p", { class: "impact", text })),
  ]);
}

export async function render(main) {
  const [all, events, digests] = await Promise.all([data.items(), data.events(), data.digests()]);
  const items = data.newestFirst(all);
  const important = items.filter((item) => item.importance === "높음" && (daysSince(item.published || item.listed) ?? 999) <= IMPORTANT_DAYS).slice(0, 5);
  const importantIds = new Set(important.map((item) => item.id));
  const recent = items.filter((item) => !importantIds.has(item.id)).slice(0, RECENT_COUNT);

  const left = h("div", { class: "stack-lg" }, [
    important.length ? h("section", { class: "stack", "aria-labelledby": "h-important" }, [h("h2", { id: "h-important", text: "중요 소식" }), ...important.map(card)]) : null,
    h("section", { class: "stack", "aria-labelledby": "h-recent" }, [
      h("h2", { id: "h-recent", text: "최근 소식" }),
      ...(recent.length ? recent.map(card) : [empty(items.length ? "다른 최근 소식이 없습니다." : "아직 게시된 소식이 없습니다. 자동 수집이 새 소식을 찾으면 여기에 나타납니다.")]),
      items.length > recent.length + important.length ? h("p", {}, h("a", { href: "#news", text: `전체 소식 ${items.length}건 보기` })) : null,
    ]),
  ]);
  const right = h("div", { class: "stack-lg" }, [pricePanel(items), eventsPanel(events), digestPanel(digests)]);
  main.replaceChildren(h("div", { class: "two-col" }, [left, right]));
}
