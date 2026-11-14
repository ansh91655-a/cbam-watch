// 글 속 용어 풀이의 찾기: 글에서 용어의 표기를 찾는다. 화면 요소를 다루지 않으므로 node로 시험한다(tests/test_sitejs.py).
// 용어의 자료는 data/gloss.json이다(tools/publish/gloss.py): [{ forms: ["부문 간 보정계수", "CSCF"], ko, en, abbr, text, read }]
// - 국문 표기는 띄어쓰기가 달라도 찾는다("부문간 보정계수").
// - 영문 약어는 낱말 하나로 나온 곳만 찾고 대소문자를 가린다(markets의 ets, see의 SEE에 걸리지 않게). 복수형의 s는 받아 준다(EUAs).
// - 긴 표기부터 본다("EU ETS"가 "ETS"보다, "기본 탄소가격"이 "탄소가격"보다 먼저). 긴 표기에 걸린 자리에서는 그 안의 짧은 표기를 다시 찾지 않는다.

const escape = (text) => text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
const LATIN = /^[A-Za-z0-9][A-Za-z0-9 /()-]*$/;

function pattern(form) {
  if (LATIN.test(form)) return `(?<![A-Za-z0-9])${escape(form).replace(/ /g, "\\s")}s?(?![A-Za-z0-9])`;
  return escape(form).replace(/ /g, "\\s?");
}

// 용어들에서 찾는 틀을 만든다. 식을 만들지 못하는 브라우저(뒤돌아보기를 모르는 옛 브라우저)에서는 아무것도 찾지 않는다.
export function compile(terms) {
  const rows = [];
  (terms || []).forEach((term, at) => (term.forms || []).forEach((form) => { if (form) rows.push({ form, at }); }));
  rows.sort((a, b) => b.form.length - a.form.length);
  let regex = null;
  try {
    regex = rows.length ? new RegExp(rows.map((row) => `(${pattern(row.form)})`).join("|"), "g") : null;
  } catch (error) {
    regex = null;
  }
  return { terms: terms || [], rows, regex };
}

// 글 하나에서 표시할 자리를 찾는다: [{ start, end, at(용어의 자리) }], 앞에서부터.
// seen: 이미 표시한 용어의 자리. 여기에 든 용어는 건너뛰고, 새로 찾은 용어는 넣는다(글 한 편에서 용어마다 한 번만 표시한다).
// skip(용어): 참이면 그 용어를 표시하지 않는다.
export function find(text, book, seen = new Set(), skip = null) {
  if (!book || !book.regex) return [];
  const found = [];
  book.regex.lastIndex = 0;
  for (let hit = book.regex.exec(String(text || "")); hit; hit = book.regex.exec(String(text || ""))) {
    if (!hit[0]) {
      book.regex.lastIndex += 1;
      continue;
    }
    const row = book.rows[hit.findIndex((group, index) => index > 0 && group !== undefined) - 1];
    if (!row || seen.has(row.at) || (skip && skip(book.terms[row.at]))) continue;
    seen.add(row.at);
    found.push({ start: hit.index, end: hit.index + hit[0].length, at: row.at });
  }
  return found;
}
