// 추정 결과를 내려받는 표의 줄들(CSV로 적기 전의 꼴). 수는 자릿수만 줄여 적는다(소수점은 마침표).
// 화면 요소를 다루지 않는다(tests/test_calc_detail.py가 node로 돌린다).
import { estimate, series } from "./compute.js";

const round = (value, digits = 4) => Number(Number(value || 0).toFixed(digits));
const METHOD = { default: "default values", actual: "actual emissions" };

// 연도별 추정: 해마다 한 줄. input은 넣은 조건(estimate의 input)
export function yearlyRows(book, path, input) {
  const head = ["year", "cn_code", "method", "tonnes", "certificate_price_eur", "embedded_tco2e_per_t", "cbam_factor_percent", "cscf_percent", "free_allocation_adjustment_tco2e_per_t",
    "carbon_price_deduction_tco2e_per_t", "certificates_per_t", "certificates", "cost_per_t_eur", "cost_eur", "includes_assumed_values"];
  return [head, ...series(book, path, input).map((row) => [row.year, input.good.code, METHOD[row.mode], Number(input.tonnes) || 0, round(input.price, 2), round(row.embedded), row.factor, row.cscf, round(row.allocation),
    round(row.relieved), round(row.perTonne), round(row.certificates, 2), round(row.costPerTonne, 2), round(row.cost, 2), row.assumed.benchmark || row.assumed.cscf ? "yes" : "no"])];
}

// 담아 둔 추정들: 추정마다 한 줄과 합계. items: [{ input, path }] (input은 넣은 조건, path는 그 추정이 쓴 CBAM 계수의 경로)
// 돌려주는 것: { rows(머리 줄을 넣은 줄들), lines([{ input, row(추정 결과, 추정할 수 없으면 null) }]), certificates, cost }
export function basketRows(book, items) {
  const head = ["cn_code", "goods", "method", "year", "tonnes", "certificate_price_eur", "cbam_factor", "embedded_tco2e_per_t", "free_allocation_adjustment_tco2e_per_t",
    "carbon_price_deduction_tco2e_per_t", "certificates_per_t", "certificates", "cost_eur"];
  const lines = items.map(({ input, path }) => ({ input, path, row: estimate(book, path, input) }));
  const done = lines.filter((line) => line.row);
  const certificates = done.reduce((sum, line) => sum + line.row.certificates, 0);
  const cost = done.reduce((sum, line) => sum + line.row.cost, 0);
  const rows = [head, ...done.map(({ input, path, row }) => [input.good.code, input.good.text, METHOD[row.mode], row.year, Number(input.tonnes) || 0, round(input.price, 2), path.name || path.key || "",
    round(row.embedded), round(row.allocation), round(row.relieved), round(row.perTonne), round(row.certificates, 2), round(row.cost, 2)]),
    ["total", "", "", "", "", "", "", "", "", "", "", round(certificates, 2), round(cost, 2)]];
  return { rows, lines, certificates, cost };
}
