// 품목 한 장 보기의 비용: 품목 하나를 기본값으로 신고할 때 제품 1톤에 드는 인증서와 비용의 어림, 해마다의 흐름.
// 값과 가정은 인증서 비용 추정 화면과 같다(같은 셈, 같은 자료). 물량과 조건을 바꾸는 일은 그 화면으로 잇는다.
import { euros, percent, tonnes } from "../../../calc/numbers.js";
import { h } from "../../../ui/dom.js";
import { icon } from "../../../ui/icons.js";
import { splitBar } from "../../../ui/splitbar.js";

function how(now) {
  const origin = now.row.origin === "kr" ? "대한민국 기본값" : "'그 밖의 나라와 영역' 기본값";
  const tail = now.allocation > now.embedded ? "무상할당 조정이 내재배출량보다 커서 인증서를 0으로 보았습니다." : "내재배출량에서 무상할당 조정을 뺀 값이 인증서 대상입니다.";
  return `${origin} ${tonnes(now.value)}에 ${now.year}년 마크업 ${percent(now.markup)}를 더한 내재배출량은 ${tonnes(now.embedded)} tCO2e입니다. 무상할당 조정은 ${tonnes(now.allocation)} tCO2e입니다`
    + `(CBAM 벤치마크 ${tonnes(now.benchmark)} × CBAM 계수 ${percent(now.factor)} × 부문 간 보정계수 ${percent(now.cscf)}). ${tail}`;
}

// 해마다의 제품 1톤당 비용과 인증서 수. 막대의 길이는 가장 큰 해를 100으로 본 것이다. 공개된 가격이 없으면(priced가 거짓) 인증서 수만 적는다
function years(rows, current, priced) {
  const size = (row) => (priced ? row.costPerTonne : row.perTonne);
  const top = Math.max(...rows.map(size), 0.0001);
  return h("ol", { class: "sheet-years" }, rows.map((row) => h("li", { "aria-current": row.year === current ? "true" : null }, [
    h("span", { class: "sheet-year", text: `${row.year}년` }),
    h("span", { class: "sheet-bar", "aria-hidden": "true" }, h("span", { style: `width:${((size(row) / top) * 100).toFixed(1)}%` })),
    priced ? h("b", { text: `${euros(row.costPerTonne)}유로` }) : h("b", { text: `${tonnes(row.perTonne)}개` }),
    priced ? h("span", { class: "count", text: `${tonnes(row.perTonne)}개` }) : null,
  ])));
}

// now: 올해의 값(js/cn/sheet.js의 line), rows: 해마다의 값(yearly), pathName: CBAM 계수의 경로 이름,
// priceText: 비용에 쓴 인증서 가격을 적은 말("2026년 3분기 가격 82.32유로"). 공개된 가격이 없으면 ""이고, 그때는 비용을 적지 않는다
export function costSection(good, now, rows, priceText, pathName) {
  const covered = now.embedded ? (now.covered / now.embedded) * 100 : 0;
  const late = rows.some((row) => row.assumed);
  const priced = Boolean(priceText);
  return h("section", { class: "sheet-sec sheet-cost", "aria-labelledby": "h-sheet-cost" }, [
    h("div", { class: "sheet-sec-head" }, [
      h("h3", { id: "h-sheet-cost", text: "인증서 비용의 어림" }),
      h("p", { class: "count", text: `${now.year}년 수입분, 제품 1톤, 기본값으로 신고할 때${now.more ? `(세부 품목 '${now.row.text}' 기준)` : ""}` }),
    ]),
    h("div", { class: "sheet-two" }, [
      h("div", { class: "sheet-block" }, [
        h("div", { class: "sheet-stats" }, [
          h("p", {}, [h("span", { text: "제출할 인증서" }), h("b", {}, [h("span", { text: tonnes(now.perTonne) }), h("small", { text: "개" })])]),
          priced ? h("p", {}, [h("span", { text: "비용" }), h("b", {}, [h("span", { text: euros(now.costPerTonne) }), h("small", { text: "유로" })])]) : null,
        ]),
        splitBar({
          label: `제품 1톤의 내재배출량 ${tonnes(now.embedded)}톤 가운데 무상할당 조정 ${tonnes(now.covered)}톤, 인증서 대상 ${tonnes(now.perTonne)}톤`,
          parts: [
            { name: "무상할당 조정", share: covered, note: `${tonnes(now.covered)} tCO2e`, tone: "free" },
            { name: "인증서 대상", share: 100 - covered, note: `${tonnes(now.perTonne)} tCO2e`, tone: "pay" },
          ],
        }),
        h("p", { class: "sheet-how", text: how(now) }),
        h("p", {}, h("a", { class: "btn", href: `#calc-${good.code}` }, [icon("emissions", 15), h("span", { text: "물량과 연도, 신고 방법을 바꿔 추정하기" })])),
      ]),
      h("div", { class: "sheet-block" }, [
        h("p", { class: "sheet-label" }, [h("span", { text: priced ? "해마다의 비용" : "해마다의 인증서 수" }), h("small", { text: priced ? "제품 1톤당 유로와 인증서 수" : "제품 1톤당" })]),
        years(rows, now.year, priced),
      ]),
    ]),
    h("p", { class: "count sheet-foot", text: [
      priced ? `인증서 가격은 모든 해에 ${priceText}를 썼고, CBAM 계수는 '${pathName}'의 값입니다.` : `공개된 인증서 가격이 없어 비용은 싣지 않았습니다. CBAM 계수는 '${pathName}'의 값입니다.`,
      "2027년 수입분부터는 갱신된 CBAM 벤치마크가 적용될 예정입니다.",
      late ? "2031년 이후의 CBAM 벤치마크와 부문 간 보정계수는 아직 정해지지 않아 2028~2030년의 벤치마크와 보정계수 100%를 그대로 썼습니다." : "",
      "제3국에서 낸 탄소가격의 공제는 넣지 않았습니다.",
    ].filter(Boolean).join(" ") }),
  ]);
}
