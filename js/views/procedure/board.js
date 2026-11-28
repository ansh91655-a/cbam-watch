// 입법 절차 화면의 '진행 중인 규제의 현재 단계'. 절차가 끝나지 않은 규제마다 따르는 절차, 지나온 단계, 지금 서 있는 단계, 다음 일정을 한 줄로 보여 준다.
import { current, dots, kindOf, ongoing } from "../../procedure/model.js";
import { dotTrack } from "../../procedure/parts.js";
import { h, unsplit } from "../../ui/dom.js";
import { countdown, koreanDate } from "../../ui/format.js";

function row(book, rule) {
  const kind = kindOf(book, rule.progress.kind);
  if (!kind) return null;
  const where = current(kind, rule);
  const label = `주요 단계 ${rule.progress.total}개 가운데 ${rule.progress.passed}개를 지남`;
  return h("li", { class: "board-row", "data-tone": rule.tone || "progress" }, [
    h("div", { class: "board-name" }, [
      h("a", { href: `#rules-${rule.id}` }, unsplit(rule.name)),
      h("a", { class: "board-kind", href: `#procedure-${kind.key}`, text: kind.name }),
    ]),
    h("div", { class: "board-track" }, [
      dotTrack(dots(kind, rule), label),
      h("span", { class: "board-count", text: `${rule.progress.passed}/${rule.progress.total}` }),
    ]),
    h("p", { class: "board-now" }, where.names.length ? [h("em", { text: where.label }), h("span", { text: where.names.join(", ") })] : null),
    h("p", { class: "board-next" }, rule.nextDate
      ? [h("time", { datetime: rule.nextDate, text: koreanDate(rule.nextDate) }), h("span", { text: `${rule.nextTitle || rule.next} (${countdown(rule.nextDate)})` })]
      : [h("span", { text: rule.next || "다음 일정이 정해지지 않았습니다." })]),
  ]);
}

export function board(book, rules) {
  const rows = ongoing(rules).map((rule) => row(book, rule)).filter(Boolean);
  if (!rows.length) return null;
  return h("section", { class: "stack proc-sec", id: "pr-board", tabindex: "-1", "aria-labelledby": "h-pr-board" }, [
    h("div", { class: "sec-head" }, [h("h2", { id: "h-pr-board", text: "진행 중인 규제의 현재 단계" }), h("span", { class: "count", text: `${rows.length}건` })]),
    h("p", { class: "sec-lead", text: "절차가 끝나지 않은 규제를 모았습니다. 점 하나가 그 절차의 주요 단계 하나이고, 채워진 점이 지나온 단계입니다. 규제의 이름을 누르면 단계마다의 날짜와 근거를 볼 수 있습니다." }),
    h("ul", { class: "board" }, rows),
  ]);
}
