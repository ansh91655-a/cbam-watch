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
// 규제별 진행 상황: 묶음, 규제마다의 단계와 연혁
export const regulations = () => load("regulations", { groups: [], regulations: [] });
// 품목 코드 조회에 쓰는 목록: 현행 부속서(current)와 확대 개정안의 부속서(proposed)
export const cn = () => load("cn", { current: [], proposed: [], council: { added: [], removed: [] } });
export const events = () => load("events", { events: [] }).then((body) => body.events || []);
// 실무 달력: 법령에 날짜가 적힌 의무 일정
export const duties = () => load("duties", { duties: [] }).then((body) => ({ duties: [], ...body }));
// CBAM 계수(무상할당을 줄여 가는 비율)의 현행 값과 개정안 값
export const factor = () => load("factor", { paths: [] }).then((body) => ({ paths: [], ...body }));
// 인증서 비용 추정의 자료(법령의 표에서 만든 품목별 CBAM 벤치마크와 기본값, 마크업 등). 품목이 많아 짧은 꼴로 실려 있다(js/calc/compute.js의 unpack이 편다).
export const calc = () => load("calc", { goods: [] });
// CBAM 해설서(tools/publish/handbook.py): 장과 절, 절마다의 근거 조문, 한데 모은 용어 풀이
export const handbook = () => load("handbook", { chapters: [] }).then((body) => ({ chapters: [], terms: [], ...body }));
// 규정 원문: 법령의 목록과 차례, 법령 하나의 본문과 번역, 전체 규정 검색에 쓰는 글(크므로 찾을 때만 읽는다)
export const laws = () => load("laws/index", { acts: [] }).then((body) => body.acts || []);
export const law = (id) => (/^[0-9A-Za-z-]+$/.test(String(id)) ? load(`laws/${id}`, null) : Promise.resolve(null));
// 문서의 앞선 판과 견줘 달라진 문단(앞선 판을 받아 둔 문서만 있다). 없으면 null
export const changes = (id) => (/^[0-9A-Za-z-]+$/.test(String(id)) ? load(`laws/changes/${id}`, null) : Promise.resolve(null));
// 원문과 번역을 나란히 볼 수 있는 PDF의 목록(문서 id별: 원문 파일, 국문 파일, 쪽 수와 쪽의 크기)
export const pdfs = () => load("laws/pdf", { docs: {} }).then((body) => body.docs || {});
export const lawRows = () => load("laws/search", { rows: [] }).then((body) => body.rows || []);
export const guideRows = () => load("laws/search-guides", { rows: [] }).then((body) => body.rows || []);
// 하나로 묶은 소식의 옛 번호 → 남긴 소식의 번호
// 부문별 모아 보기의 자료(tools/publish/sectors.py)
export const sectors = () => load("sectors", {}).then((body) => ({ sectors: [], common: [], law: {}, ...body }));
// 소식, 의무 일정, 용어집과 규정 원문을 잇는 자료(tools/publish/crossrefs.py). 없으면 빈 것으로 본다(잇는 링크만 보이지 않는다)
export const refs = () => load("refs", {}).then((body) => ({ items: {}, duties: {}, terms: {}, laws: {}, ...body }));
export const moved = () => load("moved", { moved: {} }).then((body) => body.moved || {});

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
