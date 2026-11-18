// 계산 내역: 내재배출량, 무상할당 조정, 탄소가격 차감, 인증서 대상이 어떻게 나왔는지 차례로 적는다.
// 값마다 한 줄의 풀이를 달고, 전구물질이나 탄소가격처럼 여러 값으로 이루어진 것은 그 아래에 줄을 나누어 적는다.
import { fixed, percent, tonnes } from "../../calc/numbers.js";
import { h } from "../../ui/dom.js";
import { spaced } from "./picker.js";

const routeName = (book, key) => (book.routes.find((route) => route.key === key) || { name: key }).name;
const originName = (row) => (row.origin === "kr" ? "대한민국 기본값" : "'그 밖의 나라와 영역' 기본값");

// 벤치마크를 어느 생산경로의 값으로 골랐는지. 경로를 가르지 않으면 빈 글.
function routeNote(book, now, column) {
  if (!now.route || !column.some((one) => one.route)) return "";
  if (now.routeAlt) return ` 벤치마크는 두 생산경로('${routeName(book, now.route)}', '${routeName(book, now.routeAlt)}')의 값 가운데 큰 값입니다.`;
  return ` 벤치마크는 생산경로 '${routeName(book, now.route)}'의 값입니다.`;
}

function embedded(now, state, row) {
  if (now.mode !== "actual") return { how: `${originName(row)} ${tonnes(row.total)}에 ${now.year}년 마크업 ${percent(now.markup)}를 더한 값입니다.`, lines: [] };
  const { direct, indirect, inputs } = now.parts;
  const counts = row.indirect !== null;  // 간접배출량도 세는 품목인지
  if (state.pre === "listed" && state.scope === "process") {
    const own = counts ? `공정의 직접배출량(${tonnes(direct)})과 간접배출량(${tonnes(indirect)})` : `공정의 직접배출량(${tonnes(direct)})`;
    return {
      how: now.lines.length ? `${own}에 전구물질의 몫(${tonnes(inputs)})을 더한 값입니다.` : `${own}입니다. 전구물질을 아직 넣지 않아 그 몫은 더하지 않았습니다.`,
      lines: now.lines.map((line) => {
        const from = line.see.given ? "넣으신 값" : `${originName(line.row)} ${tonnes(line.see.total)} + 마크업 ${percent(line.see.markup)}`;
        return `${spaced(line.good.code)} · ${tonnes(line.mass)}톤 × ${tonnes(line.see.value)}(${from}) = ${tonnes(line.embedded)}`;
      }),
    };
  }
  return { how: counts ? `넣으신 직접배출량(${tonnes(direct)})과 간접배출량(${tonnes(indirect)})을 더한 값입니다.` : "넣으신 직접배출량입니다.", lines: [] };
}

function allocation(book, now, state) {
  const share = `CBAM 계수 ${percent(now.factor)} × 부문 간 보정계수 ${percent(now.cscf)}`;
  if (now.column === "B") {
    const rough = now.rough ? " 전구물질을 따로 넣지 않아, 전구물질의 몫까지 넣어 둔 기본 벤치마크(B열)로 어림한 값입니다." : "";
    return { how: `CBAM 벤치마크 ${tonnes(now.benchmark)} × ${share}.${routeNote(book, now, state.good.b)}${rough}`, lines: [] };
  }
  const own = `공정 벤치마크(A열) ${tonnes(now.benchmark)} × ${share} = ${tonnes(now.process)}`;
  return {
    how: (now.lines.length ? `${own}, 여기에 전구물질의 몫(${tonnes(now.inputAllocation)})을 더한 값입니다.` : `${own}. 전구물질을 아직 넣지 않아 공정의 몫만 계산했습니다.`) + routeNote(book, now, state.good.a),
    lines: now.lines.map((line) => {
      const route = line.sefa.route ? `, ${routeName(book, line.sefa.route)}${line.sefa.routeAlt ? `와 ${routeName(book, line.sefa.routeAlt)} 가운데 큰 값` : ""}` : "";
      const from = line.sefa.given ? (line.sefa.scaled ? `넣으신 값을 ${now.year}년의 CBAM 계수에 맞춘 값` : "넣으신 값")
        : `B열 벤치마크 ${tonnes(line.sefa.benchmark)}${route} × ${percent(now.factor)} × ${percent(now.cscf)}`;
      return `${spaced(line.good.code)} · ${tonnes(line.mass)}톤 × ${tonnes(line.sefa.value)}(${from}) = ${tonnes(line.allocation)}`;
    }),
  };
}

