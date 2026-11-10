// 가장 중요한 소식 하나를 크게 보여 주는 칸. 최근의 중요 소식이 없으면 날짜가 가장 늦은 소식을 쓴다.
// 제목과 '자세히 보기'는 이 사이트의 국문 요약 화면으로 가고, '원문 열기'는 원문으로 간다.
import { h, safeLink } from "../../ui/dom.js";
import { day } from "../../ui/format.js";
import { icon } from "../../ui/icons.js";
import { hasPage, titleLink } from "../../ui/itemlink.js";
import { topicName, topicOf } from "../../ui/topics.js";

export function feature(item, important, others) {
  const topic = topicOf(item);
  const original = safeLink(item.link, "원문 열기", { class: hasPage(item) ? "btn btn-ghost" : "btn btn-main" });
  if (original) original.append(icon("out", 15));
  return h("article", { class: "feature b-7" }, [
    h("span", { class: "feature-art", "aria-hidden": "true" }, icon(topic, 240)),
    h("span", { class: "tag", text: important ? "중요 소식" : "가장 최근 소식" }),
    h("h2", {}, titleLink(item)),
    h("p", { class: "feature-summary", text: item.summary || "" }),
    h("p", { class: "meta" }, [
      h("span", { text: item.published ? day(item.published) : `${day(item.listed)} 수록` }),
      h("span", { text: topicName(topic) }),
      item.sourceName ? h("span", { text: item.sourceName }) : null,
    ]),
    h("div", { class: "links" }, [
      hasPage(item) ? h("a", { class: "btn btn-main", href: `#item-${item.id}`, text: "자세히 보기" }) : null,
      original,
    ]),
    others.length ? h("div", { class: "feature-more" }, [
      h("p", { text: "다른 중요 소식" }),
      h("ul", {}, others.map((other) => h("li", {}, [
        h("span", { class: "when", text: day(other.published || other.listed) }),
        titleLink(other),
      ]))),
    ]) : null,
  ]);
}
