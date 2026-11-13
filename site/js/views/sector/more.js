// 부문별 모아 보기의 나머지 칸: 기본값과 비용 추정, 다가오는 의무 일정, 소식.
import { dutyHref } from "../../laws/refs.js";
import { markupText, upcoming } from "../../sector/facts.js";
import { target } from "../../ui/sitesearch.js";
import { h, safeLink } from "../../ui/dom.js";
import { count, day, koreanDate } from "../../ui/format.js";
import { icon } from "../../ui/icons.js";

export function calcSection(sector) {
  const calc = sector.calc;
  if (!calc) {
    return h("section", { class: "panel sector-side", "aria-labelledby": "h-sector-calc" }, [
      h("h2", { id: "h-sector-calc", text: "기본값과 비용 추정" }),
      h("p", { text: `${sector.name}은 인증서 비용 추정에 싣지 않았습니다. 기본값과 산정 방법은 위의 안내 문서에서 확인하세요.` }),
    ]);
  }
  const markups = markupText(calc.markups);
  return h("section", { class: "panel sector-side", "aria-labelledby": "h-sector-calc" }, [
    h("h2", { id: "h-sector-calc", text: "기본값과 비용 추정" }),
    h("p", { text: `${sector.name} 품목 ${count(calc.goods)}개(8자리 CN 코드)에 대한민국의 기본값과 CBAM 벤치마크가 정해져 있습니다.` }),
    markups ? h("p", { class: "sector-markup" }, [h("b", { text: "기본값에 더하는 마크업" }), h("span", { text: markups })]) : null,
    h("p", {}, h("a", { class: "btn btn-main", href: calc.first ? `#calc-${calc.first}` : "#calc" }, [icon("emissions", 15), h("span", { text: "품목을 골라 비용 추정하기" })])),
    h("p", { class: "count" }, [h("span", { text: "근거: " }), h("a", { href: "#law-32025R2621", text: "기본값 이행규정" }), h("span", { text: ", " }), h("a", { href: "#law-32025R2620", text: "무상할당 조정 이행규정" })]),
  ]);
}

export function dutySection(duties, todayIso) {
  const next = upcoming(duties, todayIso, 3, "eu");
  if (!next.length) return null;
  return h("section", { class: "panel sector-side", "aria-labelledby": "h-sector-duties" }, [
    h("div", { class: "panel-head" }, [h("h2", { id: "h-sector-duties", text: "다가오는 의무 일정" }), h("a", { class: "more", href: "#calendar", text: "일정 모두 보기" })]),
    h("ul", { class: "sector-dates" }, next.map((duty) => h("li", {}, [
      h("time", { datetime: duty.date, text: koreanDate(duty.date) }),
      h("a", { href: dutyHref(duty), text: duty.title }),
      h("span", { class: "count", text: duty.who }),
    ]))),
    h("p", { class: "count", text: "의무 일정은 모든 부문에 같습니다. 법령에 날짜가 적힌 것만 실었습니다." }),
  ]);
}

function newsLink(item) {
  if (!item.link) return h("a", { href: `#item-${item.id}`, text: item.title });
  const link = safeLink(item.link, item.title);   // 제목만 실은 소식은 원문으로 바로 간다
  if (link) link.append(icon("out", 13));
  return link || h("span", { text: item.title });
}

export function newsSection(sector) {
  if (!sector.items.length) return null;
  const word = (sector.words || [])[0] || sector.name;
  return h("section", { class: "stack sector-sec", "aria-labelledby": "h-sector-news" }, [
    h("div", { class: "sec-head" }, [h("h2", { id: "h-sector-news", text: `${sector.name} 소식` }), h("a", { href: target(word), text: `'${word}'로 찾은 것 모두 보기` })]),
    h("p", { class: "sector-lead", text: `제목이나 요약에 ${sector.name}이 나오는 소식 ${count(sector.itemCount)}건 가운데 최근 것입니다.` }),
    h("ul", { class: "sector-news" }, sector.items.map((item) => h("li", {}, [h("time", { datetime: item.date, text: day(item.date) }), newsLink(item)]))),
  ]);
}
