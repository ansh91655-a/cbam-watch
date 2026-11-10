// 큰 머리 아래의 지표 줄. 지금 알아 둘 수치 네 개를 한 줄에 놓는다. 칸을 누르면 그 화면으로 간다.
import * as data from "../../data.js";
import { h } from "../../ui/dom.js";
import { countdown, daysSince, koreanDate, price, signed, today } from "../../ui/format.js";

const NEW_DAYS = 30;
const OPEN_TONES = ["progress", "planned", "dispute"];

const CAVEATS = ["보도 기준", "잠정"];

// flag: 설명 앞에 따로 적는 단서("보도 기준" 같은 것)
function cell(href, label, value, unit, note, flag = "") {
  return h("a", { class: "ledger-cell", href }, [
    h("span", { class: "ledger-label", text: label }),
    h("span", { class: "ledger-value" }, [h("span", { text: value }), unit ? h("small", { text: unit }) : null]),
    h("span", { class: "ledger-note" }, [flag ? h("em", { class: "ledger-flag", text: flag }) : null, note]),
  ]);
}

// 일정 이름의 끝 괄호에 든 단서("보도 기준", "잠정")를 떼어 낸다. 칸이 좁아 이름이 잘려도 단서는 보이도록 앞에 따로 적는 데 쓴다.
export function splitCaveat(title) {
  const text = String(title || "");
  const match = text.match(/^(.*)\(([^()]*)\)$/);
  const parts = match ? match[2].split(",").map((part) => part.trim()) : [];
  const flag = CAVEATS.find((word) => parts.includes(word)) || "";
  if (!flag) return { name: text, flag: "" };
  const rest = parts.filter((part) => part !== flag).join(", ");
  return { name: rest ? `${match[1]}(${rest})` : match[1].trim(), flag };
}

function priceCell(book) {
  const rows = book.prices || [];
  if (!rows.length) return null;
  const latest = rows[rows.length - 1];
  const before = rows[rows.length - 2];
  return cell("#price", "CBAM 인증서 가격", price(latest.value), book.unit || "유로", `${latest.label}${before ? `, 직전보다 ${signed(latest.value - before.value)}` : ""}`);
}

function nextCell(events) {
  const now = today();
  const next = events.filter((event) => String(event.date).length === 10 && event.date >= now).sort((a, b) => a.date.localeCompare(b.date))[0];
  if (!next) return null;
  const { name, flag } = splitCaveat(next.title);
  return cell(`#calendar-${next.date.slice(0, 4)}`, "다음 일정", countdown(next.date), "", `${koreanDate(next.date)} ${name}`, flag);
}

function newsCell(items) {
  const fresh = items.filter((item) => data.dateOf(item) && (daysSince(data.dateOf(item)) ?? 999) <= NEW_DAYS).length;
  return cell("#news", `최근 ${NEW_DAYS}일 소식`, String(fresh), "건", `지금까지 모두 ${items.length}건`);
}

function rulesCell(body) {
  const all = body.regulations || [];
  if (!all.length) return null;
  const open = all.filter((rule) => OPEN_TONES.includes(rule.tone)).length;
  return cell("#rules", "진행 중인 규제", String(open), "건", `살펴보는 규제 ${all.length}건 가운데`);
}

export function ledger(book, events, items, rules) {
  const cells = [priceCell(book), nextCell(events), newsCell(items), rulesCell(rules)].filter(Boolean);
  return cells.length ? h("div", { class: "ledger" }, cells) : null;
}
