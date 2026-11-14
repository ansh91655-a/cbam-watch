// 규제. 규제마다 지금 어느 단계에 있는지, 그동안 무슨 일이 있었는지, 다음에 무엇이 남았는지를 보여 준다.
// #rules는 전체 목록, #rules-<묶음>은 한 묶음, #rules-<규제>는 한 규제의 자세한 화면이다.
// #rules-recent(와 #rules-recent-90)는 연혁을 합쳐 최근에 달라진 것만 보는 화면이다(rules/recent.js).
import { adopted } from "../cn/stage.js";
import * as data from "../data.js";
import { readRule } from "../laws/refs.js";
import { band } from "../ui/band.js";
import { card } from "../ui/card.js";
import { empty, fill, h, safeLink, table, unsplit } from "../ui/dom.js";
import { countdown, day, koreanDate, today } from "../ui/format.js";
import { gloss } from "../ui/gloss.js";
import { icon } from "../ui/icons.js";
import { changes, periodOf, RECENT, sidePeriod } from "../rules/changes.js";
import { findPanel } from "../ui/lawfind.js";
import { stackable } from "../ui/stack.js";
import { stepper } from "../ui/stepper.js";
import { analysis } from "./rules/analysis.js";
import { figure } from "./rules/figure.js";
import { recentBlock, recentPage } from "./rules/recent.js";
import { sideNav } from "./rules/side.js";
import { tool } from "./rules/tool.js";

function stageChip(rule) {
  return h("span", { class: "stage-chip", "data-tone": rule.tone || "progress", text: rule.stage });
}

function nextLine(rule) {
  if (!rule.next) return null;
  const when = rule.nextDate ? h("time", { datetime: rule.nextDate, text: `${koreanDate(rule.nextDate)}, ${countdown(rule.nextDate)}` }) : null;
  return h("p", { class: "rule-next" }, [h("strong", { text: "다음 단계" }), h("span", { text: rule.next }), when]);
}

