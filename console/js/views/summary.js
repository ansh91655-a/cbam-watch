// 오늘 상태. 사람이 봐야 하는 것을 먼저 보여 준다.
import { empty, h, pill, table } from "../ui/dom.js";
import { viewHead } from "../ui/head.js";
import { countsText, minute } from "../ui/format.js";
import { isHold, latest, needsEyes, today, willRetry } from "../model.js";

const KIND = { collect: "수집·작성", verify: "검증·게시", report: "실행 확인과 보고", weekly: "주간 작업", adhoc: "임시 작업" };
const REGULAR = ["collect", "verify", "report", "weekly"]; // 정해진 때에 도는 실행. 기록이 없으면 '기록 없음'으로 보인다

// 가장 최근 실행의 줄들. 임시 작업은 돈 적이 있을 때만 줄을 더한다.
function runRows(runs) {
  const adhoc = latest(runs, "adhoc");
  return [...REGULAR.map((kind) => runRow(latest(runs, kind), kind)), ...(adhoc ? [runRow(adhoc, "adhoc")] : [])];
}

function runRow(run, kind) {
  if (!run) return h("tr", {}, [h("td", { text: KIND[kind] }), h("td", { colspan: "3" }, pill("기록 없음", "warn"))]);
  const problems = (run.problems || []).length;
  return h("tr", {}, [
    h("td", { text: KIND[kind] }),
    h("td", { class: "num", text: minute(run.startedAt) }),
    h("td", { text: countsText(run.counts) }),
    h("td", {}, problems ? pill(`문제 ${problems}건`, "bad") : pill("문제 없음", "accent")),
  ]);
}

function tile(value, label) {
  return h("div", { class: "panel figure" }, [h("p", { class: "value", text: String(value) }), h("p", { class: "label", text: label })]);
}

export function render(main, model) {
  const day = today();
  const todays = model.runs.filter((run) => String(run.startedAt || "").startsWith(day));
  const problems = [...new Set(todays.flatMap((run) => run.problems || []))];
  const eyes = model.items.filter(needsEyes);
  const retry = model.items.filter(willRetry);
  const waiting = model.items.filter((item) => item.state === "검증 대기");
  const mismatches = model.audits.filter((audit) => audit.result === "mismatch");
  const report = latest(model.runs, "report");
  const todo = [
    ...problems.map((text) => h("li", { text })),
    ...eyes.map((item) => h("li", { text: `보류: ${item.title || item.id} (${item.verdict.gate || ""} ${item.verdict.why || ""})` })),
  ];
  main.replaceChildren(
    viewHead("오늘 상태", report ? `마지막 보고 ${minute(report.startedAt)}: ${report.ok ? "정상" : "문제 있음"}` : "아직 보고 실행의 기록이 없습니다."),
    h("div", { class: "filters" }, [
      tile(problems.length, "오늘의 문제"),
      tile(eyes.length, "확인이 필요한 보류"),
      tile(retry.length, "다시 쓰거나 다시 낼 초안"),
      tile(waiting.length, "검증 대기"),
      tile(model.items.filter((item) => item.state === "통과").length, "통과(최근 300건 안)"),
      tile(mismatches.length, "다시 대조에서 어긋남"),
    ]),
    h("section", { class: "stack" }, [h("h2", { text: "확인이 필요한 것" }), todo.length ? h("ul", { class: "plain-list" }, todo) : empty("지금 확인할 것이 없습니다. 보류된 초안 가운데 글을 고치면 풀리는 것은 다음 실행이 한 번 다시 쓰고, 원문을 열지 못한 것은 두 번까지 다시 검증에 냅니다.")]),
    h("section", { class: "stack" }, [h("h2", { text: "가장 최근 실행" }), table(["실행", { text: "시작", num: true }, "건수", "문제"], runRows(model.runs))]),
    h("p", { class: "count", text: `보류 전체 ${model.items.filter(isHold).length}건은 보류함에서 볼 수 있습니다.` }),
  );
}
