// 사이트 검색. 찾는 말 하나로 소식, 규제, 용어집, 일정, 품목 코드, 원문 대장, 규정 원문을 한 번에 찾아 갈래별로 보여 준다.
// 주소는 #search-찾는 말이다(결과를 주소로 남겨 뒤로 가기와 공유가 되게 한다). 머리글의 검색 칸(ui/sitesearch.js)이 이 화면으로 보낸다.
// 찾는 일은 js/search/의 모듈이, 구역과 결과 한 줄을 그리는 일은 views/search/의 모듈이 한다. 여기에서는 무엇을 보여 줄지와 갈래 고르기만 맡는다.
import * as data from "../data.js";
import { makeIndex, marks, parse } from "../laws/engine.js";
import { visit } from "../router.js";
import { codeVerdict, codeWords } from "../search/codes.js";
import { gather, keep, KINDS, missing, needed, rank, reach } from "../search/find.js";
import { findPages } from "../search/pages.js";
import * as rows from "../search/rows.js";
import { band } from "../ui/band.js";
import { empty, fill, h } from "../ui/dom.js";
import { count, today } from "../ui/format.js";
import { icon } from "../ui/icons.js";
import { corpus, guideCorpus, understood } from "../ui/lawfind.js";
import { decode, target } from "../ui/sitesearch.js";
import { examples, lawSection, lawShown, NAMES, section, settle, shortcuts } from "./search/sections.js";

// 모든 갈래를 함께 볼 때 갈래마다 보여 주는 줄 수
const FEW = { terms: 3, rules: 4, news: 5, dates: 3, codes: 3, files: 3, laws: 2, acts: 3, guides: 3 };
const PAGE = 40;       // 갈래 하나만 볼 때 한 번에 보여 주는 줄 수
const PARTS = 30;      // 갈래 하나만 볼 때 보여 주는 조문의 수(나머지는 규정 원문 화면에서 본다)
const WAIT_MS = 300;   // 규정의 글을 이만큼 기다렸다가, 아직이면 먼저 찾은 것부터 보여 준다

const pause = (ms) => new Promise((resolve) => { setTimeout(resolve, ms); });

// 게시 데이터를 읽어 찾기 좋은 줄로 바꿔 둔다. 한 번만 한다.
let loaded = null;
function book() {
  if (!loaded) {
    loaded = Promise.all([data.items(), data.regulations(), data.terms(), data.events(), data.duties(), data.cn(), data.documents(), data.laws()])
      .then(([items, rules, terms, events, duties, cn, documents, acts]) => ({
        index: makeIndex(terms),
        cn,
        ruleGroups: new Map((rules.groups || []).map((group) => [group.code, group.name])),
        actNames: Object.fromEntries(acts.map((act) => [act.id, act.name])),
        rows: {
          news: rows.newsRows(items), rules: rows.ruleRows(rules), terms: rows.termRows(terms), dates: rows.dateRows(events, duties.duties),
          codes: rows.codeRows(cn), files: rows.fileRows(documents, acts), laws: rows.lawRows(acts),
        },
      }));
  }
  return loaded;
}

// 규정 원문의 글(법령, 안내 문서)에서 찾는다. 글이 크므로 다른 갈래를 먼저 보여 주고 나서 더한다.
async function parts(parsed) {
  const [acts, guides] = await Promise.all([corpus(), guideCorpus()]);
  return { acts: rank(acts.rows, parsed), guides: rank(guides.rows, parsed) };
}

// 같은 말로 다시 왔을 때(뒤로 가기) 보던 갈래를 돌려놓으려고 기억해 둔다. 브라우저에 저장하지는 않는다.
const last = { query: "", pick: "all" };

// 찾은 것이 없을 때의 말: [굵게 적을 말, 덧붙일 말]
function nothingWords(query, hasWords, hasPages) {
  if (hasPages) return [`‘${query}’에 맞는 화면이 있습니다.`, hasWords ? "글에서는 찾지 못했습니다." : "흔히 쓰는 낱말이어서 글에서는 찾지 않습니다."];
  if (!hasWords) return ["찾을 낱말을 읽지 못했습니다.", ""];
  return [`‘${query}’에 맞는 내용을 찾지 못했습니다.`, ""];
}

