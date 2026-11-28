// 전체 규정에서 찾기. 낱말이나 질문을 받아, 그 내용이 어느 법령의 어느 조에 있는지 골라 준다.
// 화면과 떨어져 있어 node로 시험한다(tests/test_laws.py). 문장을 지어 답하지 않고 낱말이 나온 자리만 알려 준다.
//
// 찾는 방식
// 1. 질문에서 용어집의 낱말(국문, 영문, 약어)을 찾는다. 그 낱말의 영문 표기로 원문을, 국문 표기로 번역과 조의 이름을 찾는다.
//    그래서 번역이 아직 없는 조문도 국문 질문으로 찾을 수 있다. 용어집이 가리키는 조(CBAM 규정 제○조)는 앞세운다.
// 2. 남은 낱말은 조사와 어미를 떼고 그대로 찾는다. 자주 쓰는 일상어 몇 개는 영문 낱말로도 찾는다(EVERYDAY).
// 3. 드물게 나오는 낱말일수록, 조의 이름에 나올수록, 여러 낱말이 한 조에 함께 나올수록 앞에 둔다.
// 4. 짧은 영문 낱말은 다른 낱말 속에 든 것을 찾은 것으로 보지 않는다.
//    세 글자까지의 약어(ETS, CEM)는 낱말 하나로 나온 곳만(markets, cement에 걸리지 않게), 그 밖의 세 글자까지의 낱말(low, use)은 낱말의 첫머리에서만 찾는다(allow, cause에 걸리지 않게).
//    숫자만 적은 낱말(50, 7208)은 그 숫자 하나로 나온 곳만 찾는다(150, 72081000에 걸리지 않게).
//    두 글자 약어는 질문에 대문자로 적었을 때만 약어로 읽는다(영문 질문의 of, ad가 약어로 읽히지 않게).
//    질문에서 용어집의 영문 표기를 읽을 때에도 낱말의 첫머리부터 맞아야 한다(neutral의 eu를 EU로 읽지 않게).

export const BASE_ACT = "32023R0956";
// 내용이 CBAM 규정 통합본에 이미 반영된 개정 법령과, 전환기간이 끝난 법령·안내 자료는 뒤로 미룬다
const ACT_FACTOR = { [BASE_ACT]: 1.15, "32025R2083": 0.6, "32025R2549": 0.7, "32025R2550": 0.7, "32026R1740": 0.7, "32023R1773": 0.55,
  "guide-importers": 0.55, "fact-cement": 0.5, "fact-aluminium": 0.5, "fact-fertilisers": 0.5, "fact-hydrogen": 0.5, "fact-electricity": 0.5 };
const KIND_FACTOR = { article: 1, section: 1, annex: 0.8, recitals: 0.5 };
// 흔한 영문 낱말과 글자가 같은 약어. 두 글자 약어처럼, 질문에 대문자로 적었을 때만 약어로 읽는다(see article 5의 see).
const PLAIN = new Set(["see", "bat", "cog"]);
const STOP = new Set(["무엇", "뭐", "어디", "언제", "어떻게", "어떤", "어느", "왜", "누가", "누구", "얼마", "얼마나", "관련", "관한", "대한", "대해", "대하여", "규정", "규제", "법령", "조문", "조항",
  "내용", "있나요", "있는지", "있습니까", "있어요", "알려", "알려줘", "주세요", "주십시오", "하나요", "되나요", "인가요", "무슨", "경우", "어디에", "무엇인가요", "뜻", "설명",
  "the", "of", "a", "an", "in", "on", "is", "are", "what", "where", "when", "how", "which", "does", "do", "for", "to", "and", "or", "about", "under"]);
const ENDING = /(에서는|에서도|에서|에게|으로는|으로|까지|부터|하려면|하여야|해야|하나요|하는지|하는|하면|하고|하기|합니다|한다|할|한|되는지|되는|되나요|됩니다|된다|된|인가요|인지|입니까|이란|란|은|는|이|가|을|를|의|에|와|과|도|만|로)$/;
// 용어집에 없는 일상어를 원문의 낱말로 이어 준다(줄기만 적어 활용형도 걸리게 한다)
const EVERYDAY = { 기한: ["deadline", "time limit", "no later than"], 벌금: ["penalt"], 과태료: ["penalt"], 처벌: ["penalt"], 제재: ["penalt"], 벌칙: ["penalt"], 면제: ["exempt"], 예외: ["derogation", "exempt"],
  판매: ["sale of", "sell"], 구매: ["purchase", "buy"], 보고: ["report"], 등록: ["regist"], 승인: ["authoris"], 취소: ["revok", "cancel"], 정의: ["definition"], 시행: ["entry into force", "shall apply from"],
  수입: ["import"], 원산지: ["origin"], 전기: ["electricity"], 이의: ["appeal"], 불복: ["appeal"], 기록: ["record"], 보관: ["keep", "record"], 담보: ["guarantee"], 보증: ["guarantee"], 비밀: ["confidential"],
  개인정보: ["personal data"], 대리인: ["representative"], 환급: ["repurchase", "reimburse"], 가격: ["price"], 제출: ["surrender", "submit"], 검증: ["verif"], 신고: ["declar"], 우회: ["circumvent"] };

