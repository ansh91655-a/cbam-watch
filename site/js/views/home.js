// 첫 화면. 맨 위의 큰 머리에 가장 최근의 요약과 지도, 지표 줄을 두고,
// 그 아래에 품목 코드 조회, 가장 중요한 소식과 최근 소식(옆에 일정·가격·규제), 주제별 찾아보기, 품목별 가이던스를 차례로 놓는다.
// 칸마다의 짜임은 home/ 폴더의 모듈에 있다.
import * as data from "../data.js";
import { empty, fill, h } from "../ui/dom.js";
import { daysSince } from "../ui/format.js";
import { itemRows } from "../ui/rows.js";
import { guidance } from "./home/guidance.js";
import { hero, latestDigest } from "./home/hero.js";
import { lead } from "./home/lead.js";
import { ledger } from "./home/ledger.js";
import { lookupBar } from "./home/lookup.js";
import { pricePanel, rulesPanel, schedule } from "./home/rail.js";
import { topicIndex } from "./home/topicindex.js";

const IMPORTANT_DAYS = 45;
const RECENT_COUNT = 8;
const MORE_IMPORTANT = 4;

function recentSection(recent, total) {
  return h("section", { class: "stack", "aria-labelledby": "h-recent" }, [
    h("div", { class: "sec-head" }, [h("h2", { id: "h-recent", text: "최근 소식" }), h("a", { href: "#news", text: `소식 ${total}건 모두 보기` })]),
    recent.length ? itemRows(recent, { summary: true }) : empty(total ? "다른 최근 소식이 없습니다." : "아직 게시된 소식이 없습니다."),
  ]);
}

export async function render(main) {
  const [all, events, digests, book, documents, rules] = await Promise.all([data.items(), data.events(), data.digests(), data.prices(), data.documents(), data.regulations()]);
  // 처음에 한꺼번에 채운 소식 가운데 날짜가 없는 것(제도 안내)은 최근 소식으로 세지 않는다.
  const items = data.newestFirst(all).filter((item) => !item.withdrawn);
  const dated = items.filter((item) => data.dateOf(item));
  const isImportant = (item) => item.importance === "높음" && (daysSince(data.dateOf(item)) ?? 999) <= IMPORTANT_DAYS;
  const important = items.find(isImportant);
  const first = important || dated[0] || items[0];
  const others = important ? items.filter((item) => isImportant(item) && item.id !== first.id).slice(0, MORE_IMPORTANT) : [];
  const shown = new Set([first, ...others].filter(Boolean).map((item) => item.id));
  const recent = dated.filter((item) => !shown.has(item.id)).slice(0, RECENT_COUNT);

  fill(main,
    hero(latestDigest(digests), items, ledger(book, events, items, rules)),
    lookupBar(),
    h("div", { class: "cols" }, [
      h("div", { class: "stack-l" }, [first ? lead(first, Boolean(important), others) : null, recentSection(recent, items.length)]),
      h("aside", { class: "rail", "aria-label": "일정, 가격, 규제" }, [schedule(events), pricePanel(book), rulesPanel(rules)]),
    ]),
    topicIndex(items),
    guidance(documents),
  );
}
