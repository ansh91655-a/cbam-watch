// 사이트의 화면 목록. 찾는 말이 화면의 이름이나 그 화면을 부르는 말이면 그 화면으로 바로 가는 길을 보여 준다.
// 화면 요소를 다루지 않으므로 node로 시험한다(tests/test_search.py).
// 화면의 이름과 설명, 그 화면을 찾을 때 쓸 만한 말(words)은 화면의 묶음을 적은 표(js/nav/map.js)에서 온다. 이름은 길게 부르는 이름(title)을 쓴다.
import { allScreens } from "../nav/map.js";

export const PAGES = allScreens().map((one) => ({ href: one.href, name: one.title, about: one.about, words: [...(one.title === one.name ? [] : [one.name]), ...one.words] }));

const fold = (text) => String(text || "").toLowerCase();
const squeeze = (text) => fold(text).replace(/\s+/g, "");
const latin = (text) => /^[a-z0-9 ]+$/.test(text);
// 낱말 뒤에 붙어도 되는 것(조사). 이것 말고 다른 글자가 붙으면 다른 낱말이다("안내서"는 '안내'가 아니다).
const TAILS = new Set(["", "은", "는", "이", "가", "을", "를", "의", "에", "도", "만", "로", "으로", "에서", "와", "과", "란", "이란"]);

// 그 말이 찾는 말에 낱말로 나오는가. 다른 낱말 속에 든 것은 세지 않는다("탄소가격"의 가격, "months"의 hs).
// 여러 낱말로 된 말("진행 상황", "인증서 비용 추정")은 그대로 이어 나오면 된다.
function said(word, asked, tokens) {
  const key = fold(word).trim();
  if (key.includes(" ")) return asked.includes(squeeze(key));
  if (latin(key)) return tokens.includes(key);
  return tokens.some((token) => token.startsWith(key) && TAILS.has(token.slice(key.length)));
}

// 찾는 말에 맞는 화면들. 이름이 똑같은 것, 부르는 말과 똑같은 것, 이름이 나오거나 이름의 일부인 것, 부르는 말이 나온 것의 차례로 돌려준다.
export function findPages(query, pages = PAGES) {
  const asked = squeeze(query);
  if (asked.length < 2) return [];
  const tokens = fold(query).split(/[\s"'‘’“”?!.,;:()\[\]]+/).filter(Boolean);
  const scored = [];
  for (const page of pages) {
    const name = squeeze(page.name);
    let score = 0;
    if (name === asked) score = 4;
    else if (page.words.some((word) => squeeze(word) === asked)) score = 3;
    else if (said(page.name, asked, tokens) || (!latin(asked) && name.includes(asked))) score = 2;
    else if (page.words.some((word) => said(word, asked, tokens))) score = 1;
    if (score) scored.push({ page, score });
  }
  return scored.sort((a, b) => b.score - a.score).map((found) => found.page);
}
