// 전구물질 한 줄의 셈. 복합제품을 실제 배출량으로 신고할 때, 전구물질마다 제품 1톤에 들어간 양에 그 전구물질의 값을 곱해 더한다.
//   내재배출량의 몫      = 들어간 양 × 전구물질 1톤의 내재배출량(넣은 값, 없으면 기본값 + 마크업)
//   무상할당 조정의 몫   = 들어간 양 × 전구물질 1톤의 고유 내재무상할당량(생산자가 준 값, 없으면 B열 벤치마크 × CBAM 계수 × 부문 간 보정계수)
// 화면 요소를 다루지 않는다(tests/test_calc.py가 node로 돌린다).
import { amount } from "./numbers.js";
import { cscf, defaultBenchmarkAt, factorAt, markup, period } from "./tables.js";

// 그해의 CBAM 계수와 부문 간 보정계수를 곱한 비율(0~1). 계수를 알 수 없는 해는 null
function share(book, path, year) {
  const factor = factorAt(path, year);
  return factor === null ? null : (factor / 100) * (cscf(book, year).value / 100);
}

// item: { good, choice(기본값 행의 자리), route(기본값 표와 다른 경로를 고르면), mass(제품 1톤에 들어간 양, t/t), see(넣은 내재배출량), sefa(넣은 고유 내재무상할당량) }
// year: 셈하는 해. base: 넣은 값이 가리키는 해(연도별 추정에서 다른 해를 셈할 때, 넣은 무상할당을 그해의 계수에 맞춘다)
// 들어간 양이 없으면 null(아직 다 넣지 않은 줄)
export function precursorLine(book, path, item, year, base = year) {
  const good = item && item.good;
  const mass = amount(item && item.mass);
  const now = share(book, path, year);
  if (!good || !mass || now === null) return null;
  const pair = good.defaults[item.choice || 0] || good.defaults[0];
  const rate = markup(book, good.sector, year);
  const seeGiven = amount(item.see);
  const see = seeGiven === null ? pair.row.total * (1 + rate / 100) : seeGiven;
  const picked = defaultBenchmarkAt(good, pair, period(book, year), item.route);
  const sefaGiven = amount(item.sefa);
  const then = share(book, path, base);
  // 넣은 무상할당은 넣은 해의 값이다. 다른 해에는 계수의 비율만큼 달라진다(넣은 해의 계수가 0이면 알 수 없어 기본 벤치마크로 정한다)
  const usable = sefaGiven !== null && (year === base || then > 0);
  const sefa = !usable ? picked.value * now : year === base ? sefaGiven : sefaGiven * (now / then);
  return {
    good, row: pair.row, mass,
    see: { value: see, given: seeGiven !== null, total: pair.row.total, markup: seeGiven === null ? rate : null },
    sefa: { value: sefa, given: usable, scaled: usable && year !== base, benchmark: picked.value, route: picked.route, routeAlt: picked.routeAlt },
    embedded: mass * see, allocation: mass * sefa,
  };
}

// 다 넣은 줄만 셈한 목록
export function precursorLines(book, path, items, year, base = year) {
  return (items || []).map((item) => precursorLine(book, path, item, year, base)).filter(Boolean);
}
