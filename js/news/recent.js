// 최근 소식: 날짜가 오늘에서 며칠 안인 소식. 첫 화면의 '최근 30일 소식' 칸이 센 것과 소식 화면에서 보이는 것이
// 같도록 날수와 가리는 법을 한곳에 둔다. 화면 요소를 다루지 않으므로 node로 시험한다(tests/test_sitejs.py).

export const RECENT = "recent";   // 주소에 쓰는 값: #news-recent
export const RECENT_DAYS = 30;
export const PERIODS = [30, 90];  // 소식 화면의 '기간' 조건에서 고를 수 있는 날수

const DAY = 86400000;

// date(YYYY-MM-DD)가 today(YYYY-MM-DD)에서 days일 안인지. 날짜가 없거나 날짜가 아닌 것은 최근이 아니다.
export function within(date, today, days = RECENT_DAYS) {
  const then = Date.parse(`${String(date || "").slice(0, 10)}T00:00:00Z`);
  const now = Date.parse(`${String(today || "").slice(0, 10)}T00:00:00Z`);
  if (Number.isNaN(then) || Number.isNaN(now)) return false;
  return Math.round((now - then) / DAY) <= days;
}