const fold = (text) => String(text || "").toLowerCase();
const squeeze = (text) => fold(text).replace(/\s+/g, "");
const escape = (text) => text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

const SHORT = 3;  // 이보다 길지 않은 영문 낱말은 다른 낱말 속에 든 것을 찾은 것으로 보지 않는다
const LETTER = /[a-z]/;
const DIGIT = /[0-9]/;
const WORDY = /[a-z0-9]/;
// 낱말 하나로 나온 곳만 찾을 약어들: 용어집의 짧은 약어와, 질문에 대문자로 적은 짧은 낱말. makeIndex와 parse가 채운다.
const ABBR = new Set();

// 그 낱말을 어떻게 찾을지: "whole"(낱말 하나로 나온 곳만), "start"(낱말의 첫머리에서만), "number"(그 숫자 하나로 나온 곳만), ""(어디에 나와도).
function manner(needle) {
  if (/^[0-9]+$/.test(needle)) return "number";
  if (needle.length > SHORT || !/^[a-z]+$/.test(needle)) return "";
  return ABBR.has(needle) ? "whole" : "start";
}

// 낱말이 그 자리에서 기준에 맞게 나왔는가. 약어 앞뒤의 숫자는 괜찮고(ETS2), 복수형의 s, es는 받아 준다(EUAs).
function fits(haystack, at, needle, how) {
  if (!how) return true;
  const before = at > 0 ? haystack[at - 1] : "";
  const end = at + needle.length;
  if (how === "number") return !DIGIT.test(before) && !DIGIT.test(haystack[end] || "");
  if (LETTER.test(before)) return false;
  return how === "start" || /^(?:es|s)?(?:[^a-z]|$)/.test(haystack.slice(end, end + 3));
}

// 소문자로 바꾼 글에서 낱말이 나오는 첫 자리. 없으면 -1.
function seek(haystack, needle, from = 0) {
  if (!needle || !haystack) return -1;
  const how = manner(needle);
  for (let at = haystack.indexOf(needle, from); at >= 0; at = haystack.indexOf(needle, at + 1)) {
    if (fits(haystack, at, needle, how)) return at;
  }
  return -1;
}

// 질문(소문자로 바꾼 것)에 영문 표기가 낱말로 나오는 자리. 없으면 -1. 다른 낱말 속에 든 것은 세지 않는다(neutral의 eu, europe의 euro).
// 뒤에는 복수형의 s, es만 붙을 수 있다. bends이면 활용형의 d, ed, ing도 받는다(reporting, verified).
function typedAt(lowered, form, bends) {
  const tail = bends ? /^(?:es|s|d|ed|ing)?(?:[^a-z0-9]|$)/ : /^(?:es|s)?(?:[^a-z0-9]|$)/;
  for (let at = lowered.indexOf(form); at >= 0; at = lowered.indexOf(form, at + 1)) {
    if (at > 0 && WORDY.test(lowered[at - 1])) continue;
    if (tail.test(lowered.slice(at + form.length, at + form.length + 4))) return at;
  }
  return -1;
}

const latin = (form) => /^[\x20-\x7e]+$/.test(form);  // 영문, 숫자, 기호로만 된 표기

// 질문에서 읽은 표기를 남은 글에서 뗀다. 영문 표기는 낱말로 나온 곳만, 그 낱말의 끝까지 뗀다(reporting에서 report를 떼고 ing를 남기지 않게).
function cut(rest, form, bends) {
  if (!latin(form)) return rest.split(form).join(" ");
  let left = rest;
  for (let at = typedAt(left, form, bends); at >= 0; at = typedAt(left, form, bends)) {
    let end = at + form.length;
    while (end < left.length && WORDY.test(left[end])) end += 1;
    left = `${left.slice(0, at)} ${left.slice(end)}`;
  }
  return left;
}

function count(haystack, needle) {
  let found = 0;
  for (let at = seek(haystack, needle); at >= 0 && found < 9; at = seek(haystack, needle, at + needle.length)) found += 1;
  return found;
}

