// 용어집. 영문, 약어, 국문 어느 쪽으로도 찾는다. 한 번에 60건씩 보여 준다.
import * as data from "../data.js";
import { band } from "../ui/band.js";
import { empty, fill, h, table } from "../ui/dom.js";
import { stackable } from "../ui/stack.js";
import { libraryTabs } from "../ui/tabs.js";

const PAGE = 60;

function row(term) {
  return h("tr", {}, [
    h("td", { text: term.en }),
    h("td", { text: term.abbr || "" }),
    h("td", {}, [h("strong", { text: term.ko }), term.alt ? h("span", { class: "count", text: ` (${term.alt})` }) : null]),
    h("td", { text: term.note || "" }),
  ]);
}

export async function render(main) {
  const terms = await data.terms();
  const state = { text: "", shown: PAGE };
  const holder = h("div", {});
  const count = h("p", { class: "count", role: "status" });
  const more = h("button", { class: "btn", type: "button", onclick: () => { state.shown += PAGE; draw(); } });

  function draw() {
    const words = state.text.toLowerCase().split(/\s+/).filter(Boolean);
    const found = terms.filter((term) => {
      const haystack = `${term.en} ${term.abbr} ${term.ko} ${term.alt || ""} ${term.note || ""}`.toLowerCase();
      return words.every((word) => haystack.includes(word));
    });
    count.textContent = `${found.length}건`;
    holder.replaceChildren(found.length
      ? stackable(table(["영문", "약어", "국문 표기", "설명"], found.slice(0, state.shown).map(row)), { wideLast: true })
      : empty("찾는 용어가 없습니다. 다른 낱말로 찾아보세요."));
    more.hidden = found.length <= state.shown;
    more.textContent = `더 보기 (남은 ${found.length - state.shown}건)`;
  }

  fill(main,
    band("용어집", "이 사이트의 국문 정리에 쓰는 표기 기준입니다. 정부와 공공기관의 국문 자료에서 확인된 표기만 싣습니다.", libraryTabs("terms")),
    h("div", { class: "filters" }, [
      h("label", { class: "field", for: "term-q" }, [h("span", { text: "검색" }), h("input", { id: "term-q", type: "search", placeholder: "예: embedded emissions, 내재배출량", oninput: (event) => { state.text = event.target.value; state.shown = PAGE; draw(); } })]),
      count,
    ]),
    holder,
    h("p", {}, more),
  );
  draw();
}
