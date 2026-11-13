// 소식. 왼쪽에 주제 메뉴, 오른쪽에 소식. 주제를 고르지 않았을 때는 주제별로 나눠 보여 주고(기본) 최신순으로도 볼 수 있다.
// 최신순과 주제를 고른 화면에서는 달마다 머리를 달아 지난 소식을 거슬러 보기 쉽게 한다.
// 국내 기관의 게시판에 올라온 한 줄 소식(국내 공지·자료)은 기본 목록과 주제별 건수에서 빼고 #news-notices에 따로 모은다(news/notices.js).
// #news-recent는 최근 30일의 소식만 최신순으로 보여 준다. 첫 화면의 '최근 30일 소식' 칸이 센 것과 같다(news/recent.js).
import * as data from "../data.js";
import { NOTICES, NOTICE_ABOUT, NOTICE_NAME, split } from "../news/notices.js";
import { PERIODS, RECENT, RECENT_DAYS, within } from "../news/recent.js";
import { band } from "../ui/band.js";
import { card } from "../ui/card.js";
import { empty, fill, h } from "../ui/dom.js";
import { today } from "../ui/format.js";
import { icon } from "../ui/icons.js";
import { topicAbout, topicList, topicName, topicOf } from "../ui/topics.js";

const PAGE = 20;
const PER_TOPIC = 3;
const NOTICE_ROWS = 5;      // 주제별 화면의 끝에 보여 주는 국내 공지·자료의 수
const NOTICE_ICON = "sources";

function select(id, label, options, onChange, value = "") {
  const box = h("select", { id, onchange: onChange }, [h("option", { value: "", text: "전체" }), ...options.map((option) =>
    h("option", { value: option.value ?? option, text: option.text ?? option }))]);
  box.value = value;
  return h("label", { class: "field", for: id }, [h("span", { text: label }), box]);
}

