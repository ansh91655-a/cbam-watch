// 실행 기록.
import { empty, h, pill, table, viewHead } from "../ui/dom.js";
import { minute } from "../ui/format.js";

export function render(main, model) {
  const rows = model.runs.map((run) => h("tr", {}, [
    h("td", { text: run.id }),
    h("td", { class: "num", text: minute(run.startedAt) }),
    h("td", { class: "num", text: minute(run.finishedAt) }),
    h("td", { text: Object.entries(run.counts || {}).map(([key, value]) => `${key} ${value}`).join(", ") }),
    h("td", {}, (run.problems || []).length ? [pill(`문제 ${run.problems.length}건`, "bad"), h("ul", { class: "plain-list" }, run.problems.map((text) => h("li", { text })))] : pill("문제 없음", "accent")),
  ]));
  main.replaceChildren(
    viewHead("실행 기록", "최근 실행 120건까지 보여 줍니다."),
    rows.length ? table(["실행", { text: "시작", num: true }, { text: "끝", num: true }, "건수", "문제"], rows) : empty("아직 실행 기록이 없습니다."),
  );
}
