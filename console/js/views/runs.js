// 실행 기록.
import { empty, h, pill, table } from "../ui/dom.js";
import { viewHead } from "../ui/head.js";
import { countsText, minute } from "../ui/format.js";

// 메모는 글 하나로 적는 것이 약속이지만, 목록으로 적힌 기록도 읽을 수 있게 한다.
function notesText(notes) {
  return Array.isArray(notes) ? notes.filter(Boolean).join(" · ") : String(notes || "");
}

export function render(main, model) {
  const rows = model.runs.map((run) => h("tr", {}, [
    h("td", {}, [h("span", { text: run.id }), notesText(run.notes) ? h("p", { class: "count", text: notesText(run.notes) }) : null]),
    h("td", { class: "num", text: minute(run.startedAt) }),
    h("td", { class: "num", text: minute(run.finishedAt) }),
    h("td", { text: countsText(run.counts) }),
    h("td", {}, (run.problems || []).length ? [pill(`문제 ${run.problems.length}건`, "bad"), h("ul", { class: "plain-list" }, run.problems.map((text) => h("li", { text })))] : pill("문제 없음", "accent")),
  ]));
  main.replaceChildren(
    viewHead("실행 기록", "최근 실행 120건까지 보여 줍니다."),
    rows.length ? table(["실행", { text: "시작", num: true }, { text: "끝", num: true }, "건수", "문제"], rows) : empty("아직 실행 기록이 없습니다."),
  );
}
