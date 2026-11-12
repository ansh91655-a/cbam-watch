// 실무 달력: 법령에 날짜가 적힌 의무를 그해의 차례대로 보여 준다. 일정마다 누가 하는 일인지, 생산자가 준비할 것, 근거 조문을 붙인다.
import { h, safeLink } from "../../ui/dom.js";
import { koreanDate } from "../../ui/format.js";
import { icon } from "../../ui/icons.js";

function dateBox(iso) {
  return h("span", { class: "date-box" }, [h("span", { text: `${iso.slice(0, 4)}.${Number(iso.slice(5, 7))}` }), h("b", { text: Number(iso.slice(8, 10)) })]);
}

function row(duty, todayIso) {
  const link = safeLink(duty.link, duty.basis);
  if (link) link.append(icon("out", 13));
  return h("li", { class: "duty", "data-kind": duty.kind, "data-past": duty.date < todayIso ? "true" : null, id: `duty-${duty.id}`, tabindex: "-1" }, [
    dateBox(duty.date),
    h("div", { class: "duty-body" }, [
      h("p", { class: "duty-head" }, [
        h("strong", { text: duty.title }),
        h("span", { class: "pill", "data-scheme": duty.scheme, text: duty.schemeName }),
        h("span", { class: "pill", "data-tone": duty.kind === "기한" ? "due" : null, text: duty.kind }),
      ]),
      h("p", { class: "duty-when" }, [h("time", { datetime: duty.date, text: koreanDate(duty.date) }), h("span", { text: duty.who })]),
      h("p", { class: "duty-text", text: duty.text }),
      duty.supplier ? h("p", { class: "duty-supplier" }, [h("b", { text: "생산자가 준비할 것" }), h("span", { text: duty.supplier })]) : null,
      h("p", { class: "duty-basis" }, [h("span", { text: "근거" }), link || h("span", { text: duty.basis })]),
    ]),
  ]);
}

// 그해의 의무 일정 구역. 그해에 의무가 없으면 null.
export function dutyList(book, year, todayIso) {
  const mine = (book.duties || []).filter((duty) => String(duty.date).startsWith(`${year}-`));
  if (!mine.length) return null;
  const ahead = mine.filter((duty) => duty.date >= todayIso).length;
  return h("section", { class: "stack duty-sec", "aria-labelledby": "h-duty" }, [
    h("div", { class: "sec-head" }, [h("h3", { id: "h-duty", text: "의무 일정" }), h("span", { class: "count", text: `${mine.length}건${ahead && ahead < mine.length ? `, 앞으로 ${ahead}건` : ""}` })]),
    h("p", { class: "duty-note", text: book.note || "" }),
    h("ol", { class: "duty-list" }, mine.map((duty) => row(duty, todayIso))),
  ]);
}
