// 일정. 원문에서 날짜가 확인된 것만 싣는다.
import * as data from "../data.js";
import { empty, h, safeLink, table, viewHead } from "../ui/dom.js";

function rows(events) {
  return events.map((event) => h("tr", {}, [
    h("td", { class: "num", text: event.date }),
    h("td", {}, [h("span", { text: event.title }), event.note ? h("p", { class: "count", text: event.note }) : null]),
    h("td", {}, safeLink(event.link, event.sourceName || "원문") || h("span", { text: event.sourceName || "" })),
  ]));
}

export async function render(main) {
  const events = await data.events();
  const today = new Date(Date.now() + 9 * 3600000).toISOString().slice(0, 10);
  const upcoming = events.filter((event) => String(event.date) >= today).sort((a, b) => String(a.date).localeCompare(String(b.date)));
  const past = events.filter((event) => String(event.date) < today).sort((a, b) => String(b.date).localeCompare(String(a.date))).slice(0, 30);
  const headers = ["날짜", "내용", "출처"];
  main.replaceChildren(
    viewHead("일정", "출처 화면에 날짜가 적혀 있는 일정만 싣습니다. 날짜는 바뀔 수 있으니 원문에서 다시 확인하세요."),
    h("section", { class: "stack" }, [h("h2", { text: "다가오는 일정" }), upcoming.length ? table(headers, rows(upcoming)) : empty("등록된 예정 일정이 없습니다.")]),
    past.length ? h("section", { class: "stack" }, [h("h2", { text: "지난 일정" }), table(headers, rows(past))]) : null,
  );
}
