// 탄소가격 차감의 셈. 제3국에서 낸 탄소가격만큼 제출할 인증서 수를 줄인다(이행규정 (EU) 2026/2498 제7조).
//   실질적으로 지불된 탄소가격으로:  차감(인증서) = 제품 1톤당 실질 지불 탄소가격(유로) ÷ 기준가격 × 물량
//   기본 탄소가격으로:              차감(인증서) = 기본 탄소가격(유로/tCO2e) × 신고한 내재배출량 ÷ 기준가격 × 물량
// 기준가격은 수입한 해의 CBAM 인증서 가격을 평균한 값이다. 화면 요소를 다루지 않는다(tests/test_calc.py가 node로 돌린다).
import { amount } from "./numbers.js";
import { yearMean } from "./prices.js";

// 수입한 해의 기준가격: 그해의 것으로 공개된 인증서 가격의 평균(센트까지). 그해의 가격이 하나도 없으면 null.
// book: data/prices.json({ prices: [{ from, to, value }], upcoming: [{ from }] }). partial: 그해의 가격이 더 남아 있는지(셈은 calc/prices.js의 yearMean)
export function referencePrice(book, year) {
  const found = yearMean(book, year);
  return found ? { value: found.value, count: found.count, partial: found.partial } : null;
}

// 제품 1톤당 실질적으로 지불된 탄소가격(유로).
//   entry "report": 인증보고서에 적힌 값(perTonne)
//   entry "build":  (가격이 매겨진 배출량 − 값을 치르지 않은 몫) × 탄소가격 ÷ 환율 + 그 밖의 몫(간접배출량이나 전구물질에 치러진 값)
// carbon: { entry, perTonne, price(현지 통화/tCO2e), covered(tCO2e/t), free(%), rate(1유로당 현지 통화), other(유로/t) }
// fallback: covered를 비워 두었을 때 쓰는 배출량(넣은 직접배출량). 값이 모자라면 null
export function paid(carbon, fallback) {
  if (carbon.entry !== "build") {
    const euros = amount(carbon.perTonne);
    return euros === null ? null : { entry: "report", euros };
  }
  const price = amount(carbon.price);
  const rate = amount(carbon.rate);
  const covered = amount(carbon.covered) === null ? amount(fallback) : amount(carbon.covered);
  if (price === null || !rate || covered === null) return null;
  const free = Math.min(100, amount(carbon.free) || 0);
  const charged = covered * (1 - free / 100);
  const direct = (charged * price) / rate;
  const other = amount(carbon.other) || 0;
  return { entry: "build", euros: direct + other, covered, free, charged, price, rate, direct, other };
}

// 제품 1톤당 차감(인증서 수). embedded: 신고한 내재배출량(tCO2e/t), ref: 기준가격(유로). 차감을 셈할 수 없으면 null
export function deduction(carbon, embedded, ref, fallback) {
  if (!carbon || !(ref > 0)) return null;
  if (carbon.how === "paid") {
    const found = paid(carbon, fallback);
    return found ? { how: "paid", euros: found.euros, certificates: found.euros / ref, ref, detail: found } : null;
  }
  if (carbon.how === "default") {
    const dcp = amount(carbon.dcp);
    return dcp === null ? null : { how: "default", euros: dcp * embedded, certificates: (dcp * embedded) / ref, ref, dcp };
  }
  return null;
}