async function results(out, query) {
  fill(out, h("p", { class: "count", role: "status", text: "찾는 중입니다." }));
  const { index, cn, ruleGroups, actNames, rows: mine } = await book();
  const code = codeVerdict(query, cn);
  const parsed = code ? { query, groups: [codeWords(code.code)] } : parse(query, index);  // 품목 코드는 자리마다 나누지 않고 낱말 하나로 찾는다
  const context = { needles: marks(parsed), ruleGroups, actNames };
  const pages = findPages(query);
  const found = gather(parsed, mine, { today: today() });
  const state = { extra: null, pick: last.query === query ? last.pick : "all", shown: PAGE };
  last.query = query;

  const status = h("p", { class: "search-status", role: "status" });
  const tabs = h("div", { class: "search-tabs", role: "group", "aria-label": "갈래 고르기" });
  const body = h("div", { class: "search-body" });

  // 갈래를 고른다. 자판으로 골랐을 때 초점이 사라지지 않게, 고른 갈래의 단추로 초점을 옮긴다.
  function choose(kind) {
    state.pick = kind;
    state.shown = PAGE;
    draw();
    const chip = tabs.querySelector(`[data-kind="${kind}"]`);
    if (chip) chip.focus();
  }

  // 갈래 하나를 볼 때 줄을 더 보여 준다. 새로 보인 첫 줄로 초점을 옮긴다.
  function further(kind) {
    const from = state.shown;
    state.shown += PAGE;
    draw();
    const next = body.querySelectorAll(".search-list > li")[from];
    const link = next && next.querySelector("a");
    if (link) link.focus();
  }

  function draw() {
    if (!out.isConnected) return;  // 규정의 글을 읽는 사이에 다른 화면으로 갔으면 그리지 않는다(보던 갈래의 기억도 건드리지 않는다)
    const waiting = !state.extra && parsed.groups.length > 0;
    const all = { ...found, ...(state.extra || {}) };
    let need = needed(parsed);
    let kept = keep(all, need);
    let loosened = false;
    if (!code && !waiting && !Object.values(kept).some((hits) => hits.length)) {
      const best = reach(all);  // 낱말이 함께 나오는 곳이 없으면 낱말이 가장 많이 나오는 곳으로 물러선다
      if (best > 0 && best < need) {
        need = best;
        kept = keep(all, need);
        loosened = true;
      }
    }
    const counts = Object.fromEntries(KINDS.map((kind) => [kind, kept[kind].length]));
    counts.codes += code ? 1 : 0;
    counts.laws += (kept.acts || []).length + (kept.guides || []).length;
    const total = Object.values(counts).reduce((sum, value) => sum + value, 0);
    const order = code ? ["codes", ...KINDS.filter((kind) => kind !== "codes")] : KINDS;
    const present = order.filter((kind) => counts[kind] > 0);
    if (state.pick !== "all" && !counts[state.pick]) state.pick = "all";
    last.pick = state.pick;
    const one = state.pick !== "all";
    const nothing = !total && !waiting;

    // 몇 건을 찾았는지
    const gone = waiting ? [] : missing(parsed, all);
    const [lead, note] = nothing ? nothingWords(query, parsed.groups.length > 0, pages.length > 0) : [`‘${query}’ ${count(total)}건`, ""];
    fill(status,
      h("strong", { text: lead }),
      note ? h("span", { text: note }) : null,
      waiting ? h("span", { text: "규정 원문에서는 찾는 중입니다." }) : null,
      loosened ? h("span", { text: "낱말이 모두 함께 나오는 곳이 없어, 낱말의 일부가 나오는 곳을 보여 드립니다." }) : null,
      gone.length && total ? h("span", { text: `어디에도 나오지 않는 낱말: ${gone.join(", ")}` }) : null,
    );

    // 갈래 고르기: 찾은 것이 있는 갈래만 보인다. 고쳐 그려도 초점이 있던 단추는 초점을 지킨다.
    const held = tabs.contains(document.activeElement) ? document.activeElement.dataset.kind : "";
    tabs.hidden = present.length < 2;
    fill(tabs, [["all", "전체", total], ...present.map((kind) => [kind, NAMES[kind], counts[kind]])].map(([kind, title, number]) =>
      h("button", { type: "button", class: "chip", "data-kind": kind, "aria-pressed": String(state.pick === kind), onclick: () => choose(kind) },
        [h("span", { text: title }), h("span", { class: "n", text: count(number) })])));
    if (held) (tabs.querySelector(`[data-kind="${held}"]`) || tabs.firstElementChild).focus();

    // 구역들. 달라지지 않은 구역은 그대로 둔다(규정의 글을 늦게 더할 때 읽던 자리가 흐트러지지 않게).
    const wanted = [];
    if (pages.length && !one) wanted.push({ key: "pages", make: () => shortcuts(pages) });
    for (const kind of one ? [state.pick] : present) {
      const all1 = () => h("button", { type: "button", class: "search-all", onclick: () => choose(kind) }, [h("span", { text: "모두 보기" }), icon("next", 14)]);
      if (kind === "laws") {
        const limits = one ? { laws: PAGE, acts: PARTS, guides: PARTS } : FEW;
        const sizes = ["laws", "acts", "guides"].map((key) => (kept[key] || []).length).join(".");
        wanted.push({ key: `laws|${one}|${need}|${sizes}`, make: () => lawSection(kept, limits, context, query, !one && counts.laws > lawShown(kept, limits) ? all1() : null) });
        continue;
      }
      const limit = one ? state.shown : FEW[kind];
      const hits = kept[kind];
      wanted.push({ key: `${kind}|${limit}|${need}|${hits.length}`, make: () => section(kind, hits, limit, context, {
        code: kind === "codes" ? code : null,
        more: !one && hits.length > limit ? all1() : null,
        after: one && hits.length > limit ? h("p", {}, h("button", { type: "button", class: "btn", text: `더 보기 (남은 ${count(hits.length - limit)}건)`, onclick: () => further(kind) })) : null,
      }) });
    }
    if (nothing && !pages.length && !parsed.groups.length) wanted.push({ key: "unread", make: () => empty("‘기본값’, ‘검증기관 인정’처럼 찾을 내용을 낱말로 적어 주십시오.") });
    if (nothing && !pages.length && parsed.groups.length) wanted.push({ key: "none", make: () => h("p", { class: "find-none", text: "다른 낱말로 다시 찾아 주십시오. 낱말을 줄이거나 영문 표기로 적으면 더 잘 찾습니다." }) });
    if (nothing && !pages.length) wanted.push({ key: "examples", make: examples });
    settle(body, wanted);
  }

  fill(out, status, parsed.groups.length ? understood(parsed) : null, tabs, body);
  draw();
  if (!parsed.groups.length) return;
  const more = parts(parsed).then((extra) => { state.extra = extra; draw(); });
  await Promise.race([more, pause(WAIT_MS)]);
}

