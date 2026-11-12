// 다시 대조. 게시한 항목을 주마다 골라 원문과 다시 견준 결과.
import { empty, h, pill, table } from "../ui/dom.js";
import { viewHead } from "../ui/head.js";
import { minute } from "../ui/format.js";

const LABEL = { match: "일치", mismatch: "어긋남", unknown: "확인 불가" };
const TONE = { match: "accent", mismatch: "bad", unknown: "warn" };

export function render(main, model) {
  const rows = model.audits.map((audit) => h("tr", {}, [
    h("td", { class: "num", text: minute(audit.at) }),
    h("td", { text: audit.week || "" }),
    h("td", { text: audit.itemId || audit.id }),
    h("td", {}, pill(LABEL[audit.result] || audit.result || "", TONE[audit.result])),
    h("td", { text: audit.why || "" }),
  ]));
  main.replaceChildren(
    viewHead("다시 대조", "월요일마다 지난주에 게시한 항목 가운데 몇 건을 골라 지금의 원문과 다시 견줍니다. 어긋난 항목은 요약을 내립니다."),
    rows.length ? table([{ text: "대조", num: true }, "주", "항목", "결과", "사유"], rows) : empty("아직 다시 대조한 기록이 없습니다. 첫 주간 작업은 월요일 09:10에 돕니다."),
  );
}
