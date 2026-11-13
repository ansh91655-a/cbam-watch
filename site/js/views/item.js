// 소식 하나의 국문 요약. 원문으로 가기 전에 이 화면에서 요약, 실무 영향, 원문 발췌를 먼저 읽는다.
// 주소는 #item-<소식 번호>이고, 새 소식 구독(RSS)의 링크도 이 화면으로 온다.
import * as data from "../data.js";
import { isNotice } from "../news/notices.js";
import { empty, fill, h, safeLink, unsplit } from "../ui/dom.js";
import { day } from "../ui/format.js";
import { icon } from "../ui/icons.js";
import { card } from "../ui/card.js";
import { lawRefs } from "../ui/lawrefs.js";
import { topicName, topicOf } from "../ui/topics.js";

const RELATED = 4;

// 원문이 열리는 사이트의 이름(주소의 호스트)
function hostOf(link) {
  try {
    return new URL(String(link)).hostname.replace(/^www\./, "");
  } catch (error) {
    return "";
  }
}

function head(item, topic) {
  const date = data.dateOf(item);
  return h("div", { class: "view-head bleed item-head" }, h("div", { class: "band-inner" }, [
    h("a", { class: "back", href: `#news-${topic}` }, [icon("back", 16), h("span", { text: `${topicName(topic)} 소식 목록` })]),
    h("h1", {}, unsplit(item.title)),
    h("p", { class: "item-meta" }, [
      date ? h("time", { datetime: day(date), text: day(date) }) : null,
      item.kind ? h("span", { text: item.kind }) : null,
      item.sourceName ? h("span", { text: item.sourceName }) : null,
      item.importance === "높음" ? h("span", { class: "m-imp", text: "중요" }) : null,
    ]),
  ]));
}

function excerpt(item) {
  return h("section", { class: "item-excerpt", "aria-labelledby": "h-excerpt" }, [
    h("h2", { id: "h-excerpt", text: "원문 발췌" }),
    h("blockquote", { lang: "en", cite: item.link || null }, String(item.excerpt).split("\n").filter(Boolean).map((line) => h("p", { text: line }))),
    h("p", { class: "count", text: "요약의 근거가 된 원문 대목입니다." }),
  ]);
}

function facts(item, topic) {
  const rows = [
    ["원문 게시일", item.published ? day(item.published) : ""],
    ["이 사이트에 실은 날", item.listed ? day(item.listed) : ""],
    ["요약을 고친 날", item.revised ? day(item.revised) : ""],
    ["종류", item.kind || ""],
    ["출처", item.sourceName || ""],
  ].filter(([, value]) => value);
  const tags = (item.topics || []).filter(Boolean);
  return h("aside", { class: "panel item-facts", "aria-label": "이 소식의 정보" }, [
    h("dl", {}, [
      ...rows.flatMap(([name, value]) => [h("dt", { text: name }), h("dd", { text: value })]),
      h("dt", { text: "주제" }), h("dd", {}, h("a", { href: `#news-${topic}`, text: topicName(topic) })),
    ]),
    tags.length ? h("ul", { class: "item-tags", "aria-label": "다룬 내용" }, tags.map((tag) => h("li", { text: tag }))) : null,
  ]);
}

function body(item, refs) {
  const host = hostOf(item.link);
  const source = safeLink(item.link, "원문 열기", { class: "btn btn-main" });
  if (source) source.append(icon("out", 15));
  return h("article", { class: "item-body" }, [
    item.withdrawn
      ? h("p", { class: "item-summary withdrawn", text: "이 소식의 요약은 내렸습니다. 원문에서 확인해 주세요." })
      : (item.summary ? h("p", { class: "item-summary", text: item.summary }) : h("p", { class: "item-summary withdrawn", text: "이 소식은 제목이 곧 내용이어서 따로 요약을 두지 않았습니다." })),
    !item.withdrawn && item.impact ? h("p", { class: "card-impact item-impact" }, [h("strong", { text: "실무 영향" }), h("span", { text: item.impact })]) : null,
    !item.withdrawn && item.excerpt ? excerpt(item) : null,
    item.withdrawn ? null : lawRefs(refs, "이 소식에 나온 법령과 조문"),
    source ? h("div", { class: "item-actions" }, [source, host ? h("span", { class: "count", text: `${host}에서 열립니다` }) : null]) : null,
    h("p", { class: "item-note", text: "이 요약은 원문을 바탕으로 정리한 참고 자료입니다. 정확한 내용은 원문에서 확인해 주세요." }),
  ]);
}

export async function render(main, id) {
  const items = data.newestFirst(await data.items());
  const item = items.find((entry) => entry.id === id);
  if (!item) {
    const target = (await data.moved())[id];  // 다른 소식과 하나로 묶인 소식이면 남긴 소식으로 넘긴다
    if (target) {
      window.location.replace(`#item-${target}`);
      return "소식";
    }
    fill(main,
      h("div", { class: "view-head bleed" }, h("div", { class: "band-inner" }, [h("h1", { text: "소식을 찾지 못했습니다" })])),
      empty("주소가 바뀌었거나 내린 소식일 수 있습니다."),
      h("p", {}, h("a", { class: "btn", href: "#news", text: "소식 목록으로 가기" })),
    );
    return "소식";
  }
  const topic = topicOf(item);
  const refs = (await data.refs()).items[item.id];  // 글에 또렷이 적힌 법령과 조문만 이어져 있다
  const related = items.filter((entry) => entry.id !== item.id && !entry.withdrawn && !isNotice(entry) && topicOf(entry) === topic).slice(0, RELATED);
  fill(main,
    head(item, topic),
    h("div", { class: "cols item-cols" }, [body(item, refs), facts(item, topic)]),
    related.length ? h("section", { class: "stack", "aria-labelledby": "h-related" }, [
      h("div", { class: "sec-head" }, [h("h2", { id: "h-related", text: `${topicName(topic)}의 다른 소식` }), h("a", { href: `#news-${topic}`, text: "이 주제 모두 보기" })]),
      h("div", { class: "cards-2" }, related.map(card)),
    ]) : null,
  );
  return item.title || "소식";
}
