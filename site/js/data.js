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
export const sources = () => load("sources", { sources: [] }).then((body) => body.sources || []);
export const documents = () => load("documents", { documents: [] }).then((body) => body.documents || []);
// 자동으로 받지 못한 문서 링크의 수. 화면 코드별.
export const unreachableDocuments = () => load("documents", { documents: [] }).then((body) => body.unreachable || {});
export const terms = () => load("terms", { terms: [] }).then((body) => body.terms || []);
export const digests = () => load("digests", { digests: [] }).then((body) => body.digests || []);
export const events = () => load("events", { events: [] }).then((body) => body.events || []);

// 판 비교 결과는 문서마다 따로 있어서 필요할 때만 읽는다.
export function diff(path) {
  return fetch(path, { cache: "no-store" }).then((response) => (response.ok ? response.json() : null)).catch(() => null);
}

// 게시일이 늦은 것부터. 게시일이 같으면 목록에 오른 날이 늦은 것부터.
export function newestFirst(list) {
  return [...list].sort((a, b) =>
    String(b.published || b.listed || "").localeCompare(String(a.published || a.listed || "")) ||
    String(b.listed || "").localeCompare(String(a.listed || "")));
}

// 이 사이트에 늦게 오른 것부터. 오른 날이 같으면 게시일이 늦은 것부터. 첫 화면의 '새로 오른 소식'에 쓴다.
export function newestListedFirst(list) {
  return [...list].sort((a, b) =>
    String(b.listed || "").localeCompare(String(a.listed || "")) ||
    String(b.published || "").localeCompare(String(a.published || "")));
}
