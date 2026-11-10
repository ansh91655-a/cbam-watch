// 소식 카드. 어느 화면에서나 같은 짜임으로 쓴다. 시안에 따라 배치만 달라진다(css/themes.css).
import { h, pill, safeLink } from "./dom.js";
import { day } from "./format.js";
import { topicName, topicOf } from "./topics.js";

// 원문 대조. 요약의 근거가 된 원문 대목을 그대로 보여 준다(EU 공식 자료만).
function excerpt(item) {
  return h("details", { class: "excerpt" }, [
    h("summary", { text: "원문 대조" }),
    h("blockquote", { lang: "en", cite: item.link || null }, String(item.excerpt).split("\n").filter(Boolean).map((line) => h("p", { text: line }))),
    h("p", { class: "count", text: `출처: ${item.sourceName || "원문"}. 원문 글을 그대로 옮긴 것입니다.` }),
  ]);
}

function state(item) {
  if (item.withdrawn) return pill("요약 내림", "warn");
  return pill(item.authoring === "사람이 고침" ? "사람이 고침" : "자동 정리");
}

export function card(item) {
  const topic = topicOf(item);
  const meta = h("p", { class: "card-meta" }, [
    item.published
      ? h("time", { class: "m-date", datetime: day(item.published), text: day(item.published) })
      : (item.listed ? h("span", { class: "m-date", text: `등재 ${day(item.listed)}` }) : null),
    h("a", { class: "m-topic", href: `#news-${topic}`, text: topicName(topic) }),
    item.kind ? h("span", { class: "m-kind", text: item.kind }) : null,
    item.importance === "높음" ? h("span", { class: "m-imp", text: "중요" }) : null,
    item.sourceName ? h("span", { class: "m-src", text: item.sourceName }) : null,
  ]);
  const title = safeLink(item.link, item.title || "원문") || h("span", { text: item.title || "" });
  return h("article", { class: "card", "data-importance": item.importance || null, "data-topic": topic, id: item.id ? `item-${item.id}` : null }, [
    meta,
    h("h3", { class: "card-title" }, title),
    item.withdrawn ? h("p", { class: "card-summary withdrawn", text: "다시 대조한 결과 원문과 어긋난 곳이 있어 요약을 내렸습니다. 원문에서 직접 확인하세요." }) : null,
    !item.withdrawn && item.summary ? h("p", { class: "card-summary", text: item.summary }) : null,
    !item.withdrawn && item.impact ? h("p", { class: "card-impact" }, [h("strong", { text: "실무 영향" }), h("span", { text: item.impact })]) : null,
    !item.withdrawn && item.excerpt ? excerpt(item) : null,
    h("div", { class: "card-foot" }, [
      safeLink(item.link, "원문 보기"),
      item.checkedAt ? h("span", { text: `원문 대조 ${day(item.checkedAt)}` }) : null,
      state(item),
    ]),
  ]);
}
