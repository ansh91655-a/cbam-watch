// 달력. 열두 달을 달력 모양으로 놓고, 일정이 있는 날을 표시하고, 달마다 그 달의 일정을 아래에 적는다.
import { h, safeLink } from "./dom.js";
import { countdown, daysUntil, koreanDate } from "./format.js";

const WEEKDAYS = ["일", "월", "화", "수", "목", "금", "토"];
const WEIGHT = { "기한": 3, "시행": 2, "행사": 1, "가격": 0 };

export function eventId(event) {
  return `ev-${String(event.date)}-${Math.abs([...String(event.title)].reduce((sum, char) => (sum * 31 + char.codePointAt(0)) % 1000003, 7))}`;
}

function eventRow(event) {
  const monthOnly = String(event.date).length === 7;
  const left = monthOnly ? null : daysUntil(event.date);
  return h("div", { class: "cal-event", id: eventId(event), "data-kind": event.kind || null, tabindex: "-1" }, [
    h("span", { class: "d", text: monthOnly ? `${koreanDate(event.date, false)}부터(날짜는 원문에 없음)` : `${koreanDate(event.date, false)}${left !== null && left >= 0 ? `, ${countdown(event.date)}` : ""}` }),
    h("span", { class: "t", text: event.title }),
    event.note ? h("span", { class: "n", text: event.note }) : null,
    event.basis ? h("span", { class: "b", lang: "en", text: `원문: “${event.basis}”` }) : null,
    h("span", { class: "s" }, [h("span", { text: "출처 " }), safeLink(event.link, event.sourceName || "원문") || h("span", { text: event.sourceName || "" })]),
  ]);
}

function month(year, index, events, todayIso, onPick) {
  const prefix = `${year}-${String(index + 1).padStart(2, "0")}`;
  const mine = events.filter((event) => String(event.date).startsWith(prefix)).sort((a, b) => String(a.date).localeCompare(String(b.date)));
  const byDay = new Map();
  for (const event of mine) {
    if (String(event.date).length !== 10) continue;
    const dayNo = Number(String(event.date).slice(8, 10));
    byDay.set(dayNo, [...(byDay.get(dayNo) || []), event]);
  }
  const first = new Date(Date.UTC(year, index, 1)).getUTCDay();
  const length = new Date(Date.UTC(year, index + 1, 0)).getUTCDate();
  const cells = WEEKDAYS.map((name) => h("span", { class: "wd", text: name }));
  for (let blank = 0; blank < first; blank += 1) cells.push(h("span", {}));
  for (let dayNo = 1; dayNo <= length; dayNo += 1) {
    const iso = `${prefix}-${String(dayNo).padStart(2, "0")}`;
    const here = byDay.get(dayNo);
    if (here) {
      const lead = [...here].sort((a, b) => (WEIGHT[b.kind] ?? 1) - (WEIGHT[a.kind] ?? 1))[0];
      cells.push(h("button", { class: "day", type: "button", "data-kind": lead.kind || null, "data-today": iso === todayIso ? "true" : null, text: dayNo,
        "aria-label": `${koreanDate(iso)} ${here.map((event) => event.title).join(", ")}`, title: here.map((event) => event.title).join("\n"), onclick: () => onPick(here[0]) }));
    } else {
      cells.push(h("span", { class: "day", "data-today": iso === todayIso ? "true" : null, text: dayNo }));
    }
  }
  return h("section", { class: "cal-month", "data-has": mine.length ? "true" : null, "aria-label": `${year}년 ${index + 1}월` }, [
    h("h3", {}, [h("span", { text: `${index + 1}월` }), mine.length ? h("small", { text: `일정 ${mine.length}건` }) : null]),
    h("div", { class: "cal-days" }, cells),
    mine.length ? h("div", { class: "cal-events" }, mine.map(eventRow)) : null,
  ]);
}

export function monthGrid(events, year, todayIso, onPick) {
  return h("div", { class: "cal-grid" }, Array.from({ length: 12 }, (_, index) => month(year, index, events, todayIso, onPick)));
}
