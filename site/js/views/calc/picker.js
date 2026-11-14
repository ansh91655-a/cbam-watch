// 품목 고르기. CN 코드나 영문 품목 이름으로 찾아 하나를 고른다. 품목 이름은 법령의 표에 적힌 영문 그대로다.
import { search } from "../../calc/compute.js";
import { h } from "../../ui/dom.js";
import { icon } from "../../ui/icons.js";

export const SECTOR = { cement: "시멘트", fertilisers: "비료", steel: "철강", aluminium: "알루미늄", hydrogen: "수소" };
const SECTOR_ICON = { cement: "cement", fertilisers: "fertilisers", steel: "steel", aluminium: "aluminium", hydrogen: "hydrogen" };
const EXAMPLES = ["72081000", "72104900", "73063077", "76061292", "25232900", "31021019"];
const LIMIT = 8;

export function spaced(code) {
  return String(code).replace(/^(\d{4})(\d{2})(\d{2})$/, "$1 $2 $3");
}

function goodLine(good) {
  return [
    h("span", { class: "cn-code", text: spaced(good.code) }),
    h("span", { class: "calc-good-text", lang: "en", text: good.text }),
    h("span", { class: "pill", text: SECTOR[good.sector] || good.sector }),
  ];
}

// 고른 품목을 보여 주는 칸. '다른 품목 고르기'를 누르면 onPick(null)을 부른다.
function chosenCard(good, onPick) {
  return h("div", { class: "calc-chosen" }, [
    h("span", { class: "chipicon" }, icon(SECTOR_ICON[good.sector] || "file", 20)),
    h("div", { class: "calc-chosen-body" }, [
      h("p", {}, [h("span", { class: "cn-code", text: spaced(good.code) }), h("span", { class: "pill", text: SECTOR[good.sector] || good.sector })]),
      h("p", { class: "calc-good-text", lang: "en", text: good.text }),
      // 그 품목의 대상 여부, 기본값과 벤치마크, 일정, 근거 조문을 모은 화면으로
      h("p", { class: "calc-chosen-more" }, h("a", { href: `#cn-${good.code}`, text: "이 품목 한 장 보기" })),
    ]),
    h("button", { type: "button", class: "btn calc-change", onclick: () => onPick(null), text: "다른 품목 고르기" }),
  ]);
}

// goods: 품목 목록, chosen: 고른 품목(없으면 찾는 칸을 보여 준다), onPick(품목 또는 null), typed: 찾는 칸에 미리 넣어 둘 글
export function picker(goods, chosen, onPick, typed = "") {
  if (chosen) return chosenCard(chosen, onPick);
  const list = h("ul", { class: "calc-hits" });
  const status = h("p", { class: "count", "aria-live": "polite" });
  const input = h("input", { id: "calc-q", type: "search", autocomplete: "off", placeholder: "예: 7208 10 00 또는 hot-rolled", value: typed || null });
  const show = () => {
    const hits = search(goods, input.value, LIMIT + 1);
    const asked = input.value.trim();
    list.replaceChildren(...hits.slice(0, LIMIT).map((good) => h("li", {}, h("button", { type: "button", class: "calc-hit", onclick: () => onPick(good) }, goodLine(good)))));
    status.textContent = !asked ? "" : !hits.length ? "맞는 품목이 없습니다. CN 코드의 앞 4자리부터 넣어 보세요." : hits.length > LIMIT ? `${LIMIT}개까지 보여 드립니다. 더 길게 넣으면 좁혀집니다.` : `${hits.length}개를 찾았습니다.`;
  };
  input.addEventListener("input", show);
  if (typed) show();
  const known = EXAMPLES.map((code) => goods.find((good) => good.code === code)).filter(Boolean);
  return h("div", { class: "calc-picker" }, [
    h("form", { class: "calc-search", role: "search", onsubmit: (event) => { event.preventDefault(); const first = search(goods, input.value, 1)[0]; if (first) onPick(first); } }, [
      h("label", { class: "field", for: "calc-q" }, [h("span", { text: "품목(CN 코드 8자리나 영문 품목 이름)" }), input]),
    ]),
    h("p", { class: "cn-examples" }, [h("span", { text: "예시" }), ...known.map((good) => h("button", { type: "button", class: "pill", text: spaced(good.code), title: good.text, onclick: () => onPick(good) }))]),
    status,
    list,
  ]);
}
