// 첫 화면. 맨 위에 큰 머리(점 지도, 한 줄 소개, 지금 알아 둘 수치 세 개)를 두고,
// 그 아래에 가장 중요한 소식, 다가오는 일정, 가격 추세, 주제별 소식, 새로 오른 소식, 주간 요약을 칸으로 나눠 놓고, 맨 아래 짙은 띠에 품목별 가이던스를 둔다.
import * as data from "../data.js";
import { card } from "../ui/card.js";
import { priceChart, sparkline } from "../ui/chart.js";
import { empty, fill, h, safeLink } from "../ui/dom.js";
import { countdown, day, daysSince, koreanDate, price, signed, today } from "../ui/format.js";
import { heroMap } from "../ui/heromap.js";
import { icon } from "../ui/icons.js";
import { topicList, topicName, topicOf } from "../ui/topics.js";

const IMPORTANT_DAYS = 45;
const RECENT_COUNT = 6;
const MORE_IMPORTANT = 2;
const NEW_DAYS = 7;
// CBAM 대상 품목과 EU 집행위원회의 품목별 가이던스 번호
const SECTORS = [["cement", "시멘트", "5a"], ["steel", "철강", "5d"], ["aluminium", "알루미늄", "5e"], ["fertilisers", "비료", "5c"], ["electricity", "전력", "5f"], ["hydrogen", "수소", "5b"]];

function priceFact(book) {
  const rows = book.prices || [];
  if (!rows.length) return null;
  const latest = rows[rows.length - 1];
  const before = rows[rows.length - 2];
  return h("a", { class: "fact", href: "#price" }, [
    h("span", { class: "fact-label" }, [icon("price", 16), h("span", { text: "CBAM 인증서 가격" })]),
    h("span", { class: "fact-value" }, [h("span", { text: price(latest.value) }), h("small", { text: book.unit || "유로" })]),
    sparkline(rows),
    h("span", { class: "fact-note", text: `${latest.label}${before ? `, 직전보다 ${signed(latest.value - before.value)}` : ""}` }),
  ]);
}

function nextFact(events) {
  const now = today();
  const next = events.filter((event) => String(event.date).length === 10 && event.date >= now).sort((a, b) => a.date.localeCompare(b.date))[0];
  if (!next) return null;
  return h("a", { class: "fact", href: `#calendar-${next.date.slice(0, 4)}` }, [
    h("span", { class: "fact-label" }, [icon("calendar", 16), h("span", { text: "다음 일정" })]),
    h("span", { class: "fact-value", text: countdown(next.date) }),
    h("span", { class: "fact-note", text: `${koreanDate(next.date)} ${next.title}` }),
  ]);
}

function newsFact(items) {
  const fresh = items.filter((item) => (daysSince(item.listed) ?? 999) <= NEW_DAYS).length;
  return h("a", { class: "fact", href: "#news" }, [
    h("span", { class: "fact-label" }, [icon("news", 16), h("span", { text: `최근 ${NEW_DAYS}일 동안 오른 소식` })]),
    h("span", { class: "fact-value" }, [h("span", { text: fresh }), h("small", { text: "건" })]),
    h("span", { class: "fact-note", text: `지금까지 모두 ${items.length}건` }),
  ]);
}

function hero(book, events, items) {
  return h("section", { class: "hero bleed", "aria-label": "소개와 지금 알아 둘 것" }, h("div", { class: "hero-inner" }, [
    heroMap(),
    h("div", { class: "hero-copy" }, [
      h("p", { class: "hero-fresh", "data-fresh": "" }),
      h("h1", {}, ["CBAM 규제,", h("br"), h("span", { class: "hl", text: "달라진 것" }), "부터 봅니다"]),
      h("p", { class: "hero-lead", text: "EU 탄소국경조정제도의 법령, 가이던스, 인증서 가격, 일정을 평일마다 확인해 원문과 함께 국문으로 정리합니다." }),
      h("div", { class: "hero-actions" }, [
        h("a", { class: "btn btn-main", href: "#news", text: "새 소식 보기" }),
        h("a", { class: "btn btn-ghost", href: "#price", text: "인증서 가격 보기" }),
      ]),
    ]),
    h("p", { class: "hero-legend", "aria-hidden": "true" }, [
      h("span", {}, [h("i", {}), "EU 회원국"]),
      h("span", {}, [h("i", { class: "kr" }), "한국. 선은 EU의 주요 항구로 가는 길을 나타낸 그림입니다."]),
    ]),
    h("div", { class: "hero-stats" }, [priceFact(book), nextFact(events), newsFact(items)]),
  ]));
}

