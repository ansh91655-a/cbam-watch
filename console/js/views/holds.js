// 보류함. 검증을 통과하지 못해 게시되지 않은 항목과 그 사유.
import { empty, h, pill, safeLink, viewHead } from "../ui/dom.js";
import { minute } from "../ui/format.js";
import { isHold } from "../model.js";

const TONE = { "보류(확인 필요)": "bad", "보류(다시 쓸 예정)": "warn", "보류(다시 씀)": null };
const ORDER = ["보류(확인 필요)", "보류(다시 쓸 예정)", "보류(다시 씀)"];

export function render(main, model) {
  const holds = model.items.filter(isHold).sort((a, b) => ORDER.indexOf(a.state) - ORDER.indexOf(b.state));
  const cards = holds.map((item) => h("article", { class: "card", "data-importance": item.state === "보류(확인 필요)" ? "높음" : "보통" }, [
    h("h3", { text: item.title || item.id }),
    h("p", { class: "meta" }, [pill(item.state, TONE[item.state]), pill(`관문 ${item.verdict.gate || "?"}`), h("span", { text: item.sourceName || "" }), h("span", { text: minute(item.verdict.at) })]),
    h("p", { class: "summary", text: item.summary || "" }),
    h("p", { class: "impact" }, [h("strong", { text: "보류 사유 " }), h("span", { text: item.verdict.why || "" })]),
    h("div", { class: "foot" }, [safeLink(item.link, "원문 보기"), h("span", { text: item.id }), item.revises ? h("span", { text: `${item.revises}를 다시 쓴 초안` }) : null]),
  ]));
  main.replaceChildren(
    viewHead("보류함", "보류된 항목은 공개 사이트에 나가지 않습니다. 글을 고치면 풀리는 보류는 다음 수집·작성 실행이 한 번 다시 쓰고, 그래도 보류되거나 원문을 확인할 수 없는 것만 '확인 필요'로 남습니다."),
    ...(cards.length ? cards : [empty("보류된 항목이 없습니다.")]),
  );
}
