// 추정 결과: 인증서 수와 비용, 제품 1톤의 배출량이 어떻게 나뉘는지, 계산 내역, 연도별 추정.
import { estimate, series } from "../../calc/compute.js";
import { h, pill, table } from "../../ui/dom.js";

const fixed = (value, digits) => Number(value).toLocaleString("ko-KR", { minimumFractionDigits: digits, maximumFractionDigits: digits });
const tonnes = (value) => fixed(value, 3);                                   // 톤당 배출량(tCO2e)
const pieces = (value) => fixed(value, value >= 100 || value === 0 ? 0 : value >= 10 ? 1 : 2); // 인증서 수
const euros = (value) => fixed(value, value >= 1000 || value === 0 ? 0 : 2);  // 유로
const percent = (value) => `${fixed(value, Number.isInteger(value) ? 0 : 1)}%`;

function stats(now, state) {
  return h("div", { class: "stats calc-stats" }, [
    h("div", { class: "stat stat-hero" }, [
      h("span", { class: "stat-label", text: "제출할 인증서(추정)" }),
      h("span", { class: "stat-value" }, [h("span", { text: pieces(now.certificates) }), h("small", { text: "개" })]),
      h("span", { class: "stat-note", text: `${now.year}년 수입분 ${fixed(state.tonnes, 0)}톤` }),
    ]),
    h("div", { class: "stat" }, [
      h("span", { class: "stat-label", text: "인증서 비용(추정)" }),
      h("span", { class: "stat-value" }, [h("span", { text: euros(now.cost) }), h("small", { text: "유로" })]),
      h("span", { class: "stat-note", text: `인증서 가격 ${fixed(state.price, 2)}유로 기준` }),
    ]),
    h("div", { class: "stat" }, [
      h("span", { class: "stat-label", text: "제품 1톤당" }),
      h("span", { class: "stat-value" }, [h("span", { text: euros(now.costPerTonne) }), h("small", { text: "유로" })]),
      h("span", { class: "stat-note", text: `인증서 ${tonnes(now.perTonne)}개` }),
    ]),
  ]);
}

// 제품 1톤의 내재배출량을 두 몫으로 나눈 막대. 색만으로 가리지 않도록 범례에 이름과 값을 함께 적는다.
function split(now) {
  const whole = now.embedded || 1;
  const covered = (now.covered / whole) * 100;
  return h("div", { class: "calc-split" }, [
    h("div", { class: "calc-bar", role: "img", "aria-label": `제품 1톤의 내재배출량 ${tonnes(now.embedded)}톤 가운데 무상할당 조정 ${tonnes(now.covered)}톤, 인증서 대상 ${tonnes(now.perTonne)}톤` }, [
      covered > 0 ? h("span", { class: "calc-seg calc-seg-free", style: `flex-grow:${covered.toFixed(3)}` }) : null,
      covered < 100 ? h("span", { class: "calc-seg calc-seg-pay", style: `flex-grow:${(100 - covered).toFixed(3)}` }) : null,
    ]),
    h("ul", { class: "chart-legend" }, [
      h("li", {}, [h("span", { class: "key key-2" }), h("span", { text: "무상할당 조정" }), h("small", { text: `${tonnes(now.covered)} tCO2e` })]),
      h("li", {}, [h("span", { class: "key" }), h("span", { text: "인증서 대상" }), h("small", { text: `${tonnes(now.perTonne)} tCO2e` })]),
    ]),
  ]);
}

function steps(now, state, row) {
  const origin = row.origin === "kr" ? "대한민국 기본값" : "'그 밖의 나라와 지역' 기본값";
  const embedded = now.mode === "actual"
    ? "넣으신 실제 배출량입니다."
    : `${origin} ${tonnes(row.total)}에 ${now.year}년 마크업 ${percent(now.markup)}를 더한 값입니다.`;
  const lines = [
    ["내재배출량", `${tonnes(now.embedded)} tCO2e`, embedded],
    ["무상할당 조정", `${tonnes(now.allocation)} tCO2e`, `CBAM 벤치마크 ${tonnes(now.benchmark)} × CBAM 계수 ${percent(now.factor)} × 부문 간 보정계수 ${percent(now.cscf)}`],
    ["인증서 대상", `${tonnes(now.perTonne)} tCO2e`, now.allocation > now.embedded ? "무상할당 조정이 내재배출량보다 커서 0으로 보았습니다." : "내재배출량에서 무상할당 조정을 뺀 값입니다."],
  ];
  return h("dl", { class: "calc-steps" }, lines.flatMap(([name, value, how]) => [
    h("dt", { text: name }),
    h("dd", {}, [h("b", { text: value }), h("span", { text: how })]),
  ]));
}

