// 탄소가격 차감을 넣는 칸. 제품을 만든 나라에서 낸 탄소가격만큼 제출할 인증서 수를 줄인다(셈은 calc/carbon.js).
// 실제 배출량으로 신고하면 실질적으로 지불된 탄소가격(인증보고서의 값이나 넣은 값으로 계산한 값)이나 기본 탄소가격으로,
// 기본값으로 신고하면 기본 탄소가격으로만 청구할 수 있다.
import { referencePrice } from "../../calc/carbon.js";
import { fixed } from "../../calc/numbers.js";
import { h } from "../../ui/dom.js";
import { field, group, numberInput, row, seg } from "./fields.js";

const ENTRY = [["report", "인증보고서의 값"], ["build", "계산해 보기"]];

// 기준가격 칸의 도움말: 비워 두면 어떤 값을 쓰는지
function referenceHint(state) {
  const known = referencePrice(state.prices, state.year);
  if (!known) return `${state.year}년의 인증서 가격이 아직 공개되지 않아, 비워 두면 위에 넣은 인증서 가격을 씁니다.`;
  const mean = `${fixed(known.value, 2)}유로`;
  return known.partial
    ? `비워 두면 ${state.year}년의 인증서 가격 가운데 지금까지 공개된 ${known.count}개의 평균 ${mean}를 씁니다.`
    : `비워 두면 ${state.year}년의 것으로 공개된 인증서 가격의 평균 ${mean}를 씁니다.`;
}

// ctx: { state, show(결과만 다시 그린다), draw(칸들을 다시 그린다) }
export function carbonFields(ctx) {
  const { state, show, draw } = ctx;
  const carbon = state.carbon;
  const actual = state.mode === "actual";
  const set = (key) => (value) => { carbon[key] = value; show(); };
  const known = referencePrice(state.prices, state.year);
  const options = [["none", "넣지 않음"], actual ? ["paid", "실질적으로 지불된 탄소가격"] : null, ["default", "기본 탄소가격"]].filter(Boolean);
  const paid = carbon.how === "paid" && actual;
  return group("h-calc-carbon", "탄소가격 차감", [
    h("p", { class: "count", text: actual
      ? "제품을 만든 나라에서 낸 탄소가격이 있으면 그만큼 제출할 인증서 수가 줄어듭니다."
      : "제품을 만든 나라에서 낸 탄소가격이 있으면 그만큼 제출할 인증서 수가 줄어듭니다. 기본값으로 신고할 때에는 기본 탄소가격으로만 청구할 수 있습니다." }),
    seg("carbon", "탄소가격 차감", options, carbon.how, (how) => { carbon.how = how; draw(`[data-seg="carbon:${how}"]`); }),
    paid ? row("넣는 방법", seg("entry", "실질적으로 지불된 탄소가격을 넣는 방법", ENTRY, carbon.entry, (entry) => { carbon.entry = entry; draw(`[data-seg="entry:${entry}"]`); })) : null,
    paid && carbon.entry === "report" ? h("div", { class: "calc-grid" }, [
      field("calc-cp-euros", "제품 1톤당 실질 지불 탄소가격(유로)", numberInput("calc-cp-euros", carbon.perTonne, set("perTonne")),
        "독립적인 사람이 인증한 보고서에 적힌 값입니다. 무상으로 받은 배출권이나 환급처럼 값을 치르지 않은 몫은 빠져 있어야 합니다."),
    ]) : null,
    paid && carbon.entry === "build" ? h("div", { class: "calc-grid" }, [
      field("calc-cp-price", "탄소가격(원, tCO2e당)", numberInput("calc-cp-price", carbon.price, set("price")),
        "배출권거래제이면 보고 기간의 배출권 경매 낙찰가를 가중평균한 값입니다. 다른 통화이면 그 통화로 넣습니다."),
      field("calc-cp-rate", "환율(1유로당 원)", numberInput("calc-cp-rate", carbon.rate, set("rate")),
        "법령은 집행위원회가 공개하는 연평균 환율을 쓰도록 정하고 있습니다."),
      field("calc-cp-covered", "탄소가격이 매겨진 직접배출량(tCO2e/t)", numberInput("calc-cp-covered", carbon.covered, set("covered"), { placeholder: "위의 직접배출량" }),
        "사업장에서 나온 배출량 가운데 제품 1톤의 몫입니다. 비워 두면 위에 넣은 직접배출량을 씁니다."),
      field("calc-cp-free", "값을 치르지 않은 몫(%)", numberInput("calc-cp-free", carbon.free, set("free"), { max: "100", placeholder: "예: 90" }),
        "무상으로 받은 배출권처럼 탄소가격을 내지 않은 배출량의 비율입니다."),
      field("calc-cp-other", "그 밖에 더할 값(유로, 제품 1톤당)", numberInput("calc-cp-other", carbon.other, set("other")),
        "간접배출량이나 전구물질에 치러진 탄소가격이 있으면 넣습니다."),
    ]) : null,
    carbon.how === "default" ? h("div", { class: "calc-grid" }, [
      field("calc-cp-dcp", "기본 탄소가격(유로, tCO2e당)", numberInput("calc-cp-dcp", carbon.dcp, set("dcp")),
        "EU 집행위원회가 나라마다 정해 CBAM 등록부에 올리는 값입니다. 법령은 2027년부터 정해 올릴 수 있다고 적고 있습니다."),
    ]) : null,
    paid || carbon.how === "default" ? h("div", { class: "calc-grid" }, [
      field("calc-cp-ref", "기준가격(유로)", numberInput("calc-cp-ref", carbon.ref, set("ref"), { placeholder: known ? fixed(known.value, 2) : null }), referenceHint(state)),
    ]) : null,
  ]);
}
