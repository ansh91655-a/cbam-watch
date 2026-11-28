// 인증서 비용 추정의 셈. 화면과 떨어져 있어 시험할 수 있다(tests/test_calc.py가 node로 돌린다).
// 자료(data/calc.json)는 법령의 표에서 만든 것이고, 여기에서는 법령의 식을 그대로 따른다. 제품 1톤에 대해:
//   내재배출량    = 기본값의 총배출량 × (1 + 마크업)                                 기본값으로 신고할 때
//                 = 넣은 직접배출량 + 간접배출량 (+ 전구물질의 몫)                   실제 배출량으로 신고할 때
//   무상할당 조정 = B열 벤치마크 × CBAM 계수 × 부문 간 보정계수                      기본값으로 신고할 때, 전구물질을 따로 넣지 않고 어림할 때
//                 = A열 벤치마크 × CBAM 계수 × 부문 간 보정계수 + Σ(전구물질의 양 × 그 전구물질의 고유 내재무상할당량)   전구물질을 따로 넣을 때
//   탄소가격 차감 = 제품 1톤당 실질 지불 탄소가격 ÷ 기준가격, 또는 기본 탄소가격 × 내재배출량 ÷ 기준가격
//   인증서        = 내재배출량 − 무상할당 조정 − 탄소가격 차감 (0보다 작으면 0)
// 표에서 값을 고르는 일은 tables.js, 전구물질 한 줄은 precursor.js, 탄소가격 차감은 carbon.js가 한다.
import { deduction, referencePrice } from "./carbon.js";
import { amount } from "./numbers.js";
import { precursorLines } from "./precursor.js";
import { benchmarkAt, cscf, defaultRoutes, factorAt, markup, period, processBenchmarkAt, routesOf } from "./tables.js";

export * from "./tables.js";

const sum = (lines, key) => lines.reduce((total, line) => total + line[key], 0);
const listed = (input) => input.mode === "actual" && input.pre === "listed";  // 전구물질을 따로 넣어 셈하는지

// 신고하는 내재배출량과 그 몫. 실제 배출량인데 직접배출량을 넣기 전이면 null
function declared(book, input, pair, lines) {
  if (input.mode !== "actual") {
    const rate = markup(book, input.good.sector, input.year);
    return { value: pair.row.total * (1 + rate / 100), markup: rate, direct: null, indirect: null, inputs: 0 };
  }
  const direct = amount(input.direct === undefined ? input.see : input.direct);  // 옛 이름 see(내재배출량 하나)도 받는다
  if (direct === null) return null;
  const indirect = pair.row.indirect === null ? 0 : amount(input.indirect) || 0;  // 직접배출량만 세는 품목은 간접배출량이 없다
  const inputs = listed(input) && input.scope === "process" ? sum(lines, "embedded") : 0;
  return { value: direct + indirect + inputs, markup: null, direct, indirect, inputs };
}

// 무상할당 조정과 그 몫. share: 그해의 CBAM 계수 × 부문 간 보정계수(0~1)
function allocated(input, pair, span, share, lines) {
  const good = input.good;
  let route = pair.route;   // 벤치마크를 고른 생산경로(경로를 가르지 않는 품목은 "")
  let routeAlt = "";        // 기본값으로 신고할 때 함께 견준 경로(합금강: 두 등급 가운데 큰 값을 쓴다)
  let column = "B";
  let benchmark;
  if (input.mode !== "actual") {
    benchmark = pair.benchmark[span.index];
    routeAlt = defaultRoutes(good, pair)[1] || "";
  } else {
    if (routesOf(good).includes(input.route)) route = input.route;
    column = listed(input) ? "A" : "B";
    benchmark = column === "A" ? processBenchmarkAt(good, route, span.key) : benchmarkAt(good, route, span.key);
  }
  if (benchmark === null) return null;
  const inputs = column === "A" ? sum(lines, "allocation") : 0;
  // 전구물질을 따로 넣지 않은 실제 배출량: 전구물질의 몫까지 넣어 둔 B열로 대신한 어림인지(A열과 B열이 같은 품목은 어림이 아니다)
  const rough = input.mode === "actual" && column === "B" && processBenchmarkAt(good, route, span.key) !== benchmark;
  return { value: benchmark * share + inputs, benchmark, column, route, routeAlt, process: benchmark * share, inputs, rough };
}