// 그해의 값 가운데 법령으로 정해지지 않아 가정한 것이 있으면 알린다.
function flags(now) {
  const found = [];
  if (now.assumed.benchmark || now.assumed.cscf) found.push("2031년 이후의 CBAM 벤치마크와 부문 간 보정계수는 아직 정해지지 않아, 2028~2030년의 벤치마크와 보정계수 100%를 그대로 썼습니다.");
  else if (now.assumed.updated) found.push("2027년 수입분부터는 갱신된 CBAM 벤치마크가 적용될 예정입니다. 지금 시행 중인 값으로 계산한 참고용 추정입니다.");
  return found.map((text) => h("p", { class: "calc-flag", text }));
}

function compare(book, path, state, now) {
  if (state.mode !== "actual") return null;
  const other = estimate(book, path, { ...state, mode: "default" });
  if (!other) return null;
  const gap = other.cost - now.cost;
  const tail = Math.abs(gap) < 0.005 ? "차이가 없습니다." : gap > 0 ? `실제 배출량으로 신고할 때보다 ${euros(gap)}유로 많습니다.` : `실제 배출량으로 신고할 때보다 ${euros(-gap)}유로 적습니다.`;
  return h("p", { class: "calc-compare" }, [
    h("b", { text: "기본값으로 신고한다면" }),
    h("span", { text: `인증서 ${pieces(other.certificates)}개, 비용 ${euros(other.cost)}유로로 추정됩니다. ${tail}` }),
  ]);
}

function yearly(book, path, state) {
  const rows = series(book, path, state);
  const top = Math.max(...rows.map((row) => row.costPerTonne), 0.0001);
  // 결과(비용, 인증서)를 앞에 두고 그 값을 이루는 것들을 뒤에 둔다. 좁은 화면에서도 결과가 먼저 보인다.
  return table(["수입 연도", { text: "비용(톤당, 유로)", num: true }, { text: "인증서(톤당)", num: true }, { text: "내재배출량", num: true }, { text: "CBAM 계수", num: true }, { text: "무상할당 조정", num: true }],
    rows.map((row) => h("tr", { class: row.year === state.year ? "calc-now" : null }, [
      h("td", {}, [h("span", { text: `${row.year}년` }), row.assumed.benchmark || row.assumed.cscf ? pill("가정 포함", "warn") : null]),
      h("td", { class: "num calc-cost" }, [h("span", { class: "calc-mini", "aria-hidden": "true", style: `width:${((row.costPerTonne / top) * 100).toFixed(1)}%` }), h("b", { text: euros(row.costPerTonne) })]),
      h("td", { class: "num", text: tonnes(row.perTonne) }),
      h("td", { class: "num", text: tonnes(row.embedded) }),
      h("td", { class: "num", text: percent(row.factor) }),
      h("td", { class: "num", text: tonnes(row.allocation) }),
    ])), "연도별 추정");
}

// state: { good, choice, mode, see, route, year, tonnes, price }, path: CBAM 계수의 경로
export function result(book, path, state) {
  const now = estimate(book, path, state);
  if (!now) {
    return [h("p", { class: "empty", text: state.mode === "actual" ? "제품 1톤당 내재배출량을 넣으면 추정 결과가 나옵니다." : "이 조건으로는 추정할 수 없습니다. 연도와 값을 확인해 주세요." })];
  }
  const row = (state.good.defaults[state.choice] || state.good.defaults[0]).row;
  return [
    stats(now, state),
    ...flags(now),
    h("section", { class: "panel calc-detail", "aria-labelledby": "h-calc-split" }, [
      h("h2", { id: "h-calc-split", text: `제품 1톤의 배출량(${now.year}년)` }),
      split(now),
      steps(now, state, row),
      compare(book, path, state, now),
    ]),
    h("section", { class: "stack", "aria-labelledby": "h-calc-years" }, [
      h("h2", { id: "h-calc-years", text: "연도별 추정" }),
      h("p", { class: "sub calc-sub", text: `같은 품목과 인증서 가격(${fixed(state.price, 2)}유로)으로 해마다 계산한 값입니다. CBAM 계수는 '${path.name}'의 값을 썼습니다.` }),
      yearly(book, path, state),
    ]),
  ];
}
