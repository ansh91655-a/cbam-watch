// 소식. 왼쪽에 주제 메뉴, 오른쪽에 소식. 주제를 고르지 않았을 때는 주제별로 나눠 보여 주고(기본) 최신순으로도 볼 수 있다.
// 최신순과 주제를 고른 화면에서는 달마다 머리를 달아 지난 소식을 거슬러 보기 쉽게 한다.
import * as data from "../data.js";
import { band } from "../ui/band.js";
import { card } from "../ui/card.js";
import { empty, fill, h } from "../ui/dom.js";
import { icon } from "../ui/icons.js";
import { topicAbout, topicList, topicName, topicOf } from "../ui/topics.js";

const PAGE = 20;
const PER_TOPIC = 3;

function select(id, label, options, onChange) {
  return h("label", { class: "field", for: id }, [
    h("span", { text: label }),
    h("select", { id, onchange: onChange }, [h("option", { value: "", text: "전체" }), ...options.map((option) =>
      h("option", { value: option.value ?? option, text: option.text ?? option }))]),
  ]);
}

export async function render(main, arg) {
  const items = data.newestFirst(await data.items());
  const topics = topicList();
  const picked = topics.some((topic) => topic.code === arg) ? arg : "";
  const kinds = [...new Set(items.map((item) => item.kind).filter(Boolean))].sort();
  const years = [...new Set(items.map((item) => data.dateOf(item).slice(0, 4)).filter(Boolean))].sort().reverse();
  const state = { text: "", kind: "", importance: "", year: "", latest: false, shown: PAGE };
  const body = h("div", { class: "stack-l" });
  const count = h("p", { class: "count", role: "status" });
  const more = h("button", { class: "btn", type: "button", text: "더 보기", onclick: () => { state.shown += PAGE; draw(); } });

  function matches(item) {
    if (picked && topicOf(item) !== picked) return false;
    if (state.kind && item.kind !== state.kind) return false;
    if (state.importance && item.importance !== state.importance) return false;
    if (state.year && data.dateOf(item).slice(0, 4) !== state.year) return false;
    if (!state.text) return true;
    const haystack = `${item.title} ${item.summary} ${item.sourceName} ${topicName(topicOf(item))} ${(item.topics || []).join(" ")}`.toLowerCase();
    return state.text.toLowerCase().split(/\s+/).filter(Boolean).every((word) => haystack.includes(word));
  }

  function grouped(found) {
    return topics.map((topic) => {
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
    });
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
    return h("div", { class: "stack" }, nodes);
  }

  function draw() {
    const found = items.filter(matches);
    const filtered = Boolean(state.text || state.kind || state.importance || state.year);
    count.textContent = `${found.length}건`;
    if (!found.length) {
      fill(body, empty("조건에 맞는 소식이 없습니다. 검색어나 조건을 바꿔 보세요."));
      more.hidden = true;
    } else if (!picked && !state.latest && !filtered) {
      fill(body, grouped(found));
      more.hidden = true;
    } else {
      fill(body, byMonth(found));
      more.hidden = found.length <= state.shown;
      more.textContent = `더 보기 (남은 ${found.length - state.shown}건)`;
    }
  }

  const side = h("nav", { class: "side-nav", "aria-label": "주제" }, [
    h("a", { href: "#news", "aria-current": picked ? null : "true" }, [h("span", { class: "chipicon" }, icon("news", 17)), h("span", { text: "전체" }), h("span", { class: "n", text: items.length })]),
    ...topics.map((topic) => {
      const size = items.filter((item) => topicOf(item) === topic.code).length;
      if (!size && topic.code === "etc") return null;
      return h("a", { href: `#news-${topic.code}`, "data-topic": topic.code, "aria-current": picked === topic.code ? "true" : null, "data-empty": size ? null : "true" },
        [h("span", { class: "chipicon" }, icon(topic.code, 17)), h("span", { text: topic.name }), h("span", { class: "n", text: size })]);
    }),
  ]);

  const reset = (key) => (event) => { state[key] = event.target.value; state.shown = PAGE; draw(); };
  const byTopic = h("button", { type: "button", text: "주제별", "aria-pressed": "true" });
  const byDate = h("button", { type: "button", text: "최신순", "aria-pressed": "false" });
  const setMode = (latest) => () => { state.latest = latest; state.shown = PAGE; byTopic.setAttribute("aria-pressed", String(!latest)); byDate.setAttribute("aria-pressed", String(latest)); draw(); };
  byTopic.addEventListener("click", setMode(false));
  byDate.addEventListener("click", setMode(true));
  const filters = h("div", { class: "filters" }, [
    picked ? null : h("div", { class: "seg", role: "group", "aria-label": "보는 방법" }, [byTopic, byDate]),
    h("label", { class: "field", for: "news-q" }, [h("span", { text: "검색" }), h("input", { id: "news-q", type: "search", placeholder: "제목, 요약, 출처", oninput: reset("text") })]),
    years.length > 1 ? select("news-year", "연도", years.map((year) => ({ value: year, text: `${year}년` })), reset("year")) : null,
    select("news-kind", "종류", kinds, reset("kind")),
    select("news-importance", "중요도", ["높음", "보통", "낮음"], reset("importance")),
    count,
  ]);
  fill(main,
    band(picked ? `소식: ${topicName(picked)}` : "소식", picked ? topicAbout(picked) : "주제별로 나눠 보여 줍니다. 제목을 누르면 원문이 열립니다."),
    h("div", { class: "with-side" }, [h("aside", { class: "side" }, side), h("div", { class: "stack-l" }, [filters, body, more])]),
  );
  draw();
}
