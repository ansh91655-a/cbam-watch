// 준비 목록 맨 위의 '다가오는 날짜': 그 역할의 항목 가운데 날짜가 가까운 것 몇 개를 날짜순으로 보여 주고, 누르면 그 항목으로 옮겨 간다.
import { h } from "../../ui/dom.js";
import { countdown, koreanDate } from "../../ui/format.js";

function card(row, onPick, hrefOf) {
  const duty = row.duty;
  // 주소는 그 항목을 가리키는 화면 주소다(새 탭으로 열어도 그 항목으로 간다)
  const link = h("a", { class: "prep-soon-card", href: hrefOf(row.id), "data-tone": duty.kind === "기한" ? "due" : null }, [
    h("span", { class: "prep-soon-when" }, [h("time", { datetime: duty.date, text: koreanDate(duty.date) }), h("b", { text: countdown(duty.date) })]),
    h("span", { class: "prep-soon-title", text: row.title }),
    h("span", { class: "prep-soon-kind", text: duty.repeat ? `${duty.kind} · 해마다` : duty.kind }),
  ]);
  // 그냥 누르면 주소는 바꾸지 않고(바꾸면 화면을 다시 그린다) 그 항목으로 옮겨 가기만 한다. 새 탭으로 여는 누름은 브라우저에 맡긴다
  link.addEventListener("click", (event) => {
    if (event.button || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    onPick(row.id);
  });
  return h("li", {}, link);
}

// rows는 다가오는 날짜가 있는 항목(plan.js의 upcoming). 없으면 null. hrefOf(항목 id)는 그 항목을 가리키는 주소를 돌려준다.
export function soon(rows, onPick, hrefOf) {
  if (!rows.length) return null;
  return h("section", { class: "prep-soon", "aria-labelledby": "h-prep-soon" }, [
    h("h2", { id: "h-prep-soon", text: "다가오는 날짜" }),
    h("ol", { class: "prep-soon-list" }, rows.map((row) => card(row, onPick, hrefOf))),
  ]);
}
