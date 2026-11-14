// 소식 카드. 어느 화면에서나 같은 짜임으로 쓴다. 왼쪽에 미리보기 그림, 오른쪽에 본문.
import { h, safeLink } from "./dom.js";
import { day } from "./format.js";
import { icon } from "./icons.js";
import { titleLink } from "./itemlink.js";
import { HIGH_NAME, isHigh } from "../news/importance.js";
import { thumb } from "./thumb.js";
import { topicName, topicOf } from "./topics.js";

// 원문 발췌. 요약의 근거가 된 원문 대목을 그대로 보여 준다(EU 공식 자료만).
function excerpt(item) {
  return h("details", { class: "excerpt" }, [
    h("summary", { text: "원문 발췌 보기" }),
    h("blockquote", { lang: "en", cite: item.link || null }, String(item.excerpt).split("\n").filter(Boolean).map((line) => h("p", { text: line }))),
    h("p", { class: "count", text: `출처: ${item.sourceName || "원문"}` }),
  ]);
}

export function card(item) {
  const topic = topicOf(item);
  const meta = h("p", { class: "card-meta" }, [
    item.published
      ? h("time", { class: "m-date", datetime: day(item.published), text: day(item.published) })
      : (item.listed ? h("span", { class: "m-date", text: `${day(item.listed)} 수록` }) : null),
    h("a", { class: "m-topic", href: `#news-${topic}`, text: topicName(topic) }),
    item.kind ? h("span", { class: "m-kind", text: item.kind }) : null,
    isHigh(item) ? h("span", { class: "m-imp", text: HIGH_NAME }) : null,
    item.sourceName ? h("span", { class: "m-src", text: item.sourceName }) : null,
  ]);
  // 제목을 누르면 국문 요약 화면으로 간다. 제목이 곧 내용인 한 줄 소식은 원문으로 바로 간다.
  const title = titleLink(item);
  // 제목이 곧 내용인 소식(국내 기관의 공지와 자료 가운데 본문 요약이 아직 없는 것)은 한 줄로 짧게 보여 준다.
  if (item.brief && !item.withdrawn) {
    return h("article", { class: "card card-brief", "data-topic": topic }, [
      h("span", { class: "chipicon" }, icon(topic, 18)),
      h("div", { class: "card-body" }, [meta, h("h3", { class: "card-title" }, title)]),
    ]);
  }
  const source = safeLink(item.link, "원문 보기");
  if (source) source.append(icon("out", 15));
  return h("article", { class: "card", "data-importance": item.importance || null, "data-topic": topic }, [
    thumb(item, topic),
    h("div", { class: "card-body" }, [
      meta,
      h("h3", { class: "card-title" }, title),
      item.withdrawn ? h("p", { class: "card-summary withdrawn", text: "이 소식의 요약은 내렸습니다. 원문에서 확인해 주세요." }) : null,
      !item.withdrawn && item.summary ? h("p", { class: "card-summary", text: item.summary }) : null,
      !item.withdrawn && item.impact ? h("p", { class: "card-impact" }, [h("strong", { text: "실무 영향" }), h("span", { text: item.impact })]) : null,
      !item.withdrawn && item.excerpt ? excerpt(item) : null,
      source ? h("div", { class: "card-foot" }, source) : null,
    ]),
  ]);
}
