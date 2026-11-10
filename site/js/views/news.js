// 전체 소식. 검색어, 종류, 중요도로 걸러 본다.
import * as data from "../data.js";
import { card } from "../ui/card.js";
import { empty, h, viewHead } from "../ui/dom.js";

const PAGE = 20;

function select(id, label, options, onChange) {
  return h("label", { class: "field", for: id }, [
    h("span", { text: label }),
    h("select", { id, onchange: onChange }, [h("option", { value: "", text: "전체" }), ...options.map((value) => h("option", { value, text: value }))]),
  ]);
}

export async function render(main) {
  const items = data.newestFirst(await data.items());
  const kinds = [...new Set(items.map((item) => item.kind).filter(Boolean))].sort();
  const state = { text: "", kind: "", importance: "", shown: PAGE };
  const list = h("div", { class: "stack" });
  const count = h("p", { class: "count", role: "status" });
  const more = h("button", { class: "btn", type: "button", text: "더 보기", onclick: () => { state.shown += PAGE; draw(); } });

  function matches(item) {
    if (state.kind && item.kind !== state.kind) return false;
    if (state.importance && item.importance !== state.importance) return false;
    if (!state.text) return true;
    const haystack = `${item.title} ${item.summary} ${item.sourceName} ${(item.topics || []).join(" ")}`.toLowerCase();
    return state.text.toLowerCase().split(/\s+/).filter(Boolean).every((word) => haystack.includes(word));
  }

  function draw() {
    const found = items.filter(matches);
    count.textContent = `${found.length}건`;
    list.replaceChildren(...(found.length ? found.slice(0, state.shown).map(card) : [empty("조건에 맞는 소식이 없습니다. 검색어나 조건을 바꿔 보세요.")]));
    more.hidden = found.length <= state.shown;
  }

  const reset = (key) => (event) => { state[key] = event.target.value; state.shown = PAGE; draw(); };
  const filters = h("div", { class: "filters" }, [
    h("label", { class: "field", for: "news-q" }, [h("span", { text: "검색" }), h("input", { id: "news-q", type: "search", placeholder: "제목, 요약, 출처", oninput: reset("text") })]),
    select("news-kind", "종류", kinds, reset("kind")),
    select("news-importance", "중요도", ["높음", "보통", "낮음"], reset("importance")),
    count,
  ]);
  main.replaceChildren(viewHead("전체 소식", "게시일이 늦은 것부터 보여 줍니다. 제목을 누르면 원문이 열립니다."), filters, list, more);
  draw();
}
