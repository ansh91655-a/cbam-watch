// 실제 배출량으로 신고할 때와 기본값으로 신고할 때를 나란히 견준다(같은 품목, 물량, 해, 인증서 가격).
// 기본값으로 신고하면 실질적으로 지불된 탄소가격은 청구할 수 없으므로, 그 차감은 실제 배출량 쪽에만 들어간다.
import { breakEven } from "../../calc/breakeven.js";
import { estimate } from "../../calc/compute.js";
import { euros, pieces, tonnes } from "../../calc/numbers.js";
import { h, table } from "../../ui/dom.js";

function verdict(gap) {
  if (Math.abs(gap) < 0.005) return "두 방법의 추정 비용이 같습니다.";
  return gap > 0 ? `실제 배출량으로 신고하면 기본값으로 신고할 때보다 ${euros(gap)}유로 적게 추정됩니다.` : `실제 배출량으로 신고하면 기본값으로 신고할 때보다 ${euros(-gap)}유로 많게 추정됩니다.`;
}

// 직접배출량이 얼마보다 낮아야 실제 배출량으로 신고하는 쪽이 유리한지(넣은 다른 값은 그대로 두고 본다)
function threshold(book, path, state) {
  const even = breakEven(book, path, state);
  if (!even) return null;
  const own = state.pre === "listed" && state.scope === "process" ? "공정의 직접배출량" : "직접배출량";
  return even.kind === "never"
    ? `이 조건에서는 ${own}이 0이어도 실제 배출량으로 신고하는 쪽의 인증서가 기본값으로 신고할 때보다 적지 않습니다.`
    : `${own}이 제품 1톤당 ${tonnes(even.direct)} tCO2e보다 낮으면 실제 배출량으로 신고하는 쪽의 인증서가 더 적게 추정됩니다.`;
}

// now: 실제 배출량으로 신고할 때의 추정. 기본값으로는 추정할 수 없으면 null
export function compare(book, path, state, now) {
  if (state.mode !== "actual") return null;
  const other = estimate(book, path, { ...state, mode: "default" });
  if (!other) return null;
  const cut = now.deduction || other.deduction;
  const lines = [
    ["내재배출량(제품 1톤당)", tonnes(other.embedded), tonnes(now.embedded)],
    ["무상할당 조정", tonnes(other.allocation), tonnes(now.allocation)],
    cut ? ["탄소가격 차감", tonnes(other.relieved), tonnes(now.relieved)] : null,
    ["인증서(제품 1톤당)", tonnes(other.perTonne), tonnes(now.perTonne)],
    ["인증서(전체)", `${pieces(other.certificates)}개`, `${pieces(now.certificates)}개`],
    ["비용(전체, 유로)", euros(other.cost), euros(now.cost)],
  ].filter(Boolean);
  const even = threshold(book, path, state);
  return h("section", { class: "calc-compare", "aria-labelledby": "h-calc-compare" }, [
    h("h3", { id: "h-calc-compare", text: "기본값으로 신고할 때와 견주기" }),
    h("p", { text: verdict(other.cost - now.cost) }),
    even ? h("p", { class: "calc-even", text: even }) : null,
    table(["항목", { text: "기본값으로 신고", num: true }, { text: "실제 배출량으로 신고", num: true }],
      lines.map(([name, base, actual]) => h("tr", {}, [h("th", { scope: "row", text: name }), h("td", { class: "num", text: base }), h("td", { class: "num", text: actual })])),
      "기본값으로 신고할 때와 실제 배출량으로 신고할 때"),
    h("p", { class: "count", text: `기본값으로 신고할 때의 내재배출량은 기본값에 ${other.year}년 마크업을 더한 값입니다.` }),
  ]);
}
