// 규제 화면 왼쪽의 고르기: 전체, 묶음들, 그리고 따로 떨어뜨려 놓은 '최근 변화'(연혁을 합쳐 최근에 달라진 것만 보는 화면).
import { hrefOf, RECENT } from "../../rules/changes.js";
import { h } from "../../ui/dom.js";
import { icon } from "../../ui/icons.js";

function link(href, on, picture, name, size, apart = false) {
  return h("a", { href, class: apart ? "side-apart" : null, "aria-current": on ? "true" : null },
    [h("span", { class: "chipicon" }, icon(picture, 17)), h("span", { text: name }), h("span", { class: "n", text: size })]);
}

// picked: 고른 묶음의 이름, 전체면 "", 최근 변화면 RECENT. recent: 최근 변화의 건수(기본 날수)
export function sideNav(rules, groups, picked, recent) {
  return h("nav", { class: "side-nav", "aria-label": "규제 묶음" }, [
    link("#rules", !picked, "law", "전체", rules.length),
    ...groups.map((group) => link(`#rules-${group.code}`, picked === group.code, group.icon || "legis", group.name, rules.filter((rule) => rule.group === group.code).length)),
    link(hrefOf(), picked === RECENT, "clock", "최근 변화", recent, true),
  ]);
}
