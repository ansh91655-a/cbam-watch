// 규제 화면의 '세부 절차'. 큰 단계 표시(ui/stepper.js)보다 잘게, 그 규제가 따르는 절차의 단계마다 마쳤는지, 언제 무슨 일이 있었는지, 무엇이 남았는지를 보여 준다.
// 단계의 뜻과 하는 기관은 입법 절차의 자료(data/procedures.json)에서, 단계마다의 상태는 규제 자료의 진행도(progress)에서 온다.
// 절차가 적혀 있지 않은 규제에는 아무것도 그리지 않는다. 셈은 js/procedure/model.js, 함께 쓰는 조각은 js/procedure/parts.js, 모양은 css/procedure.css다.
import { current, dots, kindOf, STATES, stepsOf, summary } from "../../procedure/model.js";
import { dotTrack, stateMark, whoChips } from "../../procedure/parts.js";
import { h, safeLink } from "../../ui/dom.js";
import { koreanDate } from "../../ui/format.js";
import { icon } from "../../ui/icons.js";

// 그 단계에서 일어난 일(연혁의 줄). 언론 보도로만 아는 일은 그렇다고 표시한다.
function events(step) {
  if (!step.events.length) return null;
  return h("ul", { class: "ps-events" }, step.events.map((event) => {
    const source = safeLink(event.link, event.source);
    if (source) source.append(icon("out", 12));
    return h("li", { "data-press": event.press ? "true" : null }, [
      h("time", { datetime: event.date, text: koreanDate(event.date) || event.date }),
      h("span", { class: "ps-event-text", text: event.text }),
      h("span", { class: "ps-event-src" }, [event.press ? h("span", { class: "tl-press", text: "언론 보도" }) : null, source]),
    ]);
  }));
}

function stepRow(book, kind, step, before) {
  const open = step.state === "now" || step.state === "next";   // 지금 서 있는 단계는 뜻을 펼쳐 둔다
  return h("li", { class: "ps", "data-state": step.state, "aria-current": step.state === "now" ? "step" : null }, [
    !before || before.part !== step.part ? h("span", { class: "ps-part", text: step.part }) : null,
    h("span", { class: "ps-dot", "aria-hidden": "true" }),
    h("div", { class: "ps-body" }, [
      h("div", { class: "ps-head" }, [h("strong", { class: "ps-name", text: step.name }), stateMark(step.state), whoChips(book, step)]),
      events(step),
      step.note ? h("p", { class: "ps-note", text: step.note }) : null,
      step.state === "none" ? h("p", { class: "ps-none", text: "이 단계의 날짜는 연혁에 없습니다." }) : null,
      h("details", { class: "ps-what", open: open || null }, [
        h("summary", { text: "이 단계에서 하는 일" }),
        h("p", { text: step.text }),
        h("a", { href: `#procedure-${kind.key}.${step.key}`, text: "절차 안내에서 근거와 함께 보기" }),
      ]),
    ]),
  ]);
}

// 이 규제에 나온 상태만 골라 뜻을 적는다
function legend(steps) {
  const order = ["done", "now", "next", "todo", "none"];
  const words = {
    done: "마친 단계", now: "지금 와 있는 단계", next: "이어서 올 단계",
    todo: "아직 기록이 없는 단계", none: "지나갔지만 연혁에 날짜가 없는 단계",
  };
  const seen = order.filter((state) => steps.some((step) => step.state === state));
  return h("ul", { class: "ps-legend", "aria-label": "표시의 뜻" }, seen.map((state) =>
    h("li", {}, [h("span", { class: "ps-pt", "data-state": state, "aria-hidden": "true" }), h("strong", { text: STATES[state] }), h("span", { text: words[state] })])));
}

// rule: 규제 하나(progress가 있을 때만 그린다), book: 입법 절차의 자료
export function steps(rule, book) {
  const kind = rule.progress ? kindOf(book, rule.progress.kind) : null;
  if (!kind) return null;
  const rows = stepsOf(kind, rule);
  const where = current(kind, rule);
  const list = h("ol", { class: "ps-list" }, rows.map((step, index) => stepRow(book, kind, step, rows[index - 1])));
  const label = where.names.length ? `${where.label} 단계: ${where.names.join(", ")}` : "모든 단계를 지남";
  return h("section", { class: "stack rule-steps", "data-tone": rule.tone || "progress", "aria-labelledby": "h-steps" }, [
    h("div", { class: "sec-head" }, [h("h2", { id: "h-steps", text: "세부 절차" }), h("a", { href: `#procedure-${kind.key}`, text: `${kind.name} 안내` })]),
    h("div", { class: "ps-top" }, [
      h("p", { class: "ps-kind" }, [h("span", { text: "따르는 절차" }), h("strong", { text: kind.name })]),
      dotTrack(dots(kind, rule), `주요 단계 ${rule.progress.total}개 가운데 ${rule.progress.passed}개를 지남. ${label}`),
      h("p", { class: "ps-lead", text: summary(kind, rule) }),
      rule.progress.note ? h("p", { class: "ps-remark", text: rule.progress.note }) : null,
    ]),
    // 절차를 모두 마친 규제는 접어 둔다(지난 일이다). 진행 중인 규제는 펼쳐 둔다.
    rule.progress.finished
      ? h("details", { class: "ps-fold" }, [h("summary", { text: `단계 ${rows.length}개 펼쳐 보기` }), list, legend(rows)])
      : h("div", { class: "ps-open" }, [list, legend(rows)]),
  ]);
}

// 규제 목록의 카드에 적는 한 줄: 따르는 절차와 지금 서 있는 곳. 절차가 없으면 null.
export function stepLine(rule, book) {
  const kind = rule.progress ? kindOf(book, rule.progress.kind) : null;
  if (!kind) return null;
  const where = current(kind, rule);
  const tail = rule.progress.finished ? "모든 단계를 지남" : `${rule.progress.total}단계 가운데 ${rule.progress.passed}단계를 지남`;
  return h("p", { class: "rule-fine" }, [
    h("span", { class: "rule-fine-kind", text: kind.name }),
    h("span", { text: tail }),
    where.names.length ? h("span", { class: "rule-fine-now" }, [h("em", { text: where.label }), h("span", { text: where.names.join(", ") })]) : null,
  ]);
}
