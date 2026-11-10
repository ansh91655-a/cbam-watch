// 용어집. 영문, 약어, 국문 어느 쪽으로도 찾는다.
import * as data from "../data.js";
import { empty, fill, h, table, viewHead } from "../ui/dom.js";

export async function render(main) {
  const terms = await data.terms();
  const holder = h("div", {});
  const count = h("p", { class: "count", role: "status" });

  function draw(text) {
    const words = text.toLowerCase().split(/\s+/).filter(Boolean);
    const found = terms.filter((term) => {
      const haystack = `${term.en} ${term.abbr} ${term.ko} ${term.alt || ""} ${term.note || ""}`.toLowerCase();
      return words.every((word) => haystack.includes(word));
    });
    count.textContent = `${found.length}건`;
    holder.replaceChildren(found.length ? table(["영문", "약어", "국문 표기", "설명"], found.map((term) => h("tr", {}, [
      h("td", { text: term.en }),
      h("td", { text: term.abbr || "" }),
      h("td", {}, [h("strong", { text: term.ko }), term.alt ? h("span", { class: "count", text: ` (${term.alt})` }) : null]),
      h("td", { text: term.note || "" }),
    ]))) : empty("찾는 용어가 없습니다. 다른 낱말로 찾아보세요."));
  }

  fill(main, 
    viewHead("용어집", "이 사이트의 국문 정리에 쓰는 표기 기준입니다. 정부와 공공기관의 국문 자료에서 확인된 표기만 싣습니다."),
    h("div", { class: "filters" }, [
      h("label", { class: "field", for: "term-q" }, [h("span", { text: "검색" }), h("input", { id: "term-q", type: "search", placeholder: "예: embedded emissions, 내재배출량", oninput: (event) => draw(event.target.value) })]),
      count,
    ]),
    holder,
  );
  draw("");
}
