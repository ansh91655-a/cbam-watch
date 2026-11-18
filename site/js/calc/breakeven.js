// 기본값으로 신고할 때와 인증서 수가 같아지는 직접배출량. 넣은 다른 값(간접배출량, 전구물질, 탄소가격)은 그대로 두고 직접배출량만 바꾸어 찾는다.
// 화면 요소를 다루지 않는다(tests/test_calc_detail.py가 node로 돌린다).
import { estimate } from "./compute.js";

const STEPS = 60;  // 반씩 좁혀 가는 횟수(소수점 아래 열 자리보다 촘촘해진다)

// 돌려주는 것:
//   { kind: "below", direct }  직접배출량이 direct보다 낮으면 실제 배출량으로 신고하는 쪽의 인증서가 적다
//   { kind: "never" }          직접배출량이 0이어도 실제 배출량으로 신고하는 쪽이 적지 않다(전구물질이나 간접배출량의 몫이 이미 크다)
//   null                       견줄 수 없다(기본값으로 신고해도 인증서가 없거나, 직접배출량이 늘어도 인증서가 늘지 않는 조건)
export function breakEven(book, path, input) {
  const base = estimate(book, path, { ...input, mode: "default" });
  if (!base || !(base.perTonne > 0)) return null;
  const at = (direct) => estimate(book, path, { ...input, mode: "actual", direct });
  const none = at(0);
  if (!none) return null;
  if (none.perTonne >= base.perTonne) return { kind: "never" };
  let low = 0;
  let high = Math.max(1, base.embedded * 4);
  if (at(high).perTonne < base.perTonne) return null;
  for (let step = 0; step < STEPS; step += 1) {
    const mid = (low + high) / 2;
    if (at(mid).perTonne < base.perTonne) low = mid; else high = mid;
  }
  return { kind: "below", direct: (low + high) / 2 };
}