export async function render(main, arg) {
  const query = decode(arg).trim();
  // 이 화면의 칸에서 찾았으면 초점을 칸에 그대로 둔다. 화면 자판을 쓰는 기기에서는 그러지 않는다(자판이 결과를 가린다).
  const typing = Boolean(document.activeElement) && document.activeElement.id === "search-q" && !window.matchMedia("(pointer: coarse)").matches;
  const input = h("input", { id: "search-q", type: "search", value: query, placeholder: "찾는 말을 적어 주십시오. 예: 기본값, 검증기관 인정, 7208", autocomplete: "off", spellcheck: "false", enterkeyhint: "search" });
  const go = (text) => { if (!visit(target(text))) window.scrollTo(0, 0); };
  const out = h("div", { class: "search-out" });
  fill(main,
    band("검색", "소식, 규제, 규정 원문, 용어집, 일정, 품목 코드, 원문 대장을 한 번에 찾습니다."),
    h("form", { class: "law-search", role: "search", "aria-label": "검색 화면의 검색", onsubmit: (event) => { event.preventDefault(); go(input.value); } }, [
      h("label", { class: "sr", for: "search-q", text: "찾는 말" }), icon("search", 20), input, h("button", { class: "btn btn-main", type: "submit", text: "찾기" })]),
    out,
  );
  if (!query) {
    fill(out, examples());
    setTimeout(() => input.focus(), 0);  // 길잡이가 화면을 맨 위로 옮긴 뒤에 칸으로 간다
    return "";
  }
  if (typing) {  // 화면을 새로 그리면서 칸도 새로 만들었으므로 초점을 다시 준다
    input.focus({ preventScroll: true });
    input.setSelectionRange(query.length, query.length);
  }
  await results(out, query);
  return `‘${query}’ 검색`;
}
