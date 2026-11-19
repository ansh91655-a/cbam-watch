// 글 속 용어 풀이의 범위. 같은 낱말이라도 제도마다 뜻이 다르다(영국 CBAM의 '회계기간'과 '인정기구', EU CBAM의 '과징금'과 '검증기관').
// 그래서 범위가 있는 용어는 그 범위의 글에만 쓰고, 그 범위의 글에는 다른 용어를 쓰지 않는다.
// 범위는 해설서의 장이 정하고(tools/publish/handbook.py의 scope), 자료는 data/gloss.json에 있다(tools/publish/gloss.py):
//   { terms: [{ …, scope?: "uk" }], scopes: { uk: [그 범위의 풀이를 쓰는 소식의 id, …] } }
// 화면 요소를 다루지 않으므로 node로 시험한다(tests/test_sitejs.py).

const has = (body, name) => Boolean(body && body.scopes && Object.prototype.hasOwnProperty.call(body.scopes, name));

// 글의 범위. where.scope: 해설서 장의 범위나 규제 묶음의 이름, where.item: 소식의 id.
// 그 이름의 범위가 자료에 없으면(EU의 규제 묶음, 보통의 소식) 범위가 없는 글이다("").
export function scopeOf(body, where = {}) {
  if (where.scope && has(body, where.scope)) return where.scope;
  if (where.item) return Object.keys((body && body.scopes) || {}).find((name) => (body.scopes[name] || []).includes(where.item)) || "";
  return "";
}

// 그 범위의 글에 쓸 용어들
export function termsOf(body, scope = "") {
  return ((body && body.terms) || []).filter((term) => (term.scope || "") === scope);
}
