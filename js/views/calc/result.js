// 추정 결과: 인증서 수와 비용, 제품 1톤의 배출량이 어떻게 나뉘는지, 계산 내역, 기본값과의 견줌, 연도별 추정.
// 계산 내역은 steps.js, 견줌은 compare.js, 연도별 표는 yearly.js가 짓는다.
import { estimate } from "../../calc/compute.js";
import { yearlyRows } from "../../calc/export.js";
import { euros, fixed, pieces, tonnes } from "../../calc/numbers.js";
import { csvText } from "../../ui/csv.js";
import { h } from "../../ui/dom.js";
import { icon } from "../../ui/icons.js";
import { saveCsv } from "../../ui/save.js";
import { splitBar } from "../../ui/splitbar.js";
import { compare } from "./compare.js";
import { steps } from "./steps.js";
import { yearly } from "./yearly.js";

function stats(now, state) {
  return h("div", { class: "stats calc-stats" }, [
    h("div", { class: "stat stat-hero" }, [
      h("span", { class: "stat-label", text: "제출할 인증서(추정)" }),
      h("span", { class: "stat-value" }, [h("span", { text: pieces(now.certificates) }), h("small", { text: "개" })]),
      h("span", { class: "stat-note", text: `${now.year}년 수입분 ${fixed(state.tonnes || 0, 0)}톤` }),
    ]),
    h("div", { class: "stat" }, [
      h("span", { class: "stat-label", text: "인증서 비용(추정)" }),
      h("span", { class: "stat-value" }, [h("span", { text: euros(now.cost) }), h("small", { text: "유로" })]),
      h("span", { class: "stat-note", text: `인증서 가격 ${fixed(state.price || 0, 2)}유로 기준` }),
    ]),
    h("div", { class: "stat" }, [
      h("span", { class: "stat-label", text: "제품 1톤당" }),
      h("span", { class: "stat-value" }, [h("span", { text: euros(now.costPerTonne) }), h("small", { text: "유로" })]),
      h("span", { class: "stat-note", text: `인증서 ${tonnes(now.perTonne)}개` }),
    ]),
  ]);
}

// 제품 1톤의 내재배출량을 몫으로 나눈 막대: 무상할당 조정, (있으면) 탄소가격 차감, 인증서 대상.
// 색만으로 가리지 않도록 범례에 이름과 값을 함께 적는다.
function split(now) {
  const whole = now.embedded || 1;
  const share = (value) => (value / whole) * 100;
  const cut = now.deduction ? `, 탄소가격 차감 ${tonnes(now.relieved)}톤` : "";
  return splitBar({
    label: `제품 1톤의 내재배출량 ${tonnes(now.embedded)}톤 가운데 무상할당 조정 ${tonnes(now.covered)}톤${cut}, 인증서 대상 ${tonnes(now.perTonne)}톤`,
    parts: [
      { name: "무상할당 조정", share: share(now.covered), note: `${tonnes(now.covered)} tCO2e`, tone: "free" },
      now.deduction ? { name: "탄소가격 차감", share: share(now.relieved), note: `${tonnes(now.relieved)} tCO2e`, tone: "cut" } : null,
      { name: "인증서 대상", share: share(now.perTonne), note: `${tonnes(now.perTonne)} tCO2e`, tone: "pay" },
    ].filter(Boolean),
  });
}

// 그해의 값 가운데 법령으로 정해지지 않아 가정한 것이 있으면 알린다.
function flags(now) {
  const found = [];
  if (now.assumed.benchmark || now.assumed.cscf) found.push("2031년 이후의 CBAM 벤치마크와 부문 간 보정계수는 아직 정해지지 않아, 2028~2030년의 벤치마크와 보정계수 100%를 그대로 썼습니다.");
  else if (now.assumed.updated) found.push("2027년 수입분부터는 갱신된 CBAM 벤치마크가 적용될 예정입니다. 지금 시행 중인 값으로 계산한 참고용 추정입니다.");
  return found.map((text) => h("p", { class: "calc-flag", text }));
}

// 아직 추정할 수 없을 때의 안내
function waiting(state) {
  if (state.mode === "actual") return "제품 1톤당 직접배출량을 넣으면 추정 결과가 나옵니다.";
  return "이 조건으로는 추정할 수 없습니다. 연도와 값을 확인해 주세요.";
}

// state: 넣은 조건(views/calc.js), path: CBAM 계수의 경로.
// 돌려주는 것: { nodes(화면에 놓을 것들), ready(추정이 나왔는지), said(화면 낭독기에 알릴 한 줄) }
export function result(book, path, state) {
  const now = estimate(book, path, state);
  if (!now) return { nodes: [h("p", { class: "empty", text: waiting(state) })], ready: false, said: waiting(state) };
  const row = (state.good.defaults[state.choice] || state.good.defaults[0]).row;
  const nodes = [
    stats(now, state),
    ...flags(now),
    h("section", { class: "panel calc-detail", "aria-labelledby": "h-calc-split" }, [
      h("h2", { id: "h-calc-split", text: `제품 1톤의 배출량(${now.year}년)` }),
      split(now),
      steps(book, now, state, row),
      h("p", { class: "count", text: "내재배출량, 마크업, 전구물질, CBAM 벤치마크, CBAM 계수, 부문 간 보정계수, 탄소가격 차감의 뜻은 아래 '용어 풀이'에 있습니다." }),
      compare(book, path, state, now),
    ]),
    h("section", { class: "stack", "aria-labelledby": "h-calc-years" }, [
      h("div", { class: "sec-head" }, [
        h("h2", { id: "h-calc-years", text: "연도별 추정" }),
        h("button", { type: "button", class: "btn", onclick: () => saveCsv(`cbam-estimate-${state.good.code}.csv`, csvText(yearlyRows(book, path, state))) },
          [icon("download", 15), h("span", { text: "표 내려받기(CSV)" })]),
      ]),
      ...yearly(book, path, state),
    ]),
  ];
  return { nodes, ready: true, said: `제출할 인증서 ${pieces(now.certificates)}개, 인증서 비용 ${euros(now.cost)}유로로 추정됩니다.` };
}
