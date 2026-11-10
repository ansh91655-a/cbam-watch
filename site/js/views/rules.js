// 규제. 규제마다 지금 어느 단계에 있는지, 그동안 무슨 일이 있었는지, 다음에 무엇이 남았는지를 보여 준다.
// #rules는 전체 목록, #rules-<묶음>은 한 묶음, #rules-<규제>는 한 규제의 자세한 화면이다.
import * as data from "../data.js";
import { band } from "../ui/band.js";
import { card } from "../ui/card.js";
import { empty, fill, h, safeLink } from "../ui/dom.js";
import { countdown, day, koreanDate } from "../ui/format.js";
import { icon } from "../ui/icons.js";
import { stepper } from "../ui/stepper.js";

function stageChip(rule) {
  return h("span", { class: "stage-chip", "data-tone": rule.tone || "progress", text: rule.stage });
}

function nextLine(rule) {
  if (!rule.next) return null;
  const when = rule.nextDate ? h("time", { datetime: rule.nextDate, text: `${koreanDate(rule.nextDate)} · ${countdown(rule.nextDate)}` }) : null;
  return h("p", { class: "rule-next" }, [h("strong", { text: "다음 단계" }), h("span", { text: rule.next }), when]);
}

function ruleCard(rule) {
  const last = rule.timeline[rule.timeline.length - 1];
  return h("article", { class: "rule-card", "data-tone": rule.tone || "progress" }, [
    h("div", { class: "rule-top" }, [stageChip(rule), h("span", { class: "rule-kind", text: rule.kind })]),
    h("h3", {}, h("a", { href: `#rules-${rule.id}`, text: rule.name })),
    h("p", { class: "rule-official", text: rule.official }),
    rule.path && rule.path.length ? stepper(rule.path, rule.at, true) : null,
    h("p", { class: "rule-status", text: rule.status }),
    nextLine(rule),
    h("p", { class: "rule-foot" }, [
      last ? h("span", { class: "count", text: `최근 ${day(last.date) || last.date}` }) : null,
      h("a", { href: `#rules-${rule.id}`, text: "연혁과 원문 보기" }),
    ]),
  ]);
}

function timeline(rule) {
  return h("ol", { class: "tl" }, [...rule.timeline].reverse().map((event) => {
    const source = safeLink(event.link, event.source);
    if (source) source.append(icon("out", 14));
    return h("li", { "data-press": event.press ? "true" : null }, [
      h("time", { datetime: event.date, text: koreanDate(event.date) || event.date }),
      h("p", { text: event.text }),
      h("p", { class: "tl-src" }, [event.press ? h("span", { class: "tl-press", text: "언론 보도" }) : null, source]),
    ]);
  }));
}

function detail(main, rule, group, items) {
  const related = (rule.relatedItems || []).map((id) => items.find((item) => item.id === id)).filter(Boolean);
  const links = (rule.links || []).map((link) => {
    const node = safeLink(link.url, link.text);
    if (node) node.append(icon("out", 14));
    return node ? h("li", {}, node) : null;
  });
  fill(main,
    band(rule.name, rule.official),
    h("div", { class: "stack-l rule-detail" }, [
      h("p", { class: "crumbs" }, [h("a", { href: "#rules", text: "규제" }), h("span", { text: "›" }), h("a", { href: `#rules-${group.code}`, text: group.name })]),
      h("section", { class: "rule-now", "data-tone": rule.tone || "progress", "aria-labelledby": "h-now" }, [
        h("div", { class: "rule-top" }, [stageChip(rule), h("span", { class: "rule-kind", text: rule.kind })]),
        h("h2", { id: "h-now", text: "현재 상황" }),
        rule.path && rule.path.length ? stepper(rule.path, rule.at, false) : null,
        h("p", { class: "rule-status", text: rule.status }),
        nextLine(rule),
      ]),
      h("section", { class: "stack", "aria-labelledby": "h-what" }, [h("h2", { id: "h-what", text: "무엇을 정하는 규제인가요" }), h("p", { class: "rule-summary", text: rule.summary })]),
      h("section", { class: "stack", "aria-labelledby": "h-tl" }, [
        h("div", { class: "sec-head" }, [h("h2", { id: "h-tl", text: "연혁" }), h("span", { class: "count", text: `${rule.timeline.length}건 · 새 일부터` })]),
        timeline(rule),
      ]),
      links.some(Boolean) ? h("section", { class: "stack", "aria-labelledby": "h-links" }, [h("h2", { id: "h-links", text: "원문과 공식 화면" }), h("ul", { class: "rule-links" }, links)]) : null,
      related.length ? h("section", { class: "stack", "aria-labelledby": "h-rel" }, [
        h("div", { class: "sec-head" }, [h("h2", { id: "h-rel", text: "관련 소식" }), h("a", { href: "#news", text: "소식 전체" })]),
        ...related.map(card),
      ]) : null,
    ]),
  );
}

