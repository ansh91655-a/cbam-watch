// 규제 변화 기록: 규제마다의 연혁을 합쳐 최근 며칠 안에 달라진 것만 날짜가 늦은 것부터 놓는다(#rules-recent, #rules-recent-90).
// 날짜는 그 일이 일어난 날이다(연혁의 date). 며칠 안인지는 소식 화면과 같은 법으로 가린다(news/recent.js).
// 화면 요소를 다루지 않으므로 node로 시험한다(tests/test_rule_changes.py).
import { within } from "../news/recent.js";

export const RECENT = "recent";   // 주소에 쓰는 값. 규제와 묶음의 이름은 이 말로 시작하지 않는다(시험이 본다)
export const PERIODS = [30, 90];  // 고를 수 있는 날수. 첫째가 기본이다

// 주소의 값("recent", "recent-90")에서 날수. 변화 기록의 주소가 아니면 0, 고를 수 없는 날수면 기본 날수
export function periodOf(arg) {
  const [name, days = ""] = String(arg || "").split("-");
  if (name !== RECENT) return 0;
  return PERIODS.includes(Number(days)) ? Number(days) : PERIODS[0];
}

export function hrefOf(days = PERIODS[0]) {
  return days === PERIODS[0] ? `#rules-${RECENT}` : `#rules-${RECENT}-${days}`;
}

// 왼쪽 고르기의 '최근 변화'가 가리키는 날수: 변화 기록을 보고 있으면 보고 있는 날수, 다른 화면이면 기본 날수.
// 고른 표시가 붙은 칸의 건수와 주소가 보고 있는 화면과 같게 하려는 것이다(90일을 보는데 30일의 건수를 적지 않는다).
export function sidePeriod(arg) {
  return periodOf(arg) || PERIODS[0];
}

// 최근 days일 안의 연혁: [{ date, text, source, link, press, rule }]. rule은 그 연혁이 든 규제다.
// 날짜가 늦은 것부터, 같은 날이면 규제의 차례대로, 한 규제 안에서는 나중에 적힌 것부터 놓는다. 앞날의 날짜와 날짜가 아닌 것은 뺀다.
export function changes(rules, today, days = PERIODS[0]) {
  const rows = [];
  (rules || []).forEach((rule, order) => {
    (rule.timeline || []).forEach((event, at) => {
      const date = String(event.date || "");
      if (/^\d{4}-\d{2}-\d{2}$/.test(date) && date <= today && within(date, today, days)) rows.push({ row: { ...event, rule }, order, at });
    });
  });
  return rows.sort((a, b) => b.row.date.localeCompare(a.row.date) || a.order - b.order || b.at - a.at).map((one) => one.row);
}
