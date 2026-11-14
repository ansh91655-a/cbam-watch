// 첫 화면에 먼저 보일 소식의 차례. 날짜 차례 그대로 두면 중요도가 낮은 짧은 보도가 맨 위의 '새 소식' 한 줄과 '최근 소식'의 첫 카드를 차지하는 날이 있다.
// 그래서 최근 며칠 안의 소식 가운데 중요도가 보통 이상인 것을 날짜 차례로 먼저 놓고, 낮은 것을 그 뒤에, 그보다 오래된 소식을 맨 뒤에 놓는다.
// 소식 화면의 차례(주제별, 최신순)는 바꾸지 않는다. 화면 요소를 다루지 않으므로 node로 시험한다(tests/test_sitejs.py).
import { isLow } from "./importance.js";
import { RECENT_DAYS, within } from "./recent.js";

// items: 날짜가 늦은 것부터 놓인 소식들, dateOf: 소식의 날짜(YYYY-MM-DD)를 주는 함수, today: 오늘(YYYY-MM-DD)
export function leadFirst(items, today, dateOf, days = RECENT_DAYS) {
  const fresh = [];
  const quiet = [];
  const older = [];
  for (const item of items || []) {
    if (!within(dateOf(item), today, days)) older.push(item);
    else (isLow(item) ? quiet : fresh).push(item);
  }
  return [...fresh, ...quiet, ...older];
}
