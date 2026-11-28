// 사이트 검색. 찾는 말 하나로 용어집, 해설서, 규제, 소식, 일정, 품목 코드, 원문 대장, 규정 원문을 한 번에 찾는다.
// 낱말을 읽고 점수를 매기는 일은 규정 원문의 찾기 엔진(js/laws/engine.js)이 한다. 그래서 용어집의 낱말은 국문으로 적어도 영문 표기까지 함께 찾는다.
// 화면 요소를 다루지 않으므로 node로 시험한다(tests/test_search.py).
//
// 엔진은 낱말이 하나라도 나온 곳을 모두 돌려준다. 여기에서는 낱말이 함께 나온 곳만 남긴다(needed).
// 그렇게 남는 것이 어디에도 없을 때에만 낱말이 가장 많이 나온 곳으로 물러선다(화면이 reach를 보고 정한다).
import { dateOf } from "../data.js";
import { find } from "../laws/engine.js";

// 갈래와 화면에 놓는 차례. laws에는 문서 이름으로 찾은 것만 들어 있고, 조문은 글을 읽은 뒤에 따로 찾아 더한다(acts, guides).
export const KINDS = ["terms", "book", "rules", "news", "dates", "codes", "files", "laws"];
const ALL = 100000;
const EXACT = 3;        // 찾는 말이 이름과 똑같은 것에 곱하는 값
const RECENT = 0.3;     // 가장 새로운 소식에 더 주는 몫
const RECENT_DAYS = 540; // 이보다 오래된 소식에는 더 주지 않는다

const squeeze = (text) => String(text || "").toLowerCase().replace(/\s+/g, "");

// 찾는 말의 낱말(묶음) 가운데 몇 개가 함께 나와야 찾은 것으로 볼지. 둘까지는 모두, 셋부터는 하나가 빠져도 된다.
export function needed(parsed) {
  const groups = parsed.groups.length;
  return groups <= 2 ? groups : groups - 1;
}

// 줄들에서 찾아 점수가 높은 차례로 돌려준다: [{ row, score, labels, snippet }]. 찾는 말이 이름과 똑같은 것은 앞에 둔다.
export function rank(rows, parsed) {
  const asked = squeeze(parsed.query);
  const hits = find(rows, parsed, { limit: ALL });
  for (const hit of hits) {
    if ((hit.row.names || []).some((name) => squeeze(name) === asked)) hit.score *= EXACT;
  }
  return hits.sort((a, b) => b.score - a.score);
}

function freshness(date, today) {
  const then = Date.parse(String(date).slice(0, 10));
  const now = Date.parse(String(today).slice(0, 10));
  if (Number.isNaN(then) || Number.isNaN(now)) return 0;
  return Math.min(Math.max(1 - (now - then) / (RECENT_DAYS * 86400000), 0), 1);
}

// 갈래마다 찾는다. book은 갈래 이름 → 줄들(js/search/rows.js가 만든 것). today를 넘기면 새 소식을 조금 앞세운다.
export function gather(parsed, book, options = {}) {
  const found = {};
  for (const kind of KINDS) found[kind] = parsed.groups.length ? rank(book[kind] || [], parsed) : [];
  if (options.today) {
    for (const hit of found.news) hit.score *= 1 + RECENT * freshness(dateOf(hit.row.ref), options.today);
    found.news.sort((a, b) => b.score - a.score);
  }
  return found;
}

// 낱말이 need개 이상 함께 나온 것만 남긴다.
export function keep(found, need) {
  return Object.fromEntries(Object.entries(found).map(([kind, hits]) => [kind, hits.filter((hit) => hit.labels.length >= need)]));
}

// 한곳에 가장 많이 함께 나온 낱말의 수. 아무 데도 나오지 않았으면 0.
export function reach(found) {
  let best = 0;
  for (const hits of Object.values(found)) for (const hit of hits) if (hit.labels.length > best) best = hit.labels.length;
  return best;
}

// 어디에도 나오지 않은 낱말들.
export function missing(parsed, found) {
  const seen = new Set();
  for (const hits of Object.values(found)) for (const hit of hits) for (const label of hit.labels) seen.add(label);
  return parsed.groups.map((group) => group.label).filter((label) => !seen.has(label));
}

// 찾은 것의 수: 갈래마다의 수와 모두 더한 수.
export function tally(found) {
  const counts = Object.fromEntries(Object.entries(found).map(([kind, hits]) => [kind, hits.length]));
  return { counts, total: Object.values(counts).reduce((sum, value) => sum + value, 0) };
}
