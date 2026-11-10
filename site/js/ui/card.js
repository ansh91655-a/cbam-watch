// 소식 카드. 어느 화면에서나 같은 모양으로 쓴다.
import { h, pill, safeLink } from "./dom.js";
import { day } from "./format.js";

const TONE = { "높음": "bad", "보통": "accent" };

export function card(item) {
  const meta = [
    item.published ? h("span", { text: day(item.published) }) : (item.listed ? h("span", { text: `등재 ${day(item.listed)}` }) : null),
    item.kind ? pill(item.kind) : null,
    item.importance ? pill(`중요도 ${item.importance}`, TONE[item.importance]) : null,
    item.sourceName ? h("span", { text: item.sourceName }) : null,
  ];
  const link = safeLink(item.link, item.title || "원문");
  const foot = [
    safeLink(item.link, "원문 보기"),
    item.checkedAt ? h("span", { text: `원문 대조 ${day(item.checkedAt)}` }) : null,
    pill(item.authoring === "사람이 고침" ? "사람이 고침" : "자동 정리"),
  ];
  return h("article", { class: "card", "data-importance": item.importance || null, id: item.id ? `item-${item.id}` : null }, [
    h("h3", {}, link || h("span", { text: item.title || "" })),
    h("p", { class: "meta" }, meta),
    item.summary ? h("p", { class: "summary", text: item.summary }) : null,
    item.impact ? h("p", { class: "impact" }, [h("strong", { text: "실무 영향 " }), h("span", { text: item.impact })]) : null,
    h("div", { class: "foot" }, foot),
  ]);
}
