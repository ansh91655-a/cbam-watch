// 사이트의 화면 목록. 찾는 말이 화면의 이름이나 그 화면을 부르는 말이면 그 화면으로 바로 가는 길을 보여 준다.
// 화면 요소를 다루지 않으므로 node로 시험한다(tests/test_search.py).
// about은 그 화면의 머리글에 적힌 설명을 줄인 것이고, words에는 그 화면을 찾을 때 쓸 만한 말을 적는다(이름은 따로 적지 않아도 된다).

export const PAGES = [
  { href: "#home", name: "최신 동향", about: "새로 달라진 점과 주요 소식", words: ["첫 화면", "home"] },
  { href: "#news", name: "소식", about: "2025년 1월부터의 소식과 국문 요약", words: ["뉴스", "기사", "news"] },
  { href: "#rules", name: "규제", about: "규제마다의 지금 단계와 남은 절차", words: ["진행 상황", "진행 단계", "입법"] },
  { href: "#price", name: "CBAM 인증서 가격", about: "EU 집행위원회가 게시한 인증서 가격과 추세", words: ["가격", "price"] },
  { href: "#calc", name: "인증서 비용 추정", about: "품목과 물량으로 어림하는 인증서 수와 비용", words: ["비용", "추정", "계산", "계산기", "calculator", "cost"] },
  { href: "#calendar", name: "일정", about: "출처에 날짜가 적힌 일정과 법령의 의무 기한", words: ["달력", "기한", "마감", "calendar", "deadline"] },
  { href: "#laws", name: "규정 원문", about: "CBAM 법령과 가이던스의 원문과 국문 번역", words: ["법령", "규정", "조문", "번역", "가이던스", "guidance", "regulation"] },
  { href: "#docs", name: "원문 대장", about: "EU 집행위원회가 올린 CBAM 문서", words: ["문서", "자료", "pdf", "내려받기", "다운로드", "download"] },
  { href: "#terms", name: "용어집", about: "국문 정리에 쓰는 용어의 표기 기준", words: ["용어", "표기", "glossary"] },
  { href: "#sector", name: "부문별 보기", about: "부문마다의 대상 품목, 안내 문서, 기본값, 소식", words: ["부문", "부문별", "품목별", "업종", "sector"] },
  { href: "#cn", name: "품목 코드 조회", about: "CN 코드가 CBAM 대상 품목인지 확인", words: ["품목", "대상 품목", "cn", "hs"] },
  { href: "#about", name: "안내", about: "이 사이트에서 볼 수 있는 것과 알아 둘 점", words: ["사이트 안내", "소개", "about"] },
];

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
