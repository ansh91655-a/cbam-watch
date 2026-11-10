// 초안과 판정. 최근 초안이 어떤 판정을 받았는지 본다.
import { empty, h, pill, safeLink, table, viewHead } from "../ui/dom.js";
import { minute } from "../ui/format.js";

const TONE = { "통과": "accent", "검증 대기": "warn", "보류(확인 필요)": "bad", "보류(다시 쓸 예정)": "warn" };

export function render(main, model) {
  const rows = model.items.map((item) => h("tr", {}, [
    h("td", { class: "num", text: minute(item.writtenAt) }),
    h("td", {}, [safeLink(item.link, item.title || item.id) || h("span", { text: item.title || item.id }), h("p", { class: "count", text: `${item.sourceName || ""} · ${item.kind || ""} · 중요도 ${item.importance || ""}${item.excerpt ? " · 원문 발췌 있음" : ""}` })]),
    h("td", {}, pill(item.state, TONE[item.state])),
    h("td", { text: item.verdict ? `${item.verdict.gate || ""} ${item.verdict.why || ""} ${item.verdict.factNote || ""}`.trim() : "" }),
  ]));
  main.replaceChildren(
    viewHead("초안과 판정", "최근 초안 300건까지 보여 줍니다."),
    rows.length ? table([{ text: "작성", num: true }, "항목", "상태", "판정 사유"], rows) : empty("아직 초안이 없습니다."),
  );
}
