// 찾는 말이 품목 코드일 때: 그 코드가 CBAM 대상인지를 품목 코드 조회와 같은 셈(js/cn/match.js)으로 가려 둔다.
// 화면 요소를 다루지 않으므로 node로 시험한다(tests/test_search.py).
import { digits, verdict } from "../cn/match.js";
import { spaced } from "../cn/names.js";

// "7208", "7318 15 00", "CN 7208", "HS코드 7208.10"처럼 숫자만 적은 말에서 코드를 읽는다. 코드로 볼 수 없으면 "".
export function codeIn(query) {
  const hit = String(query || "").trim().match(/^(?:(?:cn|hs|taric)\s*)?(?:(?:코드|code)\s*)?[:：]?\s*(\d[\d\s.]{2,13}\d)$/i);
  if (!hit) return "";
  const code = digits(hit[1]);
  return code.length >= 4 ? code : "";
}

// 코드로 읽힌 말을 글에서 찾을 때 쓰는 낱말 묶음(엔진의 parse가 돌려주는 묶음과 같은 꼴).
// 붙여 쓴 꼴(73181500)과 띄어 쓴 꼴(7318 15 00)을 낱말 하나로 본다. 자리마다 따로 찾으면 15나 00이 든 글이 모두 걸린다.
export function codeWords(code) {
  const forms = [...new Set([code, spaced(code)])];
  return { label: spaced(code), ko: forms, en: forms, refs: [] };
}

const LIVE = ["in", "part", "mixed"];
const NAMED = /^(?:cn|hs|taric|코드|code)/i;

// 코드의 판정. 목록에 있는 코드이거나, 코드라고 밝혀 적었거나(CN 9999), 6자리 이상이면 판정을 돌려준다.
// 네 자리 숫자만 적은 말은 연도일 수도 있으므로(2026), 어느 목록에도 없는 것이면 코드로 보지 않는다(null).
// 돌려주는 값: { code, state, rows, later, council }
//   later: 지금의 목록으로는 대상이 아니지만 EU 집행위원회의 확대 개정안이 더한 품목인가.
//   council: 지금의 목록으로는 대상이 아니지만 EU 이사회의 안이 더한 코드인가.
// 견주는 법은 품목 코드 조회(views/cn.js)와 같다.
export function codeVerdict(query, book) {
  const code = codeIn(query);
  if (!code || !book || !Array.isArray(book.current)) return null;
  const now = verdict(code, book.current);
  const open = !["in", "part"].includes(now.state);
  const next = verdict(code, book.proposed || []);
  const fresh = next.rows.filter((row) => !now.rows.some((mine) => mine.entry.shown === row.entry.shown && mine.entry.sector === row.entry.sector));
  const later = open && LIVE.includes(next.state) && fresh.length > 0;
  const council = open && LIVE.includes(verdict(code, (book.council && book.council.added) || []).state);
  const known = LIVE.includes(now.state) || now.state === "excluded" || later || council;
  if (!known && code.length < 6 && !NAMED.test(String(query).trim())) return null;
  return { code, state: now.state, rows: now.rows, later, council };
}
