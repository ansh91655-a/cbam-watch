// 용어집. 영문, 약어, 국문 어느 쪽으로도 찾는다. 한 번에 60건씩 보여 준다.
// 용어마다 해설서의 풀이, 근거 조문, 그리고 그 용어가 쓰인 곳을 사이트 검색으로 찾는 길을 단다.
// #terms-찾는 말로 오면 그 말로 걸러 보여 준다(사이트 검색의 결과가 이 주소로 보낸다).
import * as data from "../data.js";
import { band } from "../ui/band.js";
import { readTerm } from "../laws/refs.js";
import { empty, fill, h, table } from "../ui/dom.js";
import { icon } from "../ui/icons.js";
import { lawRefs } from "../ui/lawrefs.js";
import { stackable } from "../ui/stack.js";
import { decode, target } from "../ui/sitesearch.js";
import { groupTabs } from "../ui/tabs.js";

const PAGE = 60;

// 그 용어를 풀어 쓴 해설서의 절로 가는 줄(해설서가 풀이한 용어에만)
function readLine(read) {
  if (!read) return null;
  return h("p", { class: "ref-links" }, [h("span", { class: "ref-name" }, [icon("guide", 14), h("span", { text: "해설서" })]), h("a", { href: read.href, text: `${read.chapter}: ${read.title}` })]);
}

const LONG = 24;   // 이보다 긴 국문 표기(표준의 이름 등)는 그대로 찾아도 나오지 않으므로 영문 표기로 찾는다

// 그 용어가 쓰인 곳을 사이트 검색으로 찾는 줄. 소식, 규제, 해설서, 규정 원문에서 국문 표기로 찾는다(괄호 안의 풀이는 뗀다)
function usedLine(term) {
  const ko = String(term.ko || "").replace(/\([^)]*\)/g, "").trim();
  const word = ko && ko.length <= LONG ? ko : String(term.en || "").replace(/\([^)]*\)/g, "").split(" / ")[0].trim();
  if (!word) return null;
  return h("p", { class: "ref-links" }, [h("span", { class: "ref-name" }, [icon("search", 14), h("span", { text: "쓰인 곳" })]), h("a", { href: target(word), text: `‘${word}’ 찾기` })]);
}

function row(term, refs, read) {
  return h("tr", {}, [
    h("td", { text: term.en }),
    h("td", {}, term.abbr ? h("span", { class: "nb", text: term.abbr }) : null),   // 약어는 글자 사이에서 줄을 바꾸지 않는다
    h("td", {}, [h("strong", { text: term.ko }), term.alt ? h("span", { class: "count", text: ` (${term.alt})` }) : null]),
    h("td", {}, [h("span", { text: term.note || "" }), readLine(read), lawRefs(refs, "근거 조문"), usedLine(term)]),
  ]);
}

export async function render(main, arg) {
  const [terms, refs] = await Promise.all([data.terms(), data.refs()]);
  const state = { text: decode(arg).trim(), shown: PAGE };
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
      ? stackable(table(["영문", "약어", "국문 표기", "설명"], found.slice(0, state.shown).map((term) => row(term, refs.terms[term.en], readTerm(refs, term))), "용어 목록"), { wideLast: true })
      : empty("찾는 용어가 없습니다. 다른 낱말로 찾아보세요."));
    more.hidden = found.length <= state.shown;
    more.textContent = `더 보기 (남은 ${found.length - state.shown}건)`;
  }

  fill(main,
    band("용어집", "이 사이트의 국문 정리에 쓰는 표기 기준입니다. 정부와 공공기관의 국문 자료에서 확인된 표기만 싣습니다.", groupTabs("terms")),
    h("div", { class: "filters" }, [
      h("label", { class: "field field-grow", for: "term-q" }, [h("span", { text: "검색" }), h("input", { id: "term-q", type: "search", value: state.text, placeholder: "예: embedded emissions, 내재배출량", oninput: (event) => { state.text = event.target.value; state.shown = PAGE; draw(); } })]),
      count,
    ]),
    holder,
    h("p", {}, more),
  );
  draw();
}
