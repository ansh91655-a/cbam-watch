// 실무 달력: 법령에 날짜가 적힌 의무를 그해의 차례대로 보여 준다. 일정마다 누가 하는 일인지, 생산자가 준비할 것, 근거 조문을 붙인다.
// 역할(신고인·수입자, 제3국 사업자, 검증기관, 영국 수입자)을 골라 그 역할의 일정만 볼 수 있다(calendar/roles.js).
import { forRole, tally } from "../../calendar/roles.js";
import { fill, h, safeLink } from "../../ui/dom.js";
import { koreanDate } from "../../ui/format.js";
import { icon } from "../../ui/icons.js";
import { lawRefs } from "../../ui/lawrefs.js";

function dateBox(iso) {
  return h("span", { class: "date-box" }, [h("span", { text: `${iso.slice(0, 4)}.${Number(iso.slice(5, 7))}` }), h("b", { text: Number(iso.slice(8, 10)) })]);
}

function row(duty, todayIso, refs) {
  const link = safeLink(duty.link, duty.basis);
  if (link) link.append(icon("out", 13));
  return h("li", { class: "duty", "data-kind": duty.kind, "data-past": duty.date < todayIso ? "true" : null, id: `duty-${duty.id}`, tabindex: "-1" }, [
    dateBox(duty.date),
    h("div", { class: "duty-body" }, [
      h("p", { class: "duty-head" }, [
        h("strong", { text: duty.title }),
        h("span", { class: "pill", "data-scheme": duty.scheme, text: duty.schemeName }),
        h("span", { class: "pill", "data-tone": duty.kind === "기한" ? "due" : null, text: duty.kind }),
        duty.repeat ? h("span", { class: "pill", text: "해마다" }) : null,
      ]),
      h("p", { class: "duty-when" }, [h("time", { datetime: duty.date, text: koreanDate(duty.date) }), h("span", { text: duty.who })]),
      h("p", { class: "duty-text", text: duty.text }),
      duty.supplier ? h("p", { class: "duty-supplier" }, [h("b", { text: "생산자가 준비할 것" }), h("span", { text: duty.supplier })]) : null,
      duty.verifier ? h("p", { class: "duty-supplier" }, [h("b", { text: "검증기관이 알아 둘 것" }), h("span", { text: duty.verifier })]) : null,
      h("p", { class: "duty-basis" }, [h("span", { text: "근거" }), link || h("span", { text: duty.basis })]),
      lawRefs(refs, "국문과 함께 보기"),
    ]),
  ]);
}

// 그해의 의무 일정 구역. 그해에 의무가 없으면 null.
// role은 처음에 고를 역할(없으면 모두), onRole은 역할을 바꿀 때 부르는 함수(주소를 고친다),
// refs는 의무마다 근거 조문을 사이트의 규정 원문으로 잇는 자료({ 의무 id: [{ act, part, label }] })
export function dutyList(book, year, todayIso, role = "", onRole = () => {}, refs = {}) {
  const mine = (book.duties || []).filter((duty) => String(duty.date).startsWith(`${year}-`));
  if (!mine.length) return null;
  const roles = tally(mine, book.roles);
  const state = { role: roles.some((one) => one.key === role) ? role : "" };
  const list = h("ol", { class: "duty-list" });
  const size = h("span", { class: "count", role: "status" });
  const about = h("p", { class: "duty-role-about" });
  const none = h("p", { class: "empty", hidden: true, text: "이 해에는 이 역할의 의무 일정이 없습니다." });
  const buttons = [{ key: "", name: "전체", size: mine.length }, ...roles].map((one) => {
    const button = h("button", { class: "chip", type: "button", "aria-pressed": "false" }, [h("span", { text: one.name }), h("span", { class: "n", text: one.size })]);
    button.addEventListener("click", () => { state.role = one.key; onRole(one.key); draw(); });
    return [one.key, button];
  });

  function draw() {
    const shown = forRole(mine, state.role);
    const ahead = shown.filter((duty) => duty.date >= todayIso).length;
    fill(list, shown.map((duty) => row(duty, todayIso, refs[duty.id])));
    size.textContent = `${shown.length}건${ahead && ahead < shown.length ? `, 앞으로 ${ahead}건` : ""}`;
    about.textContent = (roles.find((one) => one.key === state.role) || {}).about || "";
    about.hidden = !about.textContent;
    none.hidden = shown.length > 0;
    for (const [key, button] of buttons) button.setAttribute("aria-pressed", String(key === state.role));
  }

  draw();
  return h("section", { class: "stack duty-sec", "aria-labelledby": "h-duty", id: "duties" }, [
    h("div", { class: "sec-head" }, [h("h3", { id: "h-duty", text: "의무 일정" }), size]),
    h("p", { class: "duty-note", text: book.note || "" }),
    roles.length > 1 ? h("div", { class: "chips duty-roles", role: "group", "aria-label": "역할로 골라 보기" }, buttons.map(([, button]) => button)) : null,
    about,
    list,
    none,
  ]);
}
