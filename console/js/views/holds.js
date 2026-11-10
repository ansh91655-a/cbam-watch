// 보류함. 검증을 통과하지 못해 게시되지 않은 항목과 그 사유.
import { empty, h, pill, safeLink, viewHead } from "../ui/dom.js";
import { minute } from "../ui/format.js";

export function render(main, model) {
  const holds = model.items.filter((item) => item.state === "보류");
  const cards = holds.map((item) => h("article", { class: "card", "data-importance": "높음" }, [
    h("h3", { text: item.title || item.id }),
    h("p", { class: "meta" }, [pill(`관문 ${item.verdict.gate || "?"}`, "bad"), h("span", { text: item.sourceName || "" }), h("span", { text: minute(item.verdict.at) })]),
    h("p", { class: "summary", text: item.summary || "" }),
    h("p", { class: "impact" }, [h("strong", { text: "보류 사유 " }), h("span", { text: item.verdict.why || "" })]),
    h("div", { class: "foot" }, [safeLink(item.link, "원문 보기"), h("span", { text: item.id })]),
  ]));
  main.replaceChildren(
    viewHead("보류함", "보류된 항목은 공개 사이트에 나가지 않습니다. 그대로 두어도 다른 항목의 게시는 계속됩니다."),
    ...(cards.length ? cards : [empty("보류된 항목이 없습니다.")]),
  );
}
