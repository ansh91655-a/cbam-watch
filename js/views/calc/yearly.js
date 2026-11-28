// 연도별 추정의 표. 같은 품목과 인증서 가격으로 해마다 셈한 값을 적는다. 결과(비용, 인증서)를 앞에 두고 그 값을 이루는 것들을 뒤에 둔다.
import { series } from "../../calc/compute.js";
import { euros, fixed, percent, tonnes } from "../../calc/numbers.js";
import { h, pill, table } from "../../ui/dom.js";

// 넣은 값을 다른 해에 어떻게 썼는지(실제 배출량이나 탄소가격을 넣었을 때만)
function carried(state, rows) {
  const notes = [];
  if (state.mode === "actual") notes.push("넣으신 배출량은 해마다 그대로 썼습니다.");
  if (rows.some((row) => row.lines.some((line) => !line.see.given)) && state.scope === "process") notes.push("전구물질의 기본값에는 그해의 마크업을 더했습니다.");
  if (rows.some((row) => row.lines.some((line) => line.sefa.scaled))) notes.push("넣으신 전구물질의 무상할당은 그해의 CBAM 계수에 맞추어 다시 계산했습니다.");
  if (rows.some((row) => row.deduction)) notes.push("탄소가격은 넣으신 값을 해마다 그대로 썼고, 기준가격은 인증서 가격이 공개되지 않은 해에는 넣으신 인증서 가격을 썼습니다.");
  return notes.join(" ");
}

// path: CBAM 계수의 경로, state: 넣은 조건. 돌려주는 것: [표 위의 설명 글, 표]
export function yearly(book, path, state) {
  const rows = series(book, path, state);
  const top = Math.max(...rows.map((row) => row.costPerTonne), 0.0001);
  const cut = rows.some((row) => row.deduction);
  const headers = ["수입 연도", { text: "비용(톤당, 유로)", num: true }, { text: "인증서(톤당)", num: true }, { text: "내재배출량", num: true }, { text: "CBAM 계수", num: true },
    { text: "무상할당 조정", num: true }, cut ? { text: "탄소가격 차감", num: true } : null].filter(Boolean);
  const grid = table(headers, rows.map((row) => h("tr", { class: row.year === state.year ? "calc-now" : null }, [
    h("td", {}, [h("span", { text: `${row.year}년` }), row.assumed.benchmark || row.assumed.cscf ? pill("가정 포함", "warn") : null]),
    h("td", { class: "num calc-cost" }, [h("span", { class: "calc-mini", "aria-hidden": "true", style: `--share:${(row.costPerTonne / top).toFixed(3)}` }), h("b", { text: euros(row.costPerTonne) })]),
    h("td", { class: "num", text: tonnes(row.perTonne) }),
    h("td", { class: "num", text: tonnes(row.embedded) }),
    h("td", { class: "num", text: percent(row.factor) }),
    h("td", { class: "num", text: tonnes(row.allocation) }),
    cut ? h("td", { class: "num", text: tonnes(row.relieved) }) : null,
  ])), "연도별 추정");
  const lead = `같은 품목과 인증서 가격(${fixed(state.price || 0, 2)}유로)으로 해마다 계산한 값입니다. CBAM 계수는 '${path.name}'의 값을 썼습니다.`;
  return [h("p", { class: "sub calc-sub", text: [lead, carried(state, rows)].filter(Boolean).join(" ") }), grid];
}