// 가장 중요한 소식 하나. 최근의 중요 소식이 없으면 가장 늦게 오른 소식을 쓴다. 다른 중요 소식이 있으면 아래에 제목만 덧붙인다.
function feature(item, important, others) {
  const topic = topicOf(item);
  const title = safeLink(item.link, item.title) || h("span", { text: item.title });
  const source = safeLink(item.link, "원문 보기", { class: "btn btn-main" });
  return h("article", { class: "feature b-7" }, [
    h("span", { class: "feature-art", "aria-hidden": "true" }, icon(topic, 240)),
    h("span", { class: "tag", text: important ? "중요 소식" : "가장 최근 소식" }),
    h("h2", {}, title),
    h("p", { class: "feature-summary", text: item.summary || "" }),
    h("p", { class: "meta" }, [
      h("span", { text: item.published ? day(item.published) : `등재 ${day(item.listed)}` }),
      h("span", { text: topicName(topic) }),
      item.sourceName ? h("span", { text: item.sourceName }) : null,
    ]),
    h("div", { class: "links" }, [source, h("a", { class: "btn btn-ghost", href: `#news-${topic}`, text: `${topicName(topic)} 소식 더 보기` })]),
    others.length ? h("div", { class: "feature-more" }, [
      h("p", { text: "다른 중요 소식" }),
      h("ul", {}, others.map((other) => h("li", {}, [
        h("span", { class: "when", text: day(other.published || other.listed) }),
        safeLink(other.link, other.title) || h("span", { text: other.title }),
      ]))),
    ]) : null,
  ]);
}

function dateBox(value) {
  const text = String(value);
  return text.length === 10
    ? h("span", { class: "date-box" }, [h("span", { text: `${text.slice(0, 4)}.${Number(text.slice(5, 7))}` }), h("b", { text: Number(text.slice(8, 10)) })])
    : h("span", { class: "date-box" }, [h("span", { text: text.slice(0, 4) }), h("b", { text: `${Number(text.slice(5, 7))}월` })]);
}

function schedule(events) {
  const now = today().slice(0, 7);
  const upcoming = events.filter((event) => String(event.date) >= now).sort((a, b) => String(a.date).localeCompare(String(b.date))).slice(0, 4);
  if (!upcoming.length) return null;
  return h("section", { class: "panel b-5", "aria-labelledby": "h-events" }, [
    h("div", { class: "panel-head" }, [h("h2", { id: "h-events" }, [icon("calendar"), h("span", { text: "다가오는 일정" })]), h("a", { class: "more", href: "#calendar", text: "일정 전체" })]),
    h("ul", { class: "date-list" }, upcoming.map((event) => h("li", { "data-kind": event.kind || null }, [
      dateBox(event.date),
      h("span", { class: "what", text: event.title }),
      h("span", { class: "when", text: String(event.date).length === 10 ? `${koreanDate(event.date)}, ${countdown(event.date)}` : `${koreanDate(event.date)}부터` }),
    ]))),
  ]);
}

function pricePanel(book) {
  const rows = book.prices || [];
  if (rows.length < 2) return null;
  const latest = rows[rows.length - 1];
  const before = rows[rows.length - 2];
  return h("section", { class: "panel b-5", "aria-labelledby": "h-price" }, [
    h("div", { class: "panel-head" }, [h("h2", { id: "h-price" }, [icon("trend"), h("span", { text: "인증서 가격 추세" })]), h("a", { class: "more", href: "#price", text: "가격표 보기" })]),
    h("p", { class: "panel-fig" }, [
      h("b", { text: price(latest.value) }),
      h("small", { text: `${book.unit || "유로"}, ${latest.label}` }),
      h("span", { class: "delta", text: `직전보다 ${signed(latest.value - before.value)}` }),
    ]),
    priceChart(rows, book.unit || "유로"),
  ]);
}

