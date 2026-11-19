// 입법 절차 화면의 '절차'. 절차 하나를 고르면 그 절차의 풀이, 기관별 줄 그림, 단계마다의 풀이와 근거, 그 절차를 따르는 규제를 보여 준다.
import { current, kindOf, lanes, shortName } from "../../procedure/model.js";
import { cites, whoChips } from "../../procedure/parts.js";
import { h, unsplit } from "../../ui/dom.js";

// 기관별 줄 그림: 기관마다 세로줄 하나, 단계는 그 일을 하는 기관의 줄에 놓인다. 같은 때에 따로 나아가는 단계는 같은 높이에 나란히 놓인다.
// 아래의 단계 목록과 같은 내용이므로 화면 낭독기에는 읽히지 않게 한다.
function laneFigure(book, kind) {
  if (!(kind.lanes || []).length) return null;
  const plan = lanes(kind);
  const names = new Map(book.institutions.map((one) => [one.key, one.name]));
  const number = new Map(kind.steps.map((step, index) => [step.key, index + 1]));
  return h("div", { class: "lanes", "aria-hidden": "true", style: `--lanes:${plan.lanes.length}` }, [
    ...plan.lanes.map((key, index) => h("div", { class: "lane-head", "data-who": key, style: `grid-column:${index + 1}`, text: names.get(key) || key })),
    ...plan.lanes.map((key, index) => h("div", { class: "lane-line", style: `grid-column:${index + 1};grid-row:2 / span ${plan.rows}` })),
    ...plan.cells.map((cell) => h("div", {
      class: "lane-cell", "data-wide": cell.wide ? "true" : null, "data-optional": cell.step.optional ? "true" : null,
      style: `grid-column:${cell.from} / ${cell.to};grid-row:${cell.row + 1} / span ${cell.span}`,
    }, [h("span", { class: "lane-n", text: number.get(cell.step.key) }), h("span", { text: cell.wide ? cell.step.name : shortName(cell.step) })])),
  ]);
}

// 이 절차를 따르는 규제와 그 규제가 지금 서 있는 단계
function followers(kind, rules) {
  const mine = rules.filter((rule) => rule.progress && rule.progress.kind === kind.key);
  if (!mine.length) return null;
  return h("div", { class: "kind-rules" }, [
    h("strong", { text: "이 절차를 따르는 규제" }),
    h("ul", {}, mine.map((rule) => {
      const where = current(kind, rule);
      return h("li", { "data-tone": rule.tone || "progress" }, [
        h("a", { href: `#rules-${rule.id}` }, unsplit(rule.name)),
        h("span", { class: "stage-chip", "data-tone": rule.tone || "progress", text: rule.stage }),
        where.names.length ? h("span", { class: "kind-rule-now", text: `${where.label}: ${where.names.join(", ")}` }) : null,
      ]);
    })),
  ]);
}

function stepRow(book, kind, step, index, before) {
  return h("li", { class: "ps", id: `pr-step-${kind.key}-${step.key}`, tabindex: "-1", "data-optional": step.optional ? "true" : null }, [
    !before || before.part !== step.part ? h("span", { class: "ps-part", text: step.part }) : null,
    h("span", { class: "ps-dot", "aria-hidden": "true", text: index + 1 }),
    h("div", { class: "ps-body" }, [
      h("div", { class: "ps-head" }, [
        h("strong", { class: "ps-name", text: step.name }),
        step.optional ? h("span", { class: "ps-optional", text: "절차에 따라 없을 수 있음" }) : null,
        whoChips(book, step),
      ]),
      h("p", { class: "ps-text", text: step.text }),
      cites(book, step.basis),
    ]),
  ]);
}

function panel(book, kind, rules) {
  return h("article", { class: "kind stack", id: `pr-kind-${kind.key}` }, [
    h("header", { class: "kind-head" }, [h("h3", { text: kind.name }), h("span", { class: "act-en", lang: "en", text: kind.en })]),
    h("div", { class: "kind-lead" }, [h("p", { text: kind.lead.text }), cites(book, kind.lead.basis)]),
    followers(kind, rules),
    laneFigure(book, kind),
    h("ol", { class: "ps-list guide" }, kind.steps.map((step, index) => stepRow(book, kind, step, index, kind.steps[index - 1]))),
    (kind.notes || []).length ? h("div", { class: "kind-notes" }, kind.notes.map((note) => h("section", { class: "kind-note" }, [
      h("h4", { text: note.title }), h("p", { text: note.text }), cites(book, note.basis),
    ]))) : null,
  ]);
}

// picked: 보여 줄 절차의 이름(없거나 모르는 이름이면 첫 절차)
export function kinds(book, picked, rules) {
  const kind = kindOf(book, picked) || book.kinds[0];
  return h("section", { class: "stack proc-sec", id: "pr-kinds", tabindex: "-1", "aria-labelledby": "h-pr-kinds" }, [
    h("div", { class: "sec-head" }, [h("h2", { id: "h-pr-kinds", text: "절차: 어떤 차례로 만들어지는지" }), h("span", { class: "count", text: `${book.kinds.length}가지` })]),
    h("p", { class: "sec-lead", text: "절차를 고르면 단계마다 누가 무엇을 하는지와 근거를 볼 수 있습니다." }),
    h("nav", { class: "kind-tabs", "aria-label": "절차 고르기" }, book.kinds.map((one) =>
      h("a", { href: `#procedure-${one.key}`, "aria-current": one.key === kind.key ? "true" : null, text: one.name }))),
    panel(book, kind, rules),
  ]);
}