// 용어집(data/terms.json의 낱말들)을 찾기 좋은 꼴로 바꾼다.
export function makeIndex(terms) {
  return (terms || []).map((term) => {
    const ko = [term.ko, ...String(term.alt || "").split(/[,/]/)].map((form) => String(form || "").replace(/\([^)]*\)/g, "").trim()).filter((form) => form.length >= 2);
    const en = String(term.en || "").split(/\s*\/\s*/).map((form) => fold(form.replace(/\([^)]*\)/g, "")).trim()).filter((form) => form.length >= 3);
    const refs = /^CBAM 규정/.test(String(term.article || "")) ? [...String(term.article).matchAll(/제(\d+[a-z]?)조/g)].map((hit) => `art-${hit[1]}`) : [];
    const abbr = fold(term.abbr || "");
    if (abbr.length <= SHORT && /^[a-z]+$/.test(abbr)) ABBR.add(abbr);
    return { label: term.ko, ko, en, abbr, shown: String(term.abbr || "").trim(), refs };
  }).filter((entry) => entry.ko.length || entry.en.length);
}

function stem(word) {
  let found = word;
  for (let turn = 0; turn < 2; turn += 1) {
    const cut = found.replace(ENDING, "");
    if (cut === found || cut.length < 2) break;
    found = cut;
  }
  return found;
}

