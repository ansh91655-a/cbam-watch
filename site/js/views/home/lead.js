// 가장 중요한 소식 하나와 그 밖의 중요 소식. 제목을 누르면 원문으로 가기 전에 국문 요약 화면을 먼저 보여 준다.
import * as data from "../../data.js";
import { h, safeLink } from "../../ui/dom.js";
import { day } from "../../ui/format.js";
import { icon } from "../../ui/icons.js";
import { hasPage, titleLink } from "../../ui/itemlink.js";
import { itemRows } from "../../ui/rows.js";
import { topicName, topicOf } from "../../ui/topics.js";

export function lead(item, important, others) {
  const topic = topicOf(item);
  const date = data.dateOf(item);
  const source = safeLink(item.link, "원문 열기", { class: "btn" });
  if (source) source.append(icon("out", 15));
  return h("section", { class: "lead-story", "aria-labelledby": "h-lead", "data-topic": topic }, [
    h("p", { class: "lead-tag", text: important ? "중요 소식" : "가장 최근 소식" }),
    h("h2", { id: "h-lead" }, titleLink(item)),
    item.summary ? h("p", { class: "lead-summary", text: item.summary }) : null,
    item.impact ? h("p", { class: "card-impact" }, [h("strong", { text: "실무 영향" }), h("span", { text: item.impact })]) : null,
    h("p", { class: "lead-meta" }, [
      date ? h("time", { datetime: day(date), text: day(date) }) : null,
      h("a", { href: `#news-${topic}`, text: topicName(topic) }),
      item.sourceName ? h("span", { text: item.sourceName }) : null,
    ]),
    h("div", { class: "lead-links" }, [
      hasPage(item) ? h("a", { class: "btn btn-main", href: `#item-${item.id}`, text: "자세히 보기" }) : null,
      source,
    ]),
    others.length ? h("div", { class: "lead-more" }, [h("h3", { text: "다른 중요 소식" }), itemRows(others, { plain: true })]) : null,
  ]);
}
