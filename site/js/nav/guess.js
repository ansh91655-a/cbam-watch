// 없는 주소로 왔을 때 찾으려던 화면을 어림한다. 주소의 첫 낱말을 화면의 이름과 그 화면을 찾을 때 쓸 만한 말(js/nav/map.js의 words)에 견준다.
// 화면 요소를 다루지 않으므로 node로 시험한다(tests/test_nav.py).
import { allScreens } from "./map.js";

const FEW = 3;      // 어림한 화면은 이만큼까지만 보여 준다
const MIN = 3;      // 앞머리가 같은지 볼 때의 가장 짧은 글자 수(두 글자로는 엉뚱한 화면이 걸린다)

function plain(text) {
  let found = String(text || "");
  try { found = decodeURIComponent(found); } catch (error) { /* 풀 수 없는 글은 그대로 견준다 */ }
  return found.trim().toLowerCase();
}

// 주소의 글(# 뒤)에서 어림한 화면들: [{ view, href, name, title, icon, about }]. 견줄 것이 없으면 빈 목록.
// 이름이나 찾는 말과 같으면 먼저, 앞머리가 같으면(rule과 rules, handbooks와 handbook) 그다음에 놓는다.
export function guess(text) {
  const word = plain(text).split(/[-./\s]/)[0];
  if (!word) return [];
  const exact = [];
  const close = [];
  for (const one of allScreens()) {
    const keys = [one.view, one.name, ...(one.words || [])].map((key) => String(key).toLowerCase());
    if (keys.includes(word)) exact.push(one);
    else if (word.length >= MIN && keys.some((key) => key.length >= MIN && (key.startsWith(word) || word.startsWith(key)))) close.push(one);
  }
  return [...exact, ...close].slice(0, FEW);
}
