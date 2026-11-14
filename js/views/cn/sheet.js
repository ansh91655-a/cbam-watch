// 품목 한 장 보기(#cn-<코드>): 조회한 코드가 CBAM 대상이면 그 품목에 관한 것을 한 장에 모은다.
// 값과 비용은 인증서 비용 추정의 자료와 셈, 일정은 의무 일정, 근거 조문과 해설서의 절은 data/sheet.json,
// 소식과 개정안은 부문별 모아 보기의 자료에서 온다. 여기에서는 무엇을 어느 차례로 놓을지만 정한다(셈은 js/cn/sheet.js).
import * as data from "../../data.js";
import { unpack } from "../../calc/compute.js";
import { fixed } from "../../calc/numbers.js";
import { spaced } from "../../cn/names.js";
import { flagsOf, goodsUnder, line, nearest, sectorOf, sheetYear, shown, yearly } from "../../cn/sheet.js";
import { fill, h } from "../../ui/dom.js";
import { today } from "../../ui/format.js";
import { costSection } from "./sheet/cost.js";
import { guideSection, sectorSection } from "./sheet/links.js";
import { goodsSection, valuesSection } from "./sheet/values.js";

// 짧은 꼴로 실린 자료를 편 것. 글자를 넣을 때마다 다시 그리므로 한 번만 편다
let opened = null;
function bookOf(raw) {
  if (!opened || opened.raw !== raw) opened = { raw, book: unpack(raw) };
  return opened.book;
}

function head(code) {
  return h("div", { class: "cn-sheet-head" }, [
    h("h2", { id: "h-cn-sheet", text: `${spaced(code)} 한 장 보기` }),
    h("p", { class: "count", text: "이 품목에 관한 값과 비용의 어림, 일정, 근거 조문, 읽을 곳을 한 장에 모았습니다." }),
  ]);
}

// 값의 표에 이 코드의 품목이 없을 때의 안내
function noValues(now, book, sector) {
  const say = (text, link) => h("section", { class: "sheet-sec sheet-none", "aria-labelledby": "h-sheet-values" }, [
    h("h3", { id: "h-sheet-values", text: "기본값과 CBAM 벤치마크" }), h("p", { text }), link ? h("p", {}, link) : null,
  ]);
  if (!book) return say("값을 불러오지 못했습니다. 인증서 비용 추정 화면에서 확인해 주세요.", h("a", { href: `#calc-${now.query.slice(0, 8)}`, text: "인증서 비용 추정으로 가기" }));
  if (sector && !sector.calc) return say("이 부문의 품목은 인증서 비용 추정에 싣지 않았습니다. 기본값이 실린 곳은 아래의 근거 조문에서 확인해 주세요.");
  const near = nearest(book.goods, now.query);
  return say(`기본값과 CBAM 벤치마크의 표에 ${spaced(now.query)}의 품목이 없습니다. 8자리 CN 코드가 맞는지 확인해 주세요.`,
    near ? h("a", { href: `#cn-${near.code}`, text: `앞자리 ${spaced(near.code)} 아래의 품목 ${near.count}개 보기` }) : null);
}

function build(now, raw, factorBook, prices, duties, sectorBook, links) {
  const entries = now.rows.map((hit) => hit.entry);
  const sector = sectorOf(sectorBook.sectors, entries);
  const book = raw && Array.isArray(raw.goods) && raw.goods.length && factorBook.paths.length ? bookOf(raw) : null;
  const goods = book ? goodsUnder(book.goods, now.query) : [];
  const path = book ? factorBook.paths[0] : null;
  const latest = (prices.prices || [])[(prices.prices || []).length - 1];
  const price = latest ? latest.value : 0;
  const priceText = latest ? `${latest.label} 가격 ${fixed(price, 2)}유로` : "";   // 비용에 쓴 가격을 적는 말. 공개된 가격이 없으면 비용을 적지 않는다
  const year = book ? sheetYear(book, new Date().getFullYear()) : 0;
  const flags = flagsOf(entries, goods.length > 0, Boolean(sector && sector.calc));
  const parts = [];
  if (goods.length === 1) {
    const one = line(book, path, goods[0], year, price);
    parts.push(valuesSection(book, goods[0], one));
    if (one) parts.push(costSection(goods[0], one, yearly(book, path, goods[0], price), priceText, path.name));
  } else if (goods.length > 1) {
    parts.push(goodsSection(now.query, goods.map((good) => line(book, path, good, year, price)).filter(Boolean), goods.length, year, priceText));
  } else {
    parts.push(noValues(now, book, sector));
  }
  parts.push(guideSection(duties.duties, today(), shown(links.basis, flags), shown(links.read, flags)), sectorSection(sector));
  return [head(goods.length === 1 ? goods[0].code : now.query), ...parts.filter(Boolean)];
}

// now: 품목 코드 조회의 판정(js/cn/match.js의 verdict). 대상이거나 일부가 대상인 코드에만 쓴다.
// 자료를 받는 동안에는 빈 자리를 두고, 받으면 채운다. 결과를 읽어 주는 자리(aria-live) 안에 있으므로 이 자리의 변화는 읽어 주지 않게 한다.
export function sheet(now) {
  const holder = h("section", { class: "cn-sheet", "aria-labelledby": "h-cn-sheet", "aria-live": "off", "data-loading": "" }, head(now.query));
  Promise.all([data.calc(), data.factor(), data.prices(), data.duties(), data.sectors(), data.sheet()])
    .then((books) => fill(holder, ...build(now, ...books)))
    .catch(() => fill(holder, head(now.query), h("p", { class: "count" }, h("a", { href: `#calc-${now.query.slice(0, 8)}`, text: "이 품목의 인증서 비용 추정하기" }))))
    .finally(() => holder.removeAttribute("data-loading"));
  return holder;
}