export async function render(main, arg) {
  const { news, notices } = split(data.newestFirst(await data.items()));
  const topics = topicList();
  const onNotices = arg === NOTICES;
  const onRecent = arg === RECENT;
  const picked = !onNotices && topics.some((topic) => topic.code === arg) ? arg : "";
  const items = onNotices ? notices : news;   // 이 화면이 다루는 소식
  const kinds = [...new Set(items.map((item) => item.kind).filter(Boolean))].sort();
  const years = [...new Set(items.map((item) => data.dateOf(item).slice(0, 4)).filter(Boolean))].sort().reverse();
  const now = today();
  // when: 기간 조건. "d30"처럼 d로 시작하면 최근 며칠, "2026"처럼 네 자리이면 그해, ""이면 전체
  const state = { text: "", kind: "", importance: "", when: onRecent ? `d${RECENT_DAYS}` : "", latest: false, shown: PAGE };
  const body = h("div", { class: "stack-l" });
  const count = h("p", { class: "count", role: "status" });
  const more = h("button", { class: "btn", type: "button", text: "더 보기", onclick: () => { state.shown += PAGE; draw(); } });

  function matches(item) {
    if (picked && topicOf(item) !== picked) return false;
    if (state.kind && item.kind !== state.kind) return false;
    if (state.importance && item.importance !== state.importance) return false;
    if (state.when.startsWith("d") ? !within(data.dateOf(item), now, Number(state.when.slice(1))) : (state.when && data.dateOf(item).slice(0, 4) !== state.when)) return false;
    if (!state.text) return true;
    const haystack = `${item.title} ${item.summary} ${item.sourceName} ${topicName(topicOf(item))} ${(item.topics || []).join(" ")}`.toLowerCase();
    return state.text.toLowerCase().split(/\s+/).filter(Boolean).every((word) => haystack.includes(word));
  }

  // 주제별 화면의 끝에 두는 칸: 국내 공지·자료의 가장 최근 것 몇 건과 모두 보는 길
  function noticeStrip() {
    if (!notices.length) return null;
    return h("section", { class: "topic-sec notice-sec", "aria-labelledby": "h-notices" }, [
      h("div", { class: "sec-head" }, [
        h("h2", { id: "h-notices" }, [h("span", { class: "chipicon" }, icon(NOTICE_ICON, 22)), h("span", { text: NOTICE_NAME })]),
        h("a", { href: `#news-${NOTICES}`, text: `${notices.length}건 모두 보기` }),
      ]),
      h("p", { class: "about", text: NOTICE_ABOUT }),
      ...notices.slice(0, NOTICE_ROWS).map(card),
    ]);
  }

  function grouped(found) {
    return [...topics.map((topic) => {
      const mine = found.filter((item) => topicOf(item) === topic.code);
      if (!mine.length) return null;
      return h("section", { class: "topic-sec", "aria-labelledby": `h-topic-${topic.code}`, "data-topic": topic.code }, [
        h("div", { class: "sec-head" }, [
          h("h2", { id: `h-topic-${topic.code}` }, [h("span", { class: "chipicon" }, icon(topic.code, 22)), h("span", { text: topic.name })]),
          mine.length > PER_TOPIC ? h("a", { href: `#news-${topic.code}`, text: `이 주제 ${mine.length}건 모두 보기` }) : h("span", { class: "count", text: `${mine.length}건` }),
        ]),
        h("p", { class: "about", text: topic.about || "" }),
        ...mine.slice(0, PER_TOPIC).map(card),
      ]);
    }), noticeStrip()];
  }

  // 날짜가 늦은 것부터 늘어놓고, 달이 바뀌는 곳에 머리를 단다.
  function byMonth(found) {
    const nodes = [];
    let month = null;
    for (const item of found.slice(0, state.shown)) {
      const key = data.dateOf(item).slice(0, 7);
      if (key !== month) {
        month = key;
        nodes.push(h("h2", { class: "month-head", text: key ? `${key.slice(0, 4)}년 ${Number(key.slice(5, 7))}월` : "날짜 없음" }));
      }
      nodes.push(card(item));
    }
    return h("div", { class: "stack month-sec" }, nodes);  // month-sec: 넓은 화면에서 카드를 두 칸으로 놓는다(css/wide.css)
  }

  // 주제를 고른 화면의 끝: 그 주제의 국내 공지·자료가 따로 있음을 알린다
  function elsewhere() {
    const mine = picked ? notices.filter((item) => topicOf(item) === picked).length : 0;
    return mine ? h("p", { class: "notice-hint" }, [
      h("span", { text: `이 주제의 ${NOTICE_NAME} ${mine}건은 따로 모았습니다.` }), h("a", { href: `#news-${NOTICES}`, text: `${NOTICE_NAME} 보기` })]) : null;
  }

  function draw() {
    const found = items.filter(matches);
    const filtered = Boolean(state.text || state.kind || state.importance || state.when);
    count.textContent = `${found.length}건`;
    if (!found.length) {
      fill(body, empty("조건에 맞는 소식이 없습니다. 검색어나 조건을 바꿔 보세요."));
      more.hidden = true;
    } else if (!picked && !onNotices && !state.latest && !filtered) {
      fill(body, grouped(found));
      more.hidden = true;
    } else {
      fill(body, byMonth(found), found.length <= state.shown ? elsewhere() : null);
      more.hidden = found.length <= state.shown;
      more.textContent = `더 보기 (남은 ${found.length - state.shown}건)`;
    }
  }

  const side = h("nav", { class: "side-nav", "aria-label": "주제" }, [
    h("a", { href: "#news", "aria-current": picked || onNotices || onRecent ? null : "true" }, [h("span", { class: "chipicon" }, icon("news", 17)), h("span", { text: "전체" }), h("span", { class: "n", text: news.length })]),
    ...topics.map((topic) => {
      const size = news.filter((item) => topicOf(item) === topic.code).length;
      if (!size && topic.code === "etc") return null;
      return h("a", { href: `#news-${topic.code}`, "data-topic": topic.code, "aria-current": picked === topic.code ? "true" : null, "data-empty": size ? null : "true" },
        [h("span", { class: "chipicon" }, icon(topic.code, 17)), h("span", { text: topic.name }), h("span", { class: "n", text: size })]);
    }),
    notices.length ? h("a", { class: "side-apart", href: `#news-${NOTICES}`, "aria-current": onNotices ? "true" : null },
      [h("span", { class: "chipicon" }, icon(NOTICE_ICON, 17)), h("span", { text: NOTICE_NAME }), h("span", { class: "n", text: notices.length })]) : null,
  ]);

  const reset = (key) => (event) => { state[key] = event.target.value; state.shown = PAGE; draw(); };
  const byTopic = h("button", { type: "button", text: "주제별", "aria-pressed": "true" });
  const byDate = h("button", { type: "button", text: "최신순", "aria-pressed": "false" });
  const setMode = (latest) => () => { state.latest = latest; state.shown = PAGE; byTopic.setAttribute("aria-pressed", String(!latest)); byDate.setAttribute("aria-pressed", String(latest)); draw(); };
  byTopic.addEventListener("click", setMode(false));
  byDate.addEventListener("click", setMode(true));
  const filters = h("div", { class: "filters" }, [
    picked || onNotices ? null : h("div", { class: "seg", role: "group", "aria-label": "보는 방법" }, [byTopic, byDate]),
    h("label", { class: "field field-grow", for: "news-q" }, [h("span", { text: "검색" }), h("input", { id: "news-q", type: "search", placeholder: onNotices ? "제목, 기관" : "제목, 요약, 출처", oninput: reset("text") })]),
    select("news-when", "기간", [...PERIODS.map((days) => ({ value: `d${days}`, text: `최근 ${days}일` })), ...years.map((year) => ({ value: year, text: `${year}년` }))], reset("when"), state.when),
    kinds.length > 1 ? select("news-kind", "종류", kinds, reset("kind")) : null,
    onNotices ? null : select("news-importance", "중요도", ["높음", "보통", "낮음"], reset("importance")),
    count,
  ]);
  const recentName = `최근 ${RECENT_DAYS}일`;
  const title = onNotices ? `소식: ${NOTICE_NAME}` : (onRecent ? `소식: ${recentName}` : (picked ? `소식: ${topicName(picked)}` : "소식"));
  const about = onNotices ? NOTICE_ABOUT : (onRecent ? `오늘에서 ${RECENT_DAYS}일 안에 나온 소식을 최신순으로 보여 줍니다. 기간을 '전체'로 바꾸면 2025년 1월부터의 소식을 모두 볼 수 있습니다.`
    : (picked ? topicAbout(picked) : "2025년 1월부터의 소식을 주제별로 나눠 보여 줍니다. 제목을 누르면 국문 요약을 먼저 보여 줍니다."));
  fill(main,
    band(title, about),
    h("div", { class: "with-side" }, [h("aside", { class: "side" }, side), h("div", { class: "stack-l" }, [filters, body, more])]),
  );
  draw();
  return onNotices ? NOTICE_NAME : (onRecent ? `${recentName} 소식` : "");
}
