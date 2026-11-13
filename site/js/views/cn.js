// 품목 코드 조회. CN 코드를 넣으면 CBAM 규정 부속서 I에 든 품목인지와 그 근거를 보여 준다.
// 판정은 js/cn/match.js가 하고, 품목 목록은 법령 원문에서 뽑은 data/cn.json이다. 문구는 이 파일에서 정한다.
import * as data from "../data.js";
import { digits, verdict } from "../cn/match.js";
import { GAS, SECTOR, spaced, STATE } from "../cn/names.js";
import { adopted, proposalRule } from "../cn/stage.js";
import { band } from "../ui/band.js";
import { empty, fill, h, pill, safeLink } from "../ui/dom.js";
import { icon } from "../ui/icons.js";
import { libraryTabs } from "../ui/tabs.js";

const SECTOR_ICON = { cement: "cement", electricity: "electricity", fertilisers: "fertilisers", steel: "steel", aluminium: "aluminium", chemicals: "hydrogen", combined: "steel" };
const LIMIT = 10; // 개정안의 품목을 한 번에 보여 주는 줄 수
const EXAMPLES = ["7208", "7318 15", "7606", "2523 29 00", "3102", "7202 21 00", "8544 49", "8708 10"];

function goods(item) {
  return h("li", {}, [h("span", { class: "cn-code", text: item.shown }), h("span", { lang: "en", text: item.text })]);
}

// 목록의 한 줄(품목)을 보여 준다. 제외 품목이 있으면 함께 적는다.
function entryCard(hit, proposed) {
  const entry = hit.entry;
  const facts = [
    ["부문", SECTOR[entry.sector] || entry.sector],
    ["온실가스", (entry.gases || []).map((key) => GAS[key] || key).join(", ")],
    proposed ? null : ["산정 범위", entry.directOnly ? "직접배출만(부속서 II)" : "직접배출과 간접배출"],
  ].filter(Boolean);
  const listed = hit.excluded.length ? hit.excluded : (hit.partly.length ? hit.partly : entry.except || []);
  return h("article", { class: "cn-entry", "data-sector": entry.sector }, [
    h("div", { class: "cn-entry-head" }, [
      h("span", { class: "chipicon" }, icon(SECTOR_ICON[entry.sector] || "file", 20)),
      h("div", {}, [h("p", { class: "cn-code", text: entry.shown }), h("p", { class: "cn-text", lang: "en", text: entry.text })]),
    ]),
    h("dl", { class: "cn-facts" }, facts.flatMap(([name, value]) => [h("dt", { text: name }), h("dd", { text: value })])),
    entry.ex ? h("p", { class: "cn-note", text: "코드 앞의 ex는 이 코드의 품목 가운데 위 품목 이름에 해당하는 것만 든다는 뜻입니다." }) : null,
    listed.length ? h("div", { class: "cn-except" }, [h("p", { text: hit.excluded.length ? "이 코드가 해당하는 제외 품목" : "이 품목에서 제외되는 코드" }), h("ul", {}, listed.map(goods))]) : null,
  ]);
}

function basis(source, lead) {
  const link = safeLink(source.url, source.name);
  if (link) link.append(icon("out", 14));
  return h("p", { class: "cn-basis" }, [h("span", { text: lead }), link || h("span", { text: source.name })]);
}

// 개정안의 품목을 알릴 때 붙이는 말. 개정안이 채택 단계에 들어가면 '협상 전의 목록'이라고 스스로 바꿔 말한다.
function proposalWords(rule) {
  const stage = rule && rule.stage ? rule.stage : "";
  if (adopted(rule)) {
    return {
      stage,
      commission: `이 개정안은 지금 '${stage}' 단계입니다. 아래는 협상 전에 집행위원회가 제안한 목록이어서 최종 법령의 목록과 다를 수 있습니다. 최종 목록은 유럽연합 관보에 실린 원문에서 확인해 주세요.`,
      council: `이 개정안은 지금 '${stage}' 단계입니다. 아래는 협상 전의 이사회 안이어서 최종 법령의 목록과 다를 수 있습니다.`,
    };
  }
  return {
    stage,
    commission: "아직 법이 아니며, 최종 목록은 유럽의회와 EU 이사회의 협상 결과에 따라 달라집니다.",
    council: "집행위원회의 제안에는 없던 코드이며, 최종 목록에 들어갈지는 협상 결과에 달려 있습니다.",
  };
}