// 질문을 찾을 낱말의 묶음으로 바꾼다. 묶음 하나가 개념 하나다: { label, ko: [국문 표기], en: [영문 표기], refs: [용어집이 가리키는 조] }
export function parse(query, index) {
  const text = String(query || "").trim();
  const flat = squeeze(text);
  const lowered = ` ${fold(text)} `;
  const groups = [];
  let rest = fold(text);
  for (const hit of text.matchAll(/(?:^|[^A-Za-z0-9])([A-Z]{2,3})(?![A-Za-z0-9])/g)) ABBR.add(fold(hit[1]));  // 대문자로 적은 짧은 낱말은 약어로 본다(NCA, UK)
  const quoted = [...text.matchAll(/"([^"]{2,})"/g)].map((hit) => hit[1]);
  for (const phrase of quoted) {  // 따옴표로 묶은 글은 그대로 찾는다
    groups.push({ label: phrase, ko: [fold(phrase)], en: [fold(phrase)], refs: [] });
    rest = rest.replace(fold(phrase), " ");
  }
  const taken = [];
  for (const entry of [...(index || [])].sort((a, b) => b.label.length - a.label.length)) {
    const ko = entry.ko.find((form) => (latin(form) ? typedAt(lowered, fold(form), false) >= 0 : flat.includes(squeeze(form))));
    const en = entry.en.find((form) => typedAt(lowered, form, form.length > SHORT) >= 0);
    const abbr = entry.abbr && new RegExp(`(^|[^a-z0-9])${escape(entry.abbr)}([^a-z0-9]|$)`).test(fold(text))
      && ((entry.abbr.length > 2 && !PLAIN.has(entry.abbr)) || !entry.shown || new RegExp(`(^|[^A-Za-z0-9])${escape(entry.shown)}([^A-Za-z0-9]|$)`).test(text));
    if (!ko && !en && !abbr) continue;
    const key = squeeze(ko || en || entry.abbr);
    if (taken.some((other) => other.includes(key))) continue;  // 더 긴 낱말에 든 낱말은 따로 세지 않는다
    taken.push(key);
    // 약어가 흔한 영문 낱말과 같으면(OF) 그 약어로는 찾지 않는다(온 이름으로만 찾는다)
    groups.push({ label: entry.label, ko: entry.ko.map(fold), en: [...entry.en, ...(entry.abbr && !STOP.has(entry.abbr) ? [entry.abbr] : [])], refs: entry.refs });
    if (ko) rest = cut(rest, fold(ko), false);
    if (en) rest = cut(rest, en, en.length > SHORT);
    if (entry.abbr) rest = cut(rest, entry.abbr, false);
  }
  for (const raw of rest.replace(/["'‘’“”?!.,;:()\[\]]/g, " ").split(/\s+/)) {
    const word = /[가-힣]/.test(raw) ? stem(raw) : raw;
    if (word.length < 2 || STOP.has(word) || STOP.has(raw)) continue;
    if (taken.some((other) => other.includes(squeeze(word))) || groups.some((group) => group.label === word)) continue;
    groups.push({ label: word, ko: [word], en: /[가-힣]/.test(word) ? (EVERYDAY[word] || []) : [word], refs: [] });
  }
  return { query: text, groups };
}

function prepared(row) {
  if (!row._x) {
    row._x = fold(row.x);
    row._y = fold(row.y);
    row._t = fold(row.t);
    row._k = fold(`${row.n} ${row.k}`);
  }
  return row;
}

// 줄(조각)들에서 관련된 것을 골라 점수가 높은 차례로 돌려준다: [{ row, score, labels: [걸린 낱말], snippet }]
export function find(rows, parsed, options = {}) {
  const groups = parsed.groups;
  if (!groups.length) return [];
  const pool = (rows || []).filter((row) => !options.act || row.a === options.act).map(prepared);
  const seen = pool.map((row) => groups.map((group) => {
    const body = group.en.reduce((sum, needle) => sum + count(row._x, needle), 0) + group.ko.reduce((sum, needle) => sum + count(row._y, needle), 0);
    const title = group.en.some((needle) => seek(row._t, needle) >= 0) || group.ko.some((needle) => seek(row._k, needle) >= 0);
    return { body, title };
  }));
  const rarity = groups.map((group, which) => Math.log(1 + pool.length / (1 + seen.filter((hits) => hits[which].body || hits[which].title).length)));
  const found = [];
  pool.forEach((row, at) => {
    let score = 0;
    const labels = [];
    groups.forEach((group, which) => {
      const hit = seen[at][which];
      if (!hit.body && !hit.title) return;
      labels.push(group.label);
      score += ((hit.title ? 5 : 0) + Math.min(hit.body, 4)) * rarity[which];
      if (row.a === BASE_ACT && group.refs.includes(row.p)) score += 6;
    });
    if (!labels.length) return;
    score *= (1 + 0.6 * (labels.length - 1)) * (KIND_FACTOR[row.kind || kindOf(row.p)] || 1) * (ACT_FACTOR[row.a] || 1);
    found.push({ row, score, labels, snippet: snippet(row, groups.filter((group) => labels.includes(group.label))) });
  });
  return found.sort((a, b) => b.score - a.score).slice(0, options.limit || 20);
}

export function kindOf(part) {
  if (part.startsWith("art-")) return "article";
  if (part.startsWith("sec-")) return "section";  // 안내 문서의 절
  return part.startsWith("annex") ? "annex" : "recitals";
}

// 걸린 낱말이 처음 나오는 문단을 잘라 돌려준다: { text, lang }. 번역에 나오면 번역을, 아니면 원문을 보여 준다.
function snippet(row, groups, width = 190) {
  for (const [field, lang, pick] of [["y", "ko", (group) => group.ko], ["x", "en", (group) => group.en]]) {
    const lowered = row[`_${field}`];
    let best = -1;
    for (const group of groups) for (const needle of pick(group)) {
      const at = seek(lowered, needle);
      if (at >= 0 && (best < 0 || at < best)) best = at;
    }
    if (best < 0) continue;
    const whole = row[field];
    const start = whole.lastIndexOf("\n", best) + 1;
    const end = whole.indexOf("\n", best) < 0 ? whole.length : whole.indexOf("\n", best);
    let from = Math.max(start, best - Math.floor(width / 3));
    if (from > start) from = whole.indexOf(" ", from) + 1 || from;
    const to = Math.min(end, from + width);
    return { text: `${from > start ? "… " : ""}${whole.slice(from, to).trim()}${to < end ? " …" : ""}`, lang };
  }
  return { text: "", lang: "ko" };
}

// 화면에서 눈에 띄게 칠할 낱말들.
export function marks(parsed) {
  return [...new Set(parsed.groups.flatMap((group) => [...group.ko, ...group.en]).filter((needle) => needle.length >= 2))].sort((a, b) => b.length - a.length);
}

// 글을 칠할 낱말로 갈라 [글, 칠할 것인가] 쌍으로 돌려준다(화면이 <mark>로 그린다).
// 낱말을 찾는 기준은 find와 같다(짧은 영문 낱말은 낱말 하나로 나온 곳만). 겹치는 자리에서는 먼저 나오는 것, 그다음에는 긴 것을 칠한다.
export function split(text, needles) {
  const source = String(text || "");
  const lowered = fold(source);
  if (!needles.length || !source || lowered.length !== source.length) return [[source, false]];
  const spans = [];
  for (const needle of needles) {
    for (let at = seek(lowered, needle); at >= 0; at = seek(lowered, needle, at + needle.length)) {
      // 영문 낱말 뒤에 붙은 복수형의 s, es까지 함께 칠한다(default values)
      const tail = LETTER.test(needle[needle.length - 1]) ? (lowered.slice(at + needle.length, at + needle.length + 3).match(/^(es|s)(?:[^a-z]|$)/) || [])[1] || "" : "";
      spans.push([at, at + needle.length + tail.length]);
    }
  }
  spans.sort((a, b) => a[0] - b[0] || b[1] - a[1]);
  const pieces = [];
  let done = 0;
  for (const [from, to] of spans) {
    if (from < done) continue;
    if (from > done) pieces.push([source.slice(done, from), false]);
    pieces.push([source.slice(from, to), true]);
    done = to;
  }
  if (done < source.length) pieces.push([source.slice(done), false]);
  return pieces;
}
