// 규제 변화 기록: 규제마다의 연혁을 합쳐 최근 30일·90일에 달라진 것만 날짜가 늦은 것부터 보여 준다(#rules-recent, #rules-recent-90).
// 규제 전체 화면에는 가장 최근의 몇 줄만 싣고(recentBlock) 이 화면으로 잇는다. 무엇을 고르는지는 rules/changes.js에 있다.
import { changes, hrefOf, PERIODS } from "../../rules/changes.js";
import { empty, h, safeLink, unsplit } from "../../ui/dom.js";
import { count, koreanDate, today } from "../../ui/format.js";
import { icon } from "../../ui/icons.js";

const FEW = 4;   // 규제 전체 화면에 싣는 줄 수

function stage(rule) {
  return h("span", { class: "stage-chip", "data-tone": rule.tone || "progress", text: rule.stage });
}

function row(event) {
  const source = safeLink(event.link, event.source);
  if (source) source.append(icon("out", 14));
  return h("li", { "data-press": event.press ? "true" : null }, [
    h("time", { datetime: event.date, text: koreanDate(event.date) || event.date }),
    h("p", { class: "tl-rule" }, [h("a", { href: `#rules-${event.rule.id}` }, unsplit(event.rule.name)), stage(event.rule)]),
    h("p", { text: event.text }),
    h("p", { class: "tl-src" }, [event.press ? h("span", { class: "tl-press", text: "언론 보도" }) : null, source]),
  ]);
}

// 규제 전체 화면의 칸: 최근 30일의 변화 가운데 가장 늦은 몇 줄. 없으면 null.
export function recentBlock(rules) {
  const rows = changes(rules, today(), PERIODS[0]);
  if (!rows.length) return null;
  return h("section", { class: "rule-recent", "aria-labelledby": "h-recent-rules" }, [
    h("div", { class: "sec-head" }, [
      h("h2", { id: "h-recent-rules", text: `최근 ${PERIODS[0]}일에 달라진 것` }),
      h("a", { href: hrefOf(), text: `${count(rows.length)}건 모두 보기` }),
    ]),
    h("ul", {}, rows.slice(0, FEW).map((event) => h("li", {}, [
      h("time", { datetime: event.date, text: koreanDate(event.date) }),
      h("a", { href: `#rules-${event.rule.id}` }, unsplit(event.rule.name)),
      h("span", { text: event.text }),
    ]))),
  ]);
}

// 변화 기록 화면의 본문: 날수 고르기, 연혁의 줄들, 읽을 때 알아 둘 점
export function recentPage(rules, days) {
  const now = today();
  const rows = changes(rules, now, days);
  const touched = new Set(rows.map((event) => event.rule.id)).size;
  return [
    h("nav", { class: "chips", "aria-label": "기간 고르기" }, PERIODS.map((period) =>
      h("a", { class: "chip", href: hrefOf(period), "aria-current": period === days ? "true" : null },
        [h("span", { text: `최근 ${period}일` }), h("span", { class: "n", text: count(changes(rules, now, period).length) })]))),
    h("p", { class: "count", role: "status", text: rows.length ? `규제 ${count(touched)}건에서 ${count(rows.length)}건이 달라졌습니다.` : "" }),
    rows.length ? h("ol", { class: "tl tl-all" }, rows.map(row)) : empty(`최근 ${days}일 동안 달라진 규제가 없습니다.`),
    h("p", { class: "rule-note", text: "규제마다 적어 둔 연혁에서 그 일이 일어난 날짜가 이 기간에 드는 것을 모았습니다. 공식 발표 없이 언론 보도로만 알려진 일은 '언론 보도'로 표시했습니다. 규제의 이름을 누르면 그 규제의 지금 단계와 전체 연혁을 볼 수 있습니다." }),
  ];
}
