// 입법 절차 화면의 '기관'. 기관마다 한 줄 정의와 하는 일을 근거와 함께 적고, 그 기관이 CBAM 규제에서 최근에 한 일을 규제 화면으로 잇는다.
import { activity, alsoCalled } from "../../procedure/model.js";
import { cites } from "../../procedure/parts.js";
import { h, unsplit } from "../../ui/dom.js";
import { koreanDate } from "../../ui/format.js";

// 그 기관이 맡은 단계에서 일어난 일(규제의 연혁에서 고른다). 없으면 싣지 않는다.
function seen(book, rules, one) {
  const rows = activity(book, rules, one.key, 3);
  if (!rows.length) return null;
  return h("div", { class: "who-seen" }, [
    h("strong", { text: "CBAM 규제에서 최근에 한 일" }),
    h("ul", {}, rows.map(({ rule, step, event }) => h("li", {}, [
      h("time", { datetime: event.date, text: koreanDate(event.date) || event.date }),
      h("a", { href: `#rules-${rule.id}` }, unsplit(rule.name)),
      h("span", { text: step.name }),
    ]))),
  ]);
}

function card(book, rules, one) {
  return h("article", { class: "who-card", id: `pr-who-${one.key}`, tabindex: "-1", "data-who": one.key }, [
    h("header", {}, [
      h("h3", { text: one.name }),
      h("p", { class: "who-en" }, [h("span", { lang: "en", text: one.en }), one.aka ? h("span", { text: alsoCalled(one.aka) }) : null]),
    ]),
    h("p", { class: "who-role", text: one.role }),
    h("ul", { class: "who-points" }, one.points.map((point) => h("li", {}, [h("p", { text: point.text }), cites(book, point.basis)]))),
    seen(book, rules, one),
  ]);
}

export function who(book, rules) {
  return h("section", { class: "stack proc-sec", id: "pr-who", tabindex: "-1", "aria-labelledby": "h-pr-who" }, [
    h("div", { class: "sec-head" }, [h("h2", { id: "h-pr-who", text: "기관: 누가 무엇을 하는지" }), h("span", { class: "count", text: `${book.institutions.length}곳` })]),
    h("p", { class: "sec-lead", text: "법이 만들어지는 과정에 나오는 기관들입니다. 문단마다 근거가 된 조약과 법령의 조문을 달았습니다." }),
    h("div", { class: "who-grid" }, book.institutions.map((one) => card(book, rules, one))),
  ]);
}