// 기준가격: 넣은 값, 없으면 그해에 공개된 인증서 가격의 평균, 그것도 없으면 넣은 인증서 가격
function reference(input, year) {
  const given = amount(input.carbon.ref);
  if (given) return { value: given, from: "given" };
  const known = referencePrice(input.prices, year);
  if (known) return { value: known.value, from: known.partial ? "partial" : "year", count: known.count };
  return { value: Number(input.price) || 0, from: "price" };
}

// 탄소가격 차감(제품 1톤당 인증서 수). 넣지 않았거나 셈할 수 없으면 null
function relief(input, own) {
  const carbon = input.carbon;
  if (!carbon || !carbon.how || carbon.how === "none") return null;
  if (input.mode !== "actual" && carbon.how === "paid") return null;  // 기본값으로 신고하면 기본 탄소가격으로만 청구할 수 있다
  const ref = reference(input, input.year);
  const found = deduction(carbon, own.value, ref.value, own.direct);
  return found ? { ...found, refFrom: ref.from, refCount: ref.count || 0 } : null;
}

// 한 해의 추정.
// input: { good, choice(기본값 짝의 자리), mode("default" | "actual"), year, tonnes, price(인증서 가격),
//   실제 배출량일 때: direct(제품 1톤당 직접배출량), indirect(간접배출량), route(생산경로),
//     pre("none" | "listed": 전구물질을 따로 넣는지), scope("whole" | "process": 넣은 배출량이 전구물질의 몫을 담고 있는지), precursors([{ good, choice, route, mass, see, sefa }]),
//   탄소가격 차감: carbon({ how("none" | "paid" | "default"), entry("report" | "build"), perTonne, price, covered, free, rate, other, dcp, ref }), prices(data/prices.json),
//   base(넣은 값이 가리키는 해. 연도별 추정이 넣는다) }
// 돌려주는 값의 단위: 톤당 값은 tCO2e/t, certificates는 tCO2e(= 인증서 수), cost는 유로.
export function estimate(book, path, input) {
  const { good, mode, year } = input;
  const pair = good.defaults[input.choice || 0] || good.defaults[0];
  const span = period(book, year);
  const factor = factorAt(path, year);
  const correction = cscf(book, year);
  if (factor === null) return null;
  const lines = listed(input) ? precursorLines(book, path, input.precursors, year, input.base === undefined ? year : input.base) : [];
  const own = declared(book, input, pair, lines);
  const free = allocated(input, pair, span, (factor / 100) * (correction.value / 100), lines);
  if (!own || !free) return null;
  const embedded = own.value;
  const allocation = free.value;
  const left = Math.max(0, embedded - allocation);
  const cut = relief(input, own);
  const relieved = cut ? Math.min(left, cut.certificates) : 0;   // 차감은 남은 인증서까지만 줄인다
  const perTonne = left - relieved;
  const tonnes = Number(input.tonnes) || 0;
  const price = Number(input.price) || 0;
  return {
    year, mode, embedded, markup: own.markup, parts: { direct: own.direct, indirect: own.indirect, inputs: own.inputs },
    benchmark: free.benchmark, column: free.column, route: free.route, routeAlt: free.routeAlt, factor, cscf: correction.value,
    allocation, process: free.process, inputAllocation: free.inputs, lines, rough: free.rough, perTonne,
    covered: Math.min(embedded, allocation),            // 무상할당 조정으로 덜어지는 몫(톤당)
    deduction: cut, relieved,                           // 탄소가격 차감과, 그 가운데 실제로 덜어진 몫(톤당)
    certificates: perTonne * tonnes, cost: perTonne * tonnes * price, costPerTonne: perTonne * price,
    assumed: { benchmark: span.assumed, cscf: correction.assumed, updated: year >= 2027 },
  };
}

// 여러 해의 추정(물량과 가격, 넣은 값은 그대로 두고 해만 바꾼다). 넣은 값은 고른 해(input.year)의 것으로 본다.
export function series(book, path, input) {
  const rows = [];
  for (let year = book.years.from; year <= book.years.to; year += 1) rows.push(estimate(book, path, { ...input, year, base: input.year }));
  return rows.filter(Boolean);
}