function ruleCard(rule) {
  const last = rule.timeline[rule.timeline.length - 1];
  return h("article", { class: "rule-card", "data-tone": rule.tone || "progress" }, [
    h("div", { class: "rule-top" }, [stageChip(rule), h("span", { class: "rule-kind", text: rule.kind })]),
    h("h3", {}, h("a", { href: `#rules-${rule.id}` }, unsplit(rule.name))),
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

// 기관별 입장 비교표. 입법 중인 규제에서, 기관마다 낸 안이 쟁점별로 어떻게 다른지 보여 준다. 빈칸은 그 문서에서 확인하지 못한 것이다.
function positions(rule) {
  const book = rule.positions;
  if (!book || !Array.isArray(book.rows) || !book.rows.length) return null;
  const rows = book.rows.map((row) => h("tr", {}, [
    h("th", { scope: "row", text: row.topic }),
    ...book.parties.map((party) => {
      const text = (row[party.key] || {}).text || "";
      return h("td", { class: text ? null : "blank", text: text || "확인된 내용 없음" });
    }),
  ]));
  const wrap = stackable(table(["쟁점", ...book.parties.map((party) => party.name)], rows, "기관별 입장 비교"));
  wrap.classList.add("pos-table");
  const sources = h("ul", { class: "pos-sources" }, book.parties.map((party) => {
    const link = safeLink(party.link, party.source);
    if (link) link.append(icon("out", 13));
    return h("li", {}, [h("strong", { text: party.name }), h("time", { datetime: party.date, text: day(party.date) }), link]);
  }));
  // 표를 만들 때 함께 대조한 문서(예: 기관 간 협상용 대조 문서)
  for (const extra of book.also || []) {
    const link = safeLink(extra.link, extra.text);
    if (!link) continue;
    link.append(icon("out", 13));
    sources.append(h("li", {}, [h("strong", { text: "함께 대조한 문서" }), extra.date ? h("time", { datetime: extra.date, text: day(extra.date) }) : null, link]));
  }
  // 규제가 채택 단계에 들어가면 이 표는 지난 이야기가 된다. 그때는 협상 전의 기록이라고 스스로 밝힌다.
  const past = adopted(rule);
  return h("section", { class: "stack pos-wide", "aria-labelledby": "h-pos" }, [
    h("div", { class: "sec-head" }, [h("h2", { id: "h-pos", text: past ? "기관별 입장 비교(협상 전의 기록)" : "기관별 입장 비교" }), h("span", { class: "count", text: `${day(book.asOf)} 기준` })]),
    past ? h("p", { class: "pos-past", text: `이 규제는 지금 '${rule.stage}' 단계입니다. 아래 표는 협상 전에 각 기관이 낸 안을 기록으로 남긴 것이며, 최종 법령의 내용과 다를 수 있습니다.` }) : null,
    wrap,
    sources,
    h("p", { class: "pos-note", text: book.note }),
  ]);
}

// 오른쪽 칸: 이 규제의 원문과 국문 번역으로 가는 길, 그리고 규정에서 찾기(질문을 적으면 관련 조문의 위치를 알려 준다).
// read: 이 규제를 관련 화면으로 가리킨 해설서의 절들(laws/refs.js의 readRule)
function aside(rule, acts, read) {
  const own = acts.filter((act) => act.rule === rule.id);
  return h("aside", { class: "rule-aside", "aria-label": "규정 원문과 해설서" }, [
    own.length ? h("div", { class: "law-open" }, [
      h("strong", { text: "원문과 국문 번역" }),
      h("p", { text: "조문마다 원문과 번역을 나란히 봅니다." }),
      ...own.map((act) => h("a", { href: `#law-${act.id}` }, [h("span", { text: act.name }), icon("next", 15)])),
    ]) : null,
    read.length ? h("div", { class: "law-open" }, [
      h("strong", { text: "해설서에서 읽기" }),
      h("p", { text: "이 규제가 다루는 내용을 제도의 차례에 맞춰 풀어 쓴 절입니다." }),
      ...read.map((one) => h("a", { href: one.href }, [h("span", { text: one.title }), icon("next", 15)])),
    ]) : null,
    findPanel({ examples: ["인증서 제출 기한", "내재배출량 검증", "기본값"] }),
  ]);
}

function detail(main, rule, group, items, drawing, acts, read) {
  const related = (rule.relatedItems || []).map((id) => items.find((item) => item.id === id)).filter(Boolean);
  const links = (rule.links || []).map((link) => {
    const node = safeLink(link.url, link.text);
    if (node) node.append(icon("out", 14));
    return node ? h("li", {}, node) : null;
  });
  fill(main,
    band(rule.name, rule.official),
    h("div", { class: "rule-page" }, [h("div", { class: "stack-l rule-detail", "data-reading": "" }, [  // 긴 글 화면: 머리글에 읽는 자리 표시가 보인다(ui/scrollcue.js)
      h("p", { class: "crumbs" }, [h("a", { href: "#rules", text: "규제" }), h("span", { text: "›" }), h("a", { href: `#rules-${group.code}`, text: group.name })]),
      h("section", { class: "rule-now", "data-tone": rule.tone || "progress", "aria-labelledby": "h-now" }, [
        h("div", { class: "rule-top" }, [stageChip(rule), h("span", { class: "rule-kind", text: rule.kind })]),
        h("h2", { id: "h-now", text: "현재 상황" }),
        rule.path && rule.path.length ? stepper(rule.path, rule.at, false) : null,
        h("p", { class: "rule-status", text: rule.status }),
        nextLine(rule),
      ]),
      h("section", { class: "stack", "aria-labelledby": "h-what" }, [
        h("h2", { id: "h-what", text: "무엇을 정하는 규제인가요" }),
        h("p", { class: "rule-summary", text: rule.summary }),
        analysis(rule),  // 배경, 주요 내용, 쟁점과 정세, 실무에서 볼 점(분석 글이 있는 규제만)
      ]),
      drawing,  // 규제에 딸린 그림(있는 규제만)
      tool(rule),  // 이 규제의 값으로 계산해 보는 도구(있는 규제만)
      positions(rule),
      h("section", { class: "stack", "aria-labelledby": "h-tl" }, [
        h("div", { class: "sec-head" }, [h("h2", { id: "h-tl", text: "연혁" }), h("span", { class: "count", text: `${rule.timeline.length}건, 새 일부터` })]),
        timeline(rule),
      ]),
      links.some(Boolean) ? h("section", { class: "stack", "aria-labelledby": "h-links" }, [h("h2", { id: "h-links", text: "원문과 공식 화면" }), h("ul", { class: "rule-links" }, links)]) : null,
      related.length ? h("section", { class: "stack", "aria-labelledby": "h-rel" }, [
        h("div", { class: "sec-head" }, [h("h2", { id: "h-rel", text: "관련 소식" }), h("a", { href: "#news", text: "소식 전체" })]),
        ...related.map(card),
      ]) : null,
    ]), aside(rule, acts, read)]),
  );
  // 현재 상황, 요약, 분석의 글에 나온 용어에 풀이를 단다(근거 자료의 목록과 연혁에는 달지 않는다).
  // 묶음의 이름이 용어의 범위와 같은 규제(영국 CBAM)에는 그 범위의 풀이를 단다
  gloss(main, ".rule-now .rule-status, .rule-summary, .rule-analysis .an-sec:not(.an-src) p", { scope: rule.group });
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
    detail(main, one, groups.find((group) => group.code === one.group) || { code: "", name: "" }, items, await figure(one), await data.laws(), readRule(await data.refs(), one.id));
    return;
  }
  const days = periodOf(arg);
  const sideDays = sidePeriod(arg);                          // 왼쪽의 '최근 변화'가 가리키는 날수(변화 기록을 보고 있으면 보고 있는 날수)
  const recent = changes(rules, today(), sideDays).length;   // 거기에 적는 건수
  if (days) {
    fill(main,
      band("규제: 최근 변화", `규제 ${rules.length}건의 연혁에서 최근 ${days}일 동안 달라진 것만 날짜순으로 모았습니다.`),
      h("div", { class: "with-side" }, [h("aside", { class: "side" }, sideNav(rules, groups, RECENT, recent, sideDays)), h("div", { class: "stack-l" }, recentPage(rules, days))]),
    );
    return "규제: 최근 변화";
  }
  const picked = groups.some((group) => group.code === arg) ? arg : "";
  const shown = groups.filter((group) => !picked || group.code === picked);
  const side = sideNav(rules, groups, picked, recent, sideDays);
  const upcoming = rules.filter((rule) => rule.nextDate && rule.nextDate >= today())
    .sort((a, b) => a.nextDate.localeCompare(b.nextDate)).slice(0, 4);
  const soon = !picked && upcoming.length ? h("section", { class: "rule-soon", "aria-labelledby": "h-soon" }, [
    h("h2", { id: "h-soon", text: "곧 움직일 규제" }),
    h("ul", {}, upcoming.map((rule) => h("li", {}, [
      h("time", { datetime: rule.nextDate, text: koreanDate(rule.nextDate) }),
      h("a", { href: `#rules-${rule.id}` }, unsplit(rule.name)),
      h("span", { text: rule.next }),
    ]))),
  ]) : null;
  fill(main,
    band(picked ? `규제: ${shown[0].name}` : "규제", picked ? shown[0].about : `규제마다 지금 어느 단계에 있는지, 다음에 무엇이 남았는지 정리했습니다. ${koreanDate(body.asOf)} 기준입니다.`),
    h("div", { class: "with-side" }, [
      h("aside", { class: "side" }, side),
      h("div", { class: "stack-l" }, [
        picked ? null : h("div", { class: "rule-heads" }, [soon, recentBlock(rules)]),
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
