// 주제별 찾아보기. 주제마다 소식이 몇 건인지와 가장 최근 소식의 제목을 한 줄씩 적는다.
// 소식이 없는 주제도 흐리게 보여 줘서 무엇을 다루는 사이트인지 알 수 있게 한다.
import { h } from "../../ui/dom.js";
import { icon } from "../../ui/icons.js";
import { topicList, topicOf } from "../../ui/topics.js";

export function topicIndex(items) {
  const cells = topicList().map((topic) => {
    const mine = items.filter((item) => topicOf(item) === topic.code);
    if (!mine.length && topic.code === "etc") return null;
    return h("li", { "data-topic": topic.code, "data-empty": mine.length ? null : "true" }, h("a", { href: `#news-${topic.code}` }, [
      h("span", { class: "ti-icon" }, icon(topic.code, 20)),
      h("span", { class: "ti-name", text: topic.name }),
      h("span", { class: "ti-n", text: `${mine.length}건` }),
      h("span", { class: "ti-latest", text: mine.length ? mine[0].title : "아직 소식이 없습니다" }),
    ]));
  });
  return h("section", { class: "stack", "aria-labelledby": "h-topics" }, [
    h("div", { class: "sec-head" }, [h("h2", { id: "h-topics", text: "주제별 소식" }), h("a", { href: "#news", text: `소식 ${items.length}건 모두 보기` })]),
    h("div", { class: "topic-index" }, h("ul", {}, cells)),
  ]);
}
