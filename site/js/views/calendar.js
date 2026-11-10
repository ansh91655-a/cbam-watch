// 일정. 맨 위에 한 해를 한 줄로 그린 일정선, 그 아래에 달력. 출처에 날짜가 적혀 있는 일정만 싣는다.
import * as data from "../data.js";
import { band } from "../ui/band.js";
import { fill, h } from "../ui/dom.js";
import { koreanDate, today } from "../ui/format.js";
import { eventId, monthGrid } from "../ui/monthgrid.js";
import { yearLine } from "../ui/yearline.js";

// 달력에서 그 일정이 적힌 곳으로 옮겨 가 잠깐 표시한다.
function show(event) {
  const target = document.getElementById(eventId(event));
  if (!target) return;
  const calm = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  target.scrollIntoView({ block: "center", behavior: calm ? "auto" : "smooth" });
  target.dataset.flash = "true";
  target.focus({ preventScroll: true });
  setTimeout(() => { delete target.dataset.flash; }, 2200);
}

export async function render(main, arg) {
  const events = await data.events();
  const now = today();
  const thisYear = Number(now.slice(0, 4));
  const years = [...new Set([thisYear, ...events.map((event) => Number(String(event.date).slice(0, 4)))])].filter(Boolean).sort();
  const year = years.includes(Number(arg)) ? Number(arg) : thisYear;
  const mine = events.filter((event) => String(event.date).startsWith(`${year}-`));
  const upcoming = (event) => String(event.date) >= now.slice(0, String(event.date).length);
  const ahead = mine.filter(upcoming).length;
  // 보고 있는 해에 남은 일정이 없으면 다음 일정이 있는 해로 가는 길을 보여 준다.
  const next = events.filter(upcoming).sort((a, b) => String(a.date).localeCompare(String(b.date)))[0];
  const nextYear = next ? Number(String(next.date).slice(0, 4)) : null;

  fill(main,
    band("일정", "출처에 날짜가 적혀 있는 일정만 싣습니다. 언론 보도로만 알려진 날짜에는 '보도 기준'이라고 적었습니다. 날짜는 바뀔 수 있으니 원문에서 다시 확인하세요."),
    h("div", { class: "year-nav" }, [
      h("span", { class: "year", text: `${year}년` }),
      h("nav", { class: "chips", "aria-label": "연도" }, years.map((value) => h("a", { class: "chip", href: `#calendar-${value}`, "aria-current": value === year ? "true" : null, text: `${value}년` }))),
      h("span", { class: "count", text: `일정 ${mine.length}건${year >= thisYear ? `, 앞으로 ${ahead}건` : ""}` }),
      !ahead && next && nextYear !== year ? h("a", { class: "next-hint", href: `#calendar-${nextYear}`, text: `다음 일정은 ${koreanDate(next.date)} ${next.title}` }) : null,
    ]),
    h("section", { class: "stack", "aria-label": `${year}년 일정선` }, yearLine(events, year, now, show)),
    h("section", { class: "stack", "aria-label": `${year}년 달력` }, monthGrid(events, year, now, show)),
  );
}
