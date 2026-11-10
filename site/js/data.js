// 게시 데이터 읽기. 화면 파일은 이 모듈만 거친다.
// 데이터는 이 사이트의 data/ 폴더에 있는 JSON 파일이다. 한 번 읽은 파일은 다시 읽지 않는다.

const cache = new Map();

async function load(name, fallback) {
  if (!cache.has(name)) {
    cache.set(name, fetch(`data/${name}.json`, { cache: "no-store" })
      .then((response) => (response.ok ? response.json() : fallback))
      .catch(() => fallback));
  }
  return cache.get(name);
}

export const site = () => load("site", {});
export const items = () => load("items", { items: [] }).then((body) => body.items || []);
export const topics = () => load("topics", { topics: [] }).then((body) => body.topics || []);
export const prices = () => load("prices", { prices: [] }).then((body) => ({ prices: [], upcoming: [], ...body }));
export const documents = () => load("documents", { documents: [] }).then((body) => body.documents || []);
// 문서가 걸려 있는 EU 집행위원회 화면의 이름과 주소. 화면 코드별.
export const documentPages = () => load("documents", { documents: [] }).then((body) => body.pages || {});
// 자동으로 받지 못한 문서 링크의 수. 화면 코드별.
export const unreachableDocuments = () => load("documents", { documents: [] }).then((body) => body.unreachable || {});
export const terms = () => load("terms", { terms: [] }).then((body) => body.terms || []);
export const digests = () => load("digests", { digests: [] }).then((body) => body.digests || []);
export const events = () => load("events", { events: [] }).then((body) => body.events || []);

// 판 비교 결과는 문서마다 따로 있어서 필요할 때만 읽는다.
export function diff(path) {
  return fetch(path, { cache: "no-store" }).then((response) => (response.ok ? response.json() : null)).catch(() => null);
}

// 소식의 날짜: 원문의 게시일. 게시일이 없으면 이 사이트에 실린 날을 쓴다.
// 다만 처음에 한꺼번에 채운 소식(backfill) 가운데 게시일이 없는 것은 날짜가 없는 것으로 본다(실린 날이 소식의 날짜가 아니다).
export function dateOf(item) {
  return String(item.published || (item.backfill ? "" : item.listed) || "");
}

// 날짜가 늦은 것부터. 날짜가 같으면 목록에 오른 날이 늦은 것부터. 날짜가 없는 것은 맨 뒤로 간다.
export function newestFirst(list) {
  return [...list].sort((a, b) => dateOf(b).localeCompare(dateOf(a)) || String(b.listed || "").localeCompare(String(a.listed || "")));
}