export async function render(main, arg) {
  const [body, items] = await Promise.all([data.regulations(), data.items()]);
  const rules = body.regulations || [];
  const groups = (body.groups || []).filter((group) => rules.some((rule) => rule.group === group.code));
  if (!rules.length) {
    fill(main, band("규제", "규제마다 지금 어느 단계에 있는지 보여 줍니다."), empty("규제 자료를 읽지 못했습니다. 잠시 뒤에 다시 열어 주세요."));
    return;
  }
  const one = rules.find((rule) => rule.id === arg);
  if (one) {
    detail(main, one, groups.find((group) => group.code === one.group) || { code: "", name: "" }, items);
    return;
  }
  const picked = groups.some((group) => group.code === arg) ? arg : "";
  const shown = groups.filter((group) => !picked || group.code === picked);
  const side = h("nav", { class: "side-nav", "aria-label": "규제 묶음" }, [
    h("a", { href: "#rules", "aria-current": picked ? null : "true" }, [h("span", { class: "chipicon" }, icon("law", 17)), h("span", { text: "전체" }), h("span", { class: "n", text: rules.length })]),
    ...groups.map((group) => h("a", { href: `#rules-${group.code}`, "aria-current": picked === group.code ? "true" : null },
      [h("span", { class: "chipicon" }, icon(group.icon || "legis", 17)), h("span", { text: group.name }), h("span", { class: "n", text: rules.filter((rule) => rule.group === group.code).length })])),
  ]);
  const upcoming = rules.filter((rule) => rule.nextDate && rule.nextDate >= new Date(Date.now() + 9 * 3600000).toISOString().slice(0, 10))
    .sort((a, b) => a.nextDate.localeCompare(b.nextDate)).slice(0, 4);
  const soon = !picked && upcoming.length ? h("section", { class: "rule-soon", "aria-labelledby": "h-soon" }, [
    h("h2", { id: "h-soon", text: "곧 움직일 규제" }),
    h("ul", {}, upcoming.map((rule) => h("li", {}, [
      h("time", { datetime: rule.nextDate, text: koreanDate(rule.nextDate) }),
      h("a", { href: `#rules-${rule.id}`, text: rule.name }),
      h("span", { text: rule.next }),
    ]))),
  ]) : null;
  fill(main,
    band(picked ? `규제: ${shown[0].name}` : "규제", picked ? shown[0].about : `규제마다 지금 어느 단계에 있는지, 다음에 무엇이 남았는지 정리했습니다. ${koreanDate(body.asOf)} 기준입니다.`),
    h("div", { class: "with-side" }, [
      h("aside", { class: "side" }, side),
      h("div", { class: "stack-l" }, [
        soon,
        ...shown.map((group) => h("section", { class: "stack", "aria-labelledby": `h-g-${group.code}` }, [
          h("div", { class: "sec-head" }, [h("h2", { id: `h-g-${group.code}`, text: group.name }), h("span", { class: "count", text: `${rules.filter((rule) => rule.group === group.code).length}건` })]),
          picked ? null : h("p", { class: "sec-lead", text: group.about }),
          h("div", { class: "rule-grid" }, rules.filter((rule) => rule.group === group.code).map(ruleCard)),
        ])),
        h("p", { class: "rule-note", text: "연혁의 각 줄에는 원문 링크를 달았습니다. 공식 발표 없이 언론 보도로만 알려진 일은 '언론 보도'로 표시했습니다. 최종 판단은 원문으로 해 주세요." }),
      ]),
    ]),
  );
}
