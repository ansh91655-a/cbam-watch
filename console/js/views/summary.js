// 오늘 상태. 조치가 필요한 것을 먼저 보여 준다.
import { empty, h, pill, table, viewHead } from "../ui/dom.js";
import { minute } from "../ui/format.js";
import { latest, today } from "../model.js";

const KIND = { collect: "수집·작성", verify: "검증·게시", report: "실행 확인과 보고" };

function runRow(run, kind) {
  if (!run) return h("tr", {}, [h("td", { text: KIND[kind] }), h("td", { colspan: "3" }, pill("기록 없음", "warn"))]);
  const problems = (run.problems || []).length;
  const counts = Object.entries(run.counts || {}).map(([key, value]) => `${key} ${value}`).join(", ");
  return h("tr", {}, [
    h("td", { text: KIND[kind] }),
    h("td", { class: "num", text: minute(run.startedAt) }),
    h("td", { text: counts }),
    h("td", {}, problems ? pill(`문제 ${problems}건`, "bad") : pill("문제 없음", "accent")),
  ]);
}

export function render(main, model) {
  const day = today();
  const todays = model.runs.filter((run) => String(run.startedAt || "").startsWith(day));
  const problems = [...new Set(todays.flatMap((run) => run.problems || []))];
  const holds = model.items.filter((item) => item.state === "보류");
  const waiting = model.items.filter((item) => item.state === "검증 대기");
  const report = latest(model.runs, "report");
  const tiles = h("div", { class: "filters" }, [
    h("div", { class: "panel figure" }, [h("p", { class: "value", text: String(problems.length) }), h("p", { class: "label", text: "오늘의 문제" })]),
    h("div", { class: "panel figure" }, [h("p", { class: "value", text: String(holds.length) }), h("p", { class: "label", text: "보류 중인 항목" })]),
    h("div", { class: "panel figure" }, [h("p", { class: "value", text: String(waiting.length) }), h("p", { class: "label", text: "검증 대기" })]),
    h("div", { class: "panel figure" }, [h("p", { class: "value", text: String(model.items.filter((item) => item.state === "통과").length) }), h("p", { class: "label", text: "통과한 항목(최근 300건 안)" })]),
  ]);
  main.replaceChildren(
    viewHead("오늘 상태", report ? `마지막 보고 ${minute(report.startedAt)}: ${report.ok ? "정상" : "문제 있음"}` : "아직 보고 실행의 기록이 없습니다."),
    tiles,
    h("section", { class: "stack" }, [h("h2", { text: "오늘의 문제" }), problems.length ? h("ul", { class: "plain-list" }, problems.map((text) => h("li", { text }))) : empty("오늘 기록된 문제가 없습니다.")]),
    h("section", { class: "stack" }, [h("h2", { text: "가장 최근 실행" }), table(["실행", { text: "시작", num: true }, "건수", "문제"], ["collect", "verify", "report"].map((kind) => runRow(latest(model.runs, kind), kind)))]),
  );
}
