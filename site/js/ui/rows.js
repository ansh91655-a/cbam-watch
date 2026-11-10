// 소식을 한 줄씩 늘어놓은 목록. 날짜, 제목(누르면 국문 요약), 요약의 앞부분, 주제와 출처.
import * as data from "../data.js";
import { h } from "./dom.js";
import { day } from "./format.js";
import { titleLink } from "./itemlink.js";
import { topicName, topicOf } from "./topics.js";

export function itemRow(item, { summary = false } = {}) {
  const topic = topicOf(item);
  const date = data.dateOf(item);
  return h("li", { class: "row", "data-topic": topic, "data-importance": item.importance || null }, [
    date ? h("time", { class: "row-date", datetime: day(date), text: day(date) }) : h("span", { class: "row-date", text: "날짜 없음" }),
    h("span", { class: "row-head" }, [
      titleLink(item, { class: "row-title" }),
      item.importance === "높음" ? h("span", { class: "m-imp", text: "중요" }) : null,
    ]),
    summary && item.summary && !item.brief ? h("span", { class: "row-summary", text: item.summary }) : null,
    h("span", { class: "row-meta" }, [
      h("span", { text: topicName(topic) }),
      item.sourceName ? h("span", { text: item.sourceName }) : null,
    ]),
  ]);
}

export function itemRows(items, options = {}) {
  return h("ul", { class: options.plain ? "rows rows-plain" : "rows" }, items.map((item) => itemRow(item, options)));
}
