// 사이트 검색에 쓰는 줄 만들기. 게시 데이터의 기록 하나를 찾기 엔진(js/laws/engine.js)이 읽는 줄 하나로 바꾼다.
// 화면 요소를 다루지 않으므로 node로 시험한다(tests/test_search.py).
//
// 줄의 꼴: { a: 갈래, p: 번호, n: "", t·k: 이름, x·y: 본문, kind: "article", ref: 원래 기록 }
//   이름과 본문에는 국문과 영문이 섞여 있어, 같은 글을 엔진의 영문 칸(t, x)과 국문 칸(k, y)에 함께 넣는다.
//   본문은 줄바꿈으로 나눠 넣는다. 엔진이 낱말이 나온 줄 하나를 골라 보여 주기 때문이다.
//   names는 그 기록을 부르는 이름들이다. 찾는 말이 이름과 똑같으면 맨 앞에 둔다(js/search/find.js).

const lines = (...parts) => parts.flat(3).map((part) => String(part || "").trim()).filter(Boolean).join("\n");

function row(kind, id, names, body, ref, extra = {}) {
  const shown = names.map((name) => String(name || "").trim()).filter(Boolean);
  const title = shown.join(" ");
  return { a: kind, p: String(id), n: "", t: title, k: title, x: body, y: body, kind: "article", names: shown, ref, ...extra };
}

// 소식: 제목, 요약, 실무 영향, 붙인 주제어. 요약을 내린 소식은 제목으로만 찾는다.
export function newsRows(items) {
  return (items || []).filter((item) => item && item.id && item.title).map((item) =>
    row("news", item.id, [item.title], item.withdrawn ? "" : lines(item.summary, item.impact, (item.topics || []).join(", ")), item));
}

// 규제: 이름과 공식 이름, 요약, 지금 상태, 다음 단계, 분석의 글, 연혁.
export function ruleRows(body) {
  return ((body && body.regulations) || []).map((rule) => row("rules", rule.id, [rule.name, rule.official], lines(
    rule.summary, rule.status, rule.next,
    (((rule.analysis || {}).sections) || []).map((section) => (section.items || []).map((item) => item.text)),
    (rule.timeline || []).map((step) => step.text),
  ), rule));
}

// 용어집: 국문 표기, 영문, 약어, 달리 쓰는 표기가 이름이고 설명이 본문이다.
export function termRows(terms) {
  return (terms || []).map((term, at) => row("terms", at,
    [term.ko, term.en, term.abbr, ...String(term.alt || "").split(/[,/]/)], lines(term.note), term));
}

// 일정: 달력의 일정(event)과 법령에 날짜가 적힌 의무(duty).
// 의무에서 만들어 달력에 실은 일정(event.duty가 있는 것)은 의무 쪽에 같은 내용이 더 자세히 있으므로 뺀다.
export function dateRows(events, duties) {
  return [
    ...(events || []).filter((event) => !event.duty).map((event) => row("dates", `event-${event.date}-${event.title}`, [event.title], lines(event.note, event.basis), event, { form: "event" })),
    ...(duties || []).map((duty) => row("dates", `duty-${duty.id}`, [duty.title], lines(duty.text, duty.who, duty.supplier, duty.verifier, duty.basis), duty, { form: "duty" })),
  ];
}

// 품목 코드: 부속서 I의 품목 이름(영문). 현행 목록(current)과 확대 개정안의 목록(proposed)을 함께 싣는다.
// 같은 줄이 두 목록에 다 있으면 현행 목록의 것만 남긴다.
export function codeRows(book) {
  const current = (book && book.current) || [];
  const same = new Set(current.map((entry) => `${entry.shown}|${entry.sector}`));
  const fresh = ((book && book.proposed) || []).filter((entry) => !same.has(`${entry.shown}|${entry.sector}`));
  return [...current.map((entry) => [entry, "current"]), ...fresh.map((entry) => [entry, "proposed"])]
    .filter(([entry]) => entry && Array.isArray(entry.codes) && entry.codes.length)
    .map(([entry, form]) => row("codes", `${form}-${entry.codes[0]}-${entry.sector}`, [entry.text], lines(entry.shown, entry.codes.join(" ")), entry, { form }));
}

// 원문 대장: 문서 이름과 파일 이름. 규정 원문에 번역해 실은 문서(acts)이면 그 국문 이름으로도 찾는다.
// 같은 문서인지는 문서의 번호가 규정 원문의 원문 주소에 들어 있는지로 본다. act에는 그 문서의 규정 원문 번호를 적는다.
export function fileRows(documents, acts) {
  const known = (acts || []).filter((act) => act && act.url);
  return (documents || []).filter((doc) => doc && doc.title).map((doc) => {
    const act = doc.id ? known.find((one) => String(one.url).includes(String(doc.id))) : null;
    return row("files", doc.id, [doc.title, doc.filename, act ? act.name : ""], "", doc, { act: act ? act.id : "" });
  });
}

// 해설서: 절 하나가 한 줄이다. 절의 제목과 그 절이 풀이한 용어가 이름이고, 문단과 목록, 식, 표, 용어 풀이, 알아 둘 점이 본문이다.
// ref에는 절과 함께 그 절이 든 장의 번호(chapterNo), 이름(chapterTitle), 주소에 쓰는 이름(chapter)을 넣는다.
export function bookRows(book) {
  return ((book && book.chapters) || []).flatMap((chapter, at) => (chapter.sections || []).map((section) => {
    const formula = section.formula || {};
    const terms = section.terms || [];
    return row("book", `${chapter.id}.${section.id}`, [section.title, ...terms.flatMap((term) => [term.ko, term.en, term.abbr])], lines(
      section.body, section.list, formula.text, (formula.parts || []).map((pair) => pair.join(": ")),
      ((section.table || {}).rows || []).map((cells) => cells.join(" ")), terms.map((term) => `${term.ko}: ${term.text}`), section.caveat,
    ), { ...section, chapter: chapter.id, chapterNo: at + 1, chapterTitle: chapter.title });
  }));
}

// 규정 원문의 문서: 법령과 안내 문서의 이름(국문 이름, 공식 이름, 짧은 이름). 본문은 따로 찾는다(js/ui/lawfind.js의 corpus).
export function lawRows(acts) {
  return (acts || []).filter((act) => act && act.id).map((act) =>
    row("laws", act.id, [act.name, act.official, act.short === act.name ? "" : act.short], lines(act.remark), act, { form: "doc" }));
}
