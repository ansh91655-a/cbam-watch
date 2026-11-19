// 없는 주소로 왔을 때의 안내. 주소가 바뀌었거나 잘못 적힌 것이므로, 찾으려던 화면을 어림해 보여 주고(js/nav/guess.js) 검색과 모든 화면으로 가는 길을 둔다.
// 화면의 이름이 아닌 주소가 이 화면으로 온다(js/router.js). 값으로 주소의 글이 그대로 넘어온다.
import { guess } from "../nav/guess.js";
import { allScreens } from "../nav/map.js";
import { visit } from "../router.js";
import { band } from "../ui/band.js";
import { fill, h } from "../ui/dom.js";
import { icon } from "../ui/icons.js";
import { target } from "../ui/sitesearch.js";

export const TITLE = "찾는 화면이 없습니다";

function tiles(screens, few = false) {
  return h("div", { class: few ? "steps steps-few" : "steps" }, screens.map((one) => h("a", { class: "step", href: one.href }, [
    h("span", { class: "chipicon" }, icon(one.icon, 22)),
    h("h3", { text: one.title }),
    h("p", { text: one.detail || one.about }),
  ])));
}

export async function render(main, arg) {
  const guessed = guess(arg);
  const rest = allScreens().filter((one) => !guessed.some((other) => other.view === one.view));
  const input = h("input", { id: "missing-q", type: "search", placeholder: "찾는 말을 적어 주세요. 예: 기본값, 검증기관 인정, 7208", autocomplete: "off", spellcheck: "false", enterkeyhint: "search" });
  fill(main,
    band(TITLE, "주소가 바뀌었거나 잘못 적힌 주소입니다. 아래에서 다시 찾아 주세요."),
    guessed.length ? h("section", { class: "stack", "aria-labelledby": "h-guess" }, [h("h2", { id: "h-guess", text: "이 주소와 비슷한 화면" }), tiles(guessed, true)]) : null,
    h("section", { class: "stack", "aria-labelledby": "h-missing-search" }, [
      h("h2", { id: "h-missing-search", text: "사이트에서 찾기" }),
      h("form", { class: "law-search", role: "search", "aria-label": "사이트에서 찾기", onsubmit: (event) => { event.preventDefault(); if (input.value.trim()) visit(target(input.value)); } }, [
        h("label", { class: "sr", for: "missing-q", text: "찾는 말" }), icon("search", 20), input, h("button", { class: "btn btn-main", type: "submit", text: "찾기" })]),
    ]),
    h("section", { class: "stack", "aria-labelledby": "h-all" }, [h("h2", { id: "h-all", text: guessed.length ? "다른 화면" : "모든 화면" }), tiles(rest)]),
  );
  return TITLE;
}