// 주제마다 소식이 몇 건인지와 가장 최근 소식의 제목. 소식이 없는 주제도 흐리게 보여 줘서 무엇을 다루는 사이트인지 알 수 있게 한다.
function topicsPanel(items) {
  return h("section", { class: "panel b-7", "aria-labelledby": "h-topics" }, [
    h("div", { class: "panel-head" }, [h("h2", { id: "h-topics" }, [icon("news"), h("span", { text: "주제별 소식" })]), h("a", { class: "more", href: "#news", text: "소식 전체" })]),
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

// 품목마다 그림이 있는 칸. 누르면 그 품목의 가이던스 원문을 내려받는다(대장에 없으면 원문 대장으로 간다).
function sectors(documents) {
  const tiles = SECTORS.map(([key, name, no]) => {
    const doc = documents.find((item) => new RegExp(`Guidance No\\.? ?${no}\\b`, "i").test(`${item.title} ${item.filename}`));
    const body = [
      h("span", { class: "sector-art", "aria-hidden": "true" }, icon(key, 92)),
      h("span", { class: "sector-body" }, [
        h("span", { class: "tile-name", text: name }),
        h("span", { class: "tile-sub", text: doc ? `가이던스 ${no}, ${doc.format}${doc.pages ? ` ${doc.pages}쪽` : ""}` : `가이던스 ${no}` }),
        h("span", { class: "get" }, [icon(doc ? "download" : "next", 15), h("span", { text: doc ? "내려받기" : "원문 대장에서 찾기" })]),
      ]),
    ];
    const link = doc ? safeLink(doc.download, "", { class: "sector", "data-sector": key, target: null, download: doc.filename, title: `${doc.filename} 내려받기` }) : null;
    if (link) return fill(link, body);
    return h("a", { class: "sector", "data-sector": key, href: "#docs" }, body);
  });
  return h("section", { class: "showcase bleed", "aria-labelledby": "h-sectors" }, h("div", { class: "showcase-inner" }, [
    h("div", { class: "sec-head" }, [h("h2", { id: "h-sectors", text: "품목별 가이던스" }), h("a", { href: "#docs", text: "원문 대장 전체 보기" })]),
    h("p", { class: "sec-lead", text: "EU 집행위원회가 CBAM 대상 품목마다 낸 가이던스입니다. 누르면 원문 파일을 내려받습니다." }),
    h("div", { class: "sectors" }, tiles),
  ]));
}

function digest(digests) {
  if (!digests.length) return null;
  const latest = [...digests].sort((a, b) => String(b.to).localeCompare(String(a.to)))[0];
  return h("section", { class: "quote", "aria-labelledby": "h-digest" }, [
    h("div", { class: "quote-head" }, [
      h("p", { class: "label" }, [icon("clock", 16), h("span", { text: "주간 요약" })]),
      h("h2", { id: "h-digest", text: latest.title }),
      h("p", { class: "count", text: `${latest.from} ~ ${latest.to}` }),
    ]),
    h("div", { class: "quote-body" }, (latest.paragraphs || []).slice(0, 3).map((text) => h("p", { text }))),
  ]);
}

export async function render(main) {
  const [all, events, digests, book, documents] = await Promise.all([data.items(), data.events(), data.digests(), data.prices(), data.documents()]);
  const items = data.newestFirst(all).filter((item) => !item.withdrawn);
  const isImportant = (item) => item.importance === "높음" && (daysSince(item.published || item.listed) ?? 999) <= IMPORTANT_DAYS;
  const important = items.find(isImportant);
  const lead = important || data.newestListedFirst(items)[0];
  const others = important ? items.filter((item) => isImportant(item) && item.id !== lead.id).slice(0, MORE_IMPORTANT) : [];
  const shown = new Set([lead, ...others].filter(Boolean).map((item) => item.id));
  const recent = data.newestListedFirst(items).filter((item) => !shown.has(item.id)).slice(0, RECENT_COUNT);

  fill(main,
    hero(book, events, items),
    h("div", { class: "bento" }, [lead ? feature(lead, Boolean(important), others) : null, schedule(events), pricePanel(book), topicsPanel(items)]),
    h("section", { class: "stack", "aria-labelledby": "h-recent" }, [
      h("div", { class: "sec-head" }, [h("h2", { id: "h-recent", text: "새로 오른 소식" }), h("a", { href: "#news", text: `소식 ${items.length}건 모두 보기` })]),
      recent.length ? h("div", { class: "cards-2" }, recent.map(card)) : empty(items.length ? "다른 최근 소식이 없습니다." : "아직 게시된 소식이 없습니다. 자동 수집이 새 소식을 찾으면 여기에 나타납니다."),
    ]),
    digest(digests),
    sectors(documents),
  );
}
