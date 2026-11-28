// 입법 절차 화면과 규제 화면의 '세부 절차'가 함께 쓰는 작은 조각들: 하는 기관의 표시, 근거 자료의 줄, 작은 진행 표시.
import { h, safeLink } from "../ui/dom.js";
import { day } from "../ui/format.js";
import { icon } from "../ui/icons.js";
import { STATES } from "./model.js";

// 그 단계를 하는 곳. 기관은 입법 절차 화면의 그 기관 풀이로 이어지고, 기관 목록에 없는 곳(by)은 글로만 적는다.
export function whoChips(book, step) {
  const names = new Map((book.institutions || []).map((one) => [one.key, one.name]));
  const chips = (step.who || []).filter((key) => names.has(key)).map((key) =>
    h("a", { class: "who-chip", href: `#procedure-who.${key}`, "data-who": key, text: names.get(key) }));
  if (step.by) chips.push(h("span", { class: "who-chip plain", text: step.by }));
  return chips.length ? h("span", { class: "who-chips" }, chips) : null;
}

// 근거 자료의 줄. 받아 둔 조문과 법령은 이름만, 기관의 안내 화면은 확인한 날을 함께 적는다. 이 사이트에 실린 법령이면 그 조문으로도 잇는다.
export function cites(book, names) {
  const links = (names || []).map((name) => {
    const source = (book.sources || {})[name];
    const link = source ? safeLink(source.url, source.text) : null;
    if (!link) return null;
    link.append(icon("out", 12));
    return h("li", {}, [
      link,
      source.checkedOn ? h("span", { class: "cite-seen", text: `${day(source.checkedOn)} 확인` }) : null,
      source.read ? h("a", { class: "cite-read", href: source.read, text: "이 사이트에서 읽기" }) : null,
    ]);
  }).filter(Boolean);
  return links.length ? h("div", { class: "cite-line" }, [h("span", { class: "cite-label", text: "근거" }), h("ul", {}, links)]) : null;
}

// 작은 진행 표시: 꼭 있는 단계마다 점 하나. 상태는 글로도 읽힌다(aria-label).
export function dotTrack(points, label) {
  return h("span", { class: "ps-track", role: "img", "aria-label": label },
    points.map((point) => h("span", { class: "ps-pt", "data-state": point.state, title: `${point.name}: ${STATES[point.state] || ""}` })));
}

// 상태를 적은 작은 표시
export function stateMark(state) {
  return h("span", { class: "ps-state", "data-state": state, text: STATES[state] || "" });
}
