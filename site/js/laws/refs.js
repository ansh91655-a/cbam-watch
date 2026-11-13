// 소식, 의무 일정, 용어집에 적힌 법령과 조문을 규정 원문으로 잇는 자료(data/refs.json, tools/publish/crossrefs.py가 만든다)를 화면이 쓰기 좋게 다룬다.
// 글에 법령과 조문이 또렷이 적힌 곳만 이어져 있다. 화면 요소를 다루지 않으므로 node로 시험한다(tests/test_sitejs.py).

// 이은 곳의 주소: 문서 전체이면 #law-<문서>, 조각(조, 부속서)이면 #law-<문서>.<조각>
export function lawHref(ref) {
  return `#law-${ref.act}${ref.part ? `.${ref.part}` : ""}`;
}

// 의무 일정의 주소: 그해의 일정 화면에서 그 일정으로 간다
export function dutyHref(duty) {
  return `#calendar-${String(duty.date || "").slice(0, 4)}.duty-${duty.id}`;
}

// 용어의 주소: 용어집을 그 말로 걸러 보여 준다
export function termHref(term) {
  return `#terms-${encodeURIComponent(term.en || term.ko || "")}`;
}

// 조각 하나(partId가 ""이면 문서 전체)에 이어진 것: { items, duties, terms, more }. 아무것도 없으면 null.
export function linkedTo(refs, actId, partId = "") {
  const found = (((refs || {}).laws || {})[actId] || {})[partId || ""];
  if (!found) return null;
  const row = { items: [], duties: [], terms: [], more: 0, ...found };
  return row.items.length + row.duties.length + row.terms.length ? row : null;
}

// 한 줄로 간추린 말: "의무 일정 1건, 소식 3건, 용어 2건"
export function tally(row) {
  if (!row) return "";
  return [["의무 일정", row.duties.length], ["소식", row.items.length + (row.more || 0)], ["용어", row.terms.length]]
    .filter(([, size]) => size).map(([name, size]) => `${name} ${size}건`).join(", ");
}