// 기준가격이 어디에서 온 값인지
function referenceNote(now, cut) {
  if (cut.refFrom === "given") return "기준가격은 넣으신 값입니다.";
  if (cut.refFrom === "year") return `기준가격은 ${now.year}년의 것으로 공개된 인증서 가격 ${cut.refCount}개의 평균입니다.`;
  if (cut.refFrom === "partial") return `기준가격은 ${now.year}년의 인증서 가격 가운데 지금까지 공개된 ${cut.refCount}개의 평균입니다. 남은 가격이 공개되면 달라집니다.`;
  return `${now.year}년의 인증서 가격이 아직 공개되지 않아, 넣으신 인증서 가격을 기준가격으로 썼습니다.`;
}

function relief(now) {
  const cut = now.deduction;
  const ref = `기준가격 ${fixed(cut.ref, 2)}유로`;
  const lines = [];
  let how;
  if (cut.how === "default") {
    const declared = now.mode === "actual" ? "신고한 내재배출량" : "신고한 내재배출량(마크업을 더한 값)";
    how = `기본 탄소가격 ${fixed(cut.dcp, 2)}유로 × ${declared} ${tonnes(now.embedded)} ÷ ${ref}.`;
  } else {
    how = `제품 1톤당 실질 지불 탄소가격 ${fixed(cut.euros, 2)}유로 ÷ ${ref}.`;
    const detail = cut.detail;
    if (detail.entry === "build") {
      lines.push(`값을 치른 배출량: ${tonnes(detail.covered)} × (100% − ${percent(detail.free)}) = ${tonnes(detail.charged)} tCO2e`);
      lines.push(`유로로 바꾼 값: ${tonnes(detail.charged)} × 탄소가격 ${fixed(detail.price, 0)} ÷ 환율 ${fixed(detail.rate, 2)} = ${fixed(detail.direct, 2)}유로`);
      if (detail.other) lines.push(`그 밖의 몫(간접배출량이나 전구물질): ${fixed(detail.other, 2)}유로`);
    }
  }
  if (now.relieved < cut.certificates - 1e-9) how += " 남은 인증서 대상보다 커서 남은 만큼만 뺐습니다.";
  lines.push(referenceNote(now, cut));
  return { how, lines };
}

function left(now) {
  if (now.perTonne > 0) return now.deduction ? "내재배출량에서 무상할당 조정과 탄소가격 차감분을 뺀 값입니다." : "내재배출량에서 무상할당 조정을 뺀 값입니다.";
  if (now.allocation >= now.embedded) return "무상할당 조정이 내재배출량보다 커서 0으로 보았습니다.";
  return "무상할당 조정과 탄소가격 차감분을 빼면 남는 것이 없어 0으로 보았습니다.";
}

// now: 추정 결과(calc/compute.js의 estimate), state: 넣은 조건, row: 고른 기본값 행
export function steps(book, now, state, row) {
  const found = [
    ["내재배출량", `${tonnes(now.embedded)} tCO2e`, embedded(now, state, row)],
    ["무상할당 조정", `${tonnes(now.allocation)} tCO2e`, allocation(book, now, state)],
    now.deduction ? ["탄소가격 차감", `${tonnes(now.relieved)} tCO2e`, relief(now)] : null,
    ["인증서 대상", `${tonnes(now.perTonne)} tCO2e`, { how: left(now), lines: [] }],
  ].filter(Boolean);
  return h("dl", { class: "calc-steps" }, found.flatMap(([name, value, text]) => [
    h("dt", { text: name }),
    h("dd", {}, [h("b", { text: value }), h("span", { text: text.how }), text.lines.length ? h("ul", { class: "calc-lines" }, text.lines.map((line) => h("li", { text: line }))) : null]),
  ]));
}
