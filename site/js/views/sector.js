// 부문별 모아 보기. 부문 하나(철강, 알루미늄, 시멘트, 비료, 수소, 전력)에 관한 것을 한 화면에 모은다:
// 대상 품목, 안내 문서, 기본값과 비용 추정, 다가오는 의무 일정, 소식, 모든 부문에 함께 적용되는 문서.
// 주소는 #sector-<부문>이고, 부문을 주지 않으면 첫 부문을 보여 준다. 자료는 data/sectors.json(tools/publish/sectors.py)이다.
// 수와 글은 모두 사이트의 다른 자료(품목 목록, 규정 원문의 목록, 비용 추정의 자료, 게시한 소식)에서 만든 것이다.
// #sector-<부문>.values는 그 부문 품목마다의 기본값과 CBAM 벤치마크의 표를 보여 준다(views/sector/values.js).
import { unpack } from "../calc/compute.js";
import * as data from "../data.js";
import { gasText, scopeText } from "../sector/facts.js";
import { band } from "../ui/band.js";
import { empty, fill, h } from "../ui/dom.js";
import { count, today } from "../ui/format.js";
import { icon } from "../ui/icons.js";
import { groupTabs } from "../ui/tabs.js";
import { commonSection, docsSection } from "./sector/docs.js";
import { goodsSection } from "./sector/goods.js";
import { calcSection, dutySection, newsSection } from "./sector/more.js";
import { valuesView } from "./sector/values.js";

const TITLE = "부문별 보기";

const PAGES = [["", "한눈에 보기"], ["values", "기본값과 벤치마크"]];

// 부문을 바꿔도 보던 쪽(한눈에 보기, 기본값과 벤치마크)은 그대로 둔다
function picker(sectors, current, page) {
  return h("nav", { class: "sector-pick", "aria-label": "부문 고르기" }, sectors.map((sector) =>
    h("a", { href: `#sector-${sector.key}${page ? `.${page}` : ""}`, "aria-current": sector.key === current ? "page" : null }, [h("span", { class: "chipicon" }, icon(sector.key, 18)), h("span", { text: sector.name })])));
}

function pages(sector, current) {
  return h("nav", { class: "seg sector-pages", "aria-label": "보는 내용" }, PAGES.map(([key, text]) =>
    h("a", { href: `#sector-${sector.key}${key ? `.${key}` : ""}`, "aria-current": key === current ? "page" : null, text })));
}

function facts(sector) {
  const rows = [
    ["대상 품목", `CN 코드 ${count(sector.goods.rows.length)}줄`],
    ["온실가스", gasText(sector.goods.gases)],
    ["산정 범위", scopeText(sector.goods)],
    ["기본값·벤치마크", sector.calc ? `${count(sector.calc.goods)}개 품목` : "비용 추정에 싣지 않음", sector.calc ? `#sector-${sector.key}.values` : ""],
    ["안내 문서", `${count(sector.docs.length)}건`],
  ].filter(([, value]) => value);
  return h("dl", { class: "sector-facts" }, rows.map(([name, value, href]) => h("div", {}, [h("dt", { text: name }), h("dd", {}, href ? h("a", { href, text: value }) : value)])));
}

export async function render(main, arg) {
  const [key, page = ""] = String(arg || "").split(".");
  const showValues = page === "values";
  const [book, duties, calc] = await Promise.all([data.sectors(), data.duties(), showValues ? data.calc() : null]);
  const sector = book.sectors.find((one) => one.key === key) || book.sectors[0];
  if (!sector) {
    fill(main, band(TITLE, "", groupTabs("sector")), empty("부문별 자료를 불러오지 못했습니다."));
    return TITLE;
  }
  const head = [
    band(`${sector.name} 부문`, `CBAM 대상인 ${sector.name} 품목과, 그 품목에 관한 안내 문서, 기본값, 의무 일정, 소식을 한곳에 모았습니다.`, groupTabs("sector")),
    picker(book.sectors, sector.key, showValues ? "values" : ""),
    pages(sector, showValues ? "values" : ""),
  ];
  if (showValues) {
    fill(main, ...head, calc && Array.isArray(calc.goods) ? valuesView(unpack(calc), sector) : empty("기본값과 벤치마크의 자료를 불러오지 못했습니다."));
    return `${sector.name} 부문의 기본값과 벤치마크`;
  }
  fill(main, ...head,
    facts(sector),
    h("div", { class: "cols sector-cols" }, [
      h("div", { class: "sector-main" }, [docsSection(sector), goodsSection(sector, book), newsSection(sector), commonSection(book.common)]),
      h("div", { class: "sector-aside" }, [calcSection(sector), dutySection(duties.duties, today())]),
    ]),
  );
  return `${sector.name} 부문`;
}