function result(text, book, rule) {
  const now = verdict(text, book.current);
  if (now.state === "short") {
    return h("div", { class: "cn-result" }, empty(digits(text) ? "코드를 4자리 이상 넣어 주세요." : "CN 코드나 HS 코드의 앞 4~8자리를 넣어 주세요."));
  }
  const [name, tone, about] = STATE[now.state];
  const open = !["in", "part"].includes(now.state); // 지금의 목록으로 대상이 아닐 때만 개정안을 알린다
  const live = (found) => ["in", "part", "mixed"].includes(found.state);
  // 집행위 제안: 지금의 목록에 없는 품목을 더할 때만 알린다(같은 줄이 개정안에도 있는 것은 새 소식이 아니다)
  const later = verdict(text, book.proposed || []);
  const added = later.rows.filter((row) => !now.rows.some((mine) => mine.entry.shown === row.entry.shown && mine.entry.sector === row.entry.sector));
  // 이사회 안: 집행위 목록에 더한 코드와 뺀 코드
  const council = book.council || { added: [], removed: [] };
  const more = verdict(text, council.added || []);
  const cut = verdict(text, council.removed || []);
  const words = proposalWords(rule);
  const blocks = [];
  if (open && live(later) && added.length) {
    blocks.push(h("section", { class: "cn-later" }, [
      h("h3", {}, [h("span", { text: "확대 개정안에는 들어 있습니다" }), pill(words.stage || "제안 단계", "warn")]),
      h("p", { text: `EU 집행위원회가 2025년 12월에 낸 하류제품 확대 개정안의 부속서에 이 코드${later.state === "mixed" ? " 아래의 일부 코드" : ""}가 들어 있습니다. ${words.commission}` }),
      h("div", { class: "cn-entries" }, added.slice(0, LIMIT).map((hit) => entryCard(hit, true))),
      added.length > LIMIT ? h("p", { class: "count", text: `이 밖에 ${added.length - LIMIT}줄이 더 있습니다. 코드를 더 길게 넣으면 좁혀집니다.` }) : null,
      live(cut) ? h("div", { class: "cn-except" }, [h("p", { text: "EU 이사회의 안은 이 가운데 다음 코드를 뺐습니다" }), h("ul", {}, cut.rows.map((hit) => goods(hit.entry)))]) : null,
      basis(book.proposal, "근거: "),
    ]));
  }
  if (open && live(more)) {
    blocks.push(h("section", { class: "cn-later" }, [
      h("h3", {}, [h("span", { text: "EU 이사회의 안에는 들어 있습니다" }), pill(words.stage || "협상 단계", "warn")]),
      h("p", { text: `EU 이사회가 2026년 6월 12일에 정한 일반적 접근은 집행위원회의 목록에 이 코드${more.state === "mixed" ? " 아래의 일부 코드" : ""}를 더했습니다. ${words.council}` }),
      h("div", { class: "cn-except" }, h("ul", {}, more.rows.slice(0, LIMIT).map((hit) => goods(hit.entry)))),
      more.rows.length > LIMIT ? h("p", { class: "count", text: `이 밖에 ${more.rows.length - LIMIT}개가 더 있습니다. 코드를 더 길게 넣으면 좁혀집니다.` }) : null,
      basis(council, "근거: "),
    ]));
  }
  if (blocks.length) blocks.push(h("p", { class: "cn-basis" }, h("a", { href: "#rules-cbam-downstream", text: "이 개정안의 진행 상황과 기관별 입장 보기" })));
  return h("div", { class: "cn-result", "data-state": now.state }, [
    h("div", { class: "cn-verdict" }, [
      h("p", { class: "cn-query", text: spaced(now.query) }),
      pill(name, tone),
      h("p", { class: "cn-about", text: about }),
    ]),
    now.rows.length ? h("div", { class: "cn-entries" }, now.rows.map((hit) => entryCard(hit, false))) : null,
    basis(book.law, "근거: "),
    // 대상 품목이면 인증서 비용 추정으로 이어 준다(전력은 벤치마크와 기본값 표가 따로 없어 추정하지 않는다)
    ["in", "part"].includes(now.state) && !now.rows.some((hit) => hit.entry.sector === "electricity")
      ? h("p", { class: "cn-basis" }, h("a", { href: `#calc-${now.query.slice(0, 8)}`, text: "이 품목의 인증서 비용 추정하기" })) : null,
    ...blocks,
  ]);
}

