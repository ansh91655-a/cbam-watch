// 첫 화면. 맨 위에 큰 머리(한 줄 소개, 점 지도, 지금 알아 둘 수치 세 칸)를 두고, 바로 아래에 가장 최근의 요약을 놓는다.
// 이어서 가장 중요한 소식, 다가오는 일정, 가격 추세, 주제별 소식, 규제 진행 상황, 품목 코드 조회, 최근 소식을 칸으로 나눠 놓고,
// 맨 아래 짙은 띠에 부문별 보기로 가는 칸을 둔다. 칸마다의 모듈은 home/ 아래에 있다.
import * as data from "../data.js";
import { isNotice } from "../news/notices.js";
import { card } from "../ui/card.js";
import { empty, fill, h } from "../ui/dom.js";
import { daysSince } from "../ui/format.js";
import { digestPanel, latestDigest } from "./home/digest.js";
import { feature } from "./home/feature.js";
import { hero } from "./home/hero.js";
import { lookupBar } from "./home/lookup.js";
import { pricePanel, rulesPanel, schedule, topicsPanel } from "./home/panels.js";
import { sectors } from "./home/sectors.js";

const IMPORTANT_DAYS = 45;
const RECENT_COUNT = 6;
const MORE_IMPORTANT = 3;

export async function render(main) {
  const [all, events, digests, book, rules] = await Promise.all([data.items(), data.events(), data.digests(), data.prices(), data.regulations()]);
  // 처음에 한꺼번에 채운 소식 가운데 날짜가 없는 것(제도 안내)은 최근 소식으로 세지 않는다.
  // 제목이 곧 내용인 국내 공지·자료는 첫 화면에 싣지 않는다(소식 화면에 따로 모여 있다).
  const items = data.newestFirst(all).filter((item) => !item.withdrawn && !isNotice(item));
  const dated = items.filter((item) => data.dateOf(item));
  const isImportant = (item) => item.importance === "높음" && (daysSince(data.dateOf(item)) ?? 999) <= IMPORTANT_DAYS;
  const important = items.find(isImportant);
  const lead = important || dated[0] || items[0];
  const others = important ? items.filter((item) => isImportant(item) && item.id !== lead.id).slice(0, MORE_IMPORTANT) : [];
  const shown = new Set([lead, ...others].filter(Boolean).map((item) => item.id));
  const recent = dated.filter((item) => !shown.has(item.id)).slice(0, RECENT_COUNT);

  fill(main,
    hero(book, events, items, dated),
    digestPanel(latestDigest(digests), items),
    h("div", { class: "bento" }, [lead ? feature(lead, Boolean(important), others) : null, schedule(events), pricePanel(book), topicsPanel(items), rulesPanel(rules)]),
    lookupBar(),
    h("section", { class: "stack", "aria-labelledby": "h-recent" }, [
      h("div", { class: "sec-head" }, [h("h2", { id: "h-recent", text: "최근 소식" }), h("a", { href: "#news", text: `소식 ${items.length}건 모두 보기` })]),
      recent.length ? h("div", { class: "cards-2" }, recent.map(card)) : empty(items.length ? "다른 최근 소식이 없습니다." : "아직 게시된 소식이 없습니다."),
    ]),
    sectors(),
  );
}
