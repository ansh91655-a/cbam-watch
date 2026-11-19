// 부문별 모아 보기의 글을 자료에서 만든다: 산정 범위, 온실가스, 마크업, 다가오는 의무.
// 화면 요소를 다루지 않으므로 node로 시험한다(tests/test_sitejs.py).
import { GAS } from "../cn/names.js";

// 온실가스의 이름들: ["co2", "pfc"] → "이산화탄소, 과불화탄소"
export function gasText(gases) {
  return (gases || []).map((key) => GAS[key] || key).join(", ");
}

// 품목 한 줄의 산정 범위
export function scopeOf(row) {
  return row.directOnly ? "직접배출만" : "직접배출과 간접배출";
}

// 부문 전체의 산정 범위: 모두 같으면 한마디로, 섞여 있으면 줄 수를 적는다.
export function scopeText(goods) {
  const direct = (goods && goods.directOnly) || 0;
  const both = (goods && goods.both) || 0;
  if (!direct && !both) return "";
  if (!both) return "직접배출만(부속서 II)";
  if (!direct) return "직접배출과 간접배출";
  return `직접배출만 ${direct}줄, 직접배출과 간접배출 ${both}줄`;
}

// 기본값에 더하는 마크업: { 2026: 10, 2027: 20, 2028: 30 } → "2026년 10%, 2027년 20%, 2028년부터 30%"
// 마지막 값은 그 뒤의 해에도 쓰는 값이다(법령이 '몇 년부터'라고 적은 값).
export function markupText(markups) {
  const years = Object.keys(markups || {}).map(Number).filter(Boolean).sort((a, b) => a - b);
  return years.map((year, index) => `${year}년${index === years.length - 1 ? "부터" : ""} ${markups[String(year)]}%`).join(", ");
}

// 다가오는 의무 일정: 오늘부터의 것을 날짜 차례로 size건. scheme을 주면 그 제도의 것만.
export function upcoming(duties, todayIso, size = 3, scheme = "") {
  return (duties || []).filter((duty) => String(duty.date) >= todayIso && (!scheme || duty.scheme === scheme))
    .sort((a, b) => String(a.date).localeCompare(String(b.date))).slice(0, size);
}

// 개정안이 더하려는 품목을 알리는 말. 더하려는 것이 없으면 빈 글.
export function proposedText(name, proposed) {
  if (!proposed) return "";
  const parts = [proposed.own ? `${name} 품목 ${proposed.own}줄` : "", proposed.combined ? `복합 금속 제품 ${proposed.combined}줄` : ""].filter(Boolean);
  return parts.length ? `${parts.join("과 ")}을 더하려는 개정안이 심의 중입니다. 아직 법이 아니며, 최종 목록은 협상 결과에 따라 달라질 수 있습니다.` : "";
}