// 부속서 I의 품목을 부문별로 펼쳐 볼 수 있게 한다.
function listing(book) {
  // 정해 둔 차례대로 놓고, 법령에 새 부문이 생기면 그 뒤에 이어 놓는다.
  const known = ["cement", "electricity", "fertilisers", "steel", "aluminium", "chemicals", "combined"];
  const present = [...new Set(book.current.map((entry) => entry.sector))];
  const order = [...known.filter((sector) => present.includes(sector)), ...present.filter((sector) => !known.includes(sector))];
  return h("section", { class: "stack", "aria-labelledby": "h-cn-list" }, [
    h("div", { class: "sec-head" }, [h("h2", { id: "h-cn-list", text: "부속서 I의 대상 품목" }), safeLink(book.law.url, "법령 원문 열기")]),
    ...order.map((sector) => {
      const mine = book.current.filter((entry) => entry.sector === sector);
      return h("details", { class: "cn-sector" }, [
        h("summary", {}, [h("span", { class: "chipicon" }, icon(SECTOR_ICON[sector] || "file", 18)), h("strong", { text: SECTOR[sector] || sector }), h("span", { class: "count", text: `${mine.length}줄` })]),
        h("ul", { class: "cn-list" }, mine.map((entry) => h("li", {}, [
          h("a", { class: "cn-code", href: `#cn-${entry.codes[0]}`, text: entry.shown }),
          h("span", { lang: "en", text: entry.text }),
          entry.except && entry.except.length ? h("span", { class: "count", text: `제외 ${entry.except.length}줄` }) : null,
        ]))),
      ]);
    }),
  ]);
}

function notes() {
  return h("section", { class: "panel cn-notes", "aria-labelledby": "h-cn-notes" }, [
    h("h2", { id: "h-cn-notes", text: "함께 알아 둘 점" }),
    h("ul", {}, [
      h("li", { text: "한 해 동안 수입한 대상 품목의 순중량 합계가 50톤(단일 중량 임계값)을 넘지 않는 수입자는 CBAM 의무가 면제됩니다. 전력과 수소에는 이 면제가 적용되지 않습니다(CBAM 규정 제2a조, 부속서 VII)." }),
      h("li", { text: "이 조회는 코드의 앞자리를 부속서의 목록과 견주어 보여 주는 참고 자료입니다. 실제 품목 분류는 EU 세관의 판단을 따르므로, 신고 전에는 수입자와 함께 8자리 CN 코드를 확인해 주세요." }),
      h("li", { text: "품목 이름은 법령 원문(영문) 그대로입니다. CBAM 규정의 새 통합본이 나오면 목록을 다시 만듭니다." }),
    ]),
  ]);
}

export async function render(main, arg) {
  const [book, rules] = await Promise.all([data.cn(), data.regulations()]);
  const rule = proposalRule(rules);
  const head = band("품목 코드 조회", "CN 코드를 넣으면 CBAM 대상 품목인지와 그 근거를 보여 줍니다.", libraryTabs("cn"));
  if (!book || !Array.isArray(book.current) || !book.current.length) {
    fill(main, head, empty("품목 목록을 준비하고 있습니다."));
    return;
  }
  const holder = h("div", { "aria-live": "polite" });
  const input = h("input", { id: "cn-q", type: "search", inputmode: "numeric", autocomplete: "off", placeholder: "예: 7208 또는 7318 15 00", value: arg ? spaced(digits(arg)) : "" });
  const show = () => fill(holder, result(input.value, book, rule));
  input.addEventListener("input", show);
  const form = h("form", { class: "cn-form", role: "search", onsubmit: (event) => {
    event.preventDefault();
    history.replaceState(null, "", `#cn-${digits(input.value)}`);
    show();
  } }, [
    h("label", { class: "field", for: "cn-q" }, [h("span", { text: "CN 코드(HS 코드의 앞 6자리도 됩니다)" }), input]),
    h("button", { class: "btn btn-primary", type: "submit" }, [icon("search", 16), h("span", { text: "확인" })]),
  ]);
  const examples = h("p", { class: "cn-examples" }, [h("span", { text: "예시" }), ...EXAMPLES.map((code) => h("button", {
    type: "button", class: "pill", text: code, onclick: () => { input.value = code; history.replaceState(null, "", `#cn-${digits(code)}`); show(); },
  }))]);
  fill(main, head, h("section", { class: "cn-box" }, [form, examples, holder]), notes(), listing(book),
    h("p", { class: "count", text: `목록 기준일 ${book.asOf}. ${book.law.name}` }));
  show();
}
