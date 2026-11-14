// 부문별 모아 보기의 '대상 품목': CBAM 규정 부속서 I에 실린 그 부문의 품목 줄과, 줄마다의 온실가스와 산정 범위.
import { spaced } from "../../cn/names.js";
import { gasText, proposedText, scopeOf } from "../../sector/facts.js";
import { h, safeLink, table } from "../../ui/dom.js";
import { icon } from "../../ui/icons.js";
import { stackable } from "../../ui/stack.js";

function row(good) {
  const code = (good.codes || [])[0] || "";
  return h("tr", {}, [
    h("td", {}, h("a", { class: "cn-code", href: `#cn-${code}`, title: "품목 코드 조회에서 보기", text: `${good.ex ? "ex " : ""}${good.shown.replace(/^ex /, "")}` })),
    h("td", { lang: "en", text: good.text }),
    h("td", { text: gasText(good.gases) }),
    h("td", { text: scopeOf(good) }),
    h("td", {}, good.calc ? h("a", { href: `#calc-${good.calc}`, title: `${spaced(good.calc)}부터 비용 추정에서 보기`, text: "비용 추정" }) : h("span", { class: "count", text: "없음" })),
  ]);
}

export function goodsSection(sector, book) {
  const goods = sector.goods;
  const basis = safeLink((book.law || {}).url, (book.law || {}).name || "CBAM 규정 부속서 I");
  if (basis) basis.append(icon("out", 13));
  const proposed = proposedText(sector.name, sector.proposed);
  return h("section", { class: "stack sector-sec", "aria-labelledby": "h-sector-goods" }, [
    h("div", { class: "sec-head" }, [h("h2", { id: "h-sector-goods", text: "대상 품목" }), h("a", { href: "#cn", text: "품목 코드 조회" })]),
    h("p", { class: "sector-lead" }, [h("span", { text: `부속서 I의 ${sector.name} 품목은 CN 코드 ${goods.rows.length}줄입니다. 품목 이름은 법령의 원문대로 적었습니다. 근거: ` }), basis || h("span", { text: "CBAM 규정 부속서 I" })]),
    stackable(table(["CN 코드", "품목", "온실가스", "산정 범위", "기본값·벤치마크"], goods.rows.map(row), `${sector.name} 대상 품목`)),
    goods.rows.some((good) => good.ex) ? h("p", { class: "count", text: "코드 앞의 ex는 그 코드의 품목 가운데 품목 이름에 해당하는 것만 든다는 뜻입니다." }) : null,
    proposed ? h("p", { class: "sector-proposed" }, [h("span", { text: proposed }), h("a", { href: "#cn", text: "개정안의 품목 보기" })]) : null,
  ]);
}
