// 요약 칸. 큰 머리 바로 아래에 가장 최근의 요약을 둔다: 왼쪽에 이름과 제목과 기간, 오른쪽에 첫 문단.
// 나머지 문단과 근거가 된 소식은 '요약 이어서 읽기'를 눌러 본다.
import { h, unsplit } from "../../ui/dom.js";
import { koreanDate, today } from "../../ui/format.js";
import { icon } from "../../ui/icons.js";

// 가장 최근의 요약(기간이 가장 늦은 것)
export function latestDigest(digests) {
  return [...digests].sort((a, b) => String(b.to).localeCompare(String(a.to)))[0] || null;
}

// 요약을 부르는 이름. 주간 요약은 월요일에 지난주의 것을 쓰므로, 기간이 오늘에서 얼마나 떨어져 있는지를 보고 부른다.
// 기간이 한 주보다 긴 요약(사이트를 열 때 쓴 것처럼 여러 주를 묶은 것)은 주간 요약이라고 부르지 않는다.
export function digestName(digest, now = today()) {
  const days = (from, to) => Math.round((Date.parse(`${to}T00:00:00Z`) - Date.parse(`${from}T00:00:00Z`)) / 86400000);
  const since = days(digest.to, now);  // 요약의 마지막 날에서 오늘까지
  if (days(digest.from, digest.to) + 1 > 7) return since <= 7 ? "최근 동향 요약" : "동향 요약";
  if (digest.from <= now && now <= digest.to) return "이번 주 요약";
  return since >= 1 && since <= 7 ? "지난주 요약" : "주간 요약";
}

// 요약의 근거가 된 소식의 목록. 누르면 그 소식의 국문 요약으로 간다.
function sources(digest, byId) {
  const found = (digest.itemIds || []).map((id) => byId.get(id)).filter((item) => item && !item.withdrawn);
  if (!found.length) return null;
  return h("div", { class: "quote-refs" }, [
    h("p", { text: `이 요약에 든 소식 ${found.length}건` }),
    h("ul", {}, found.map((item) => h("li", {}, h("a", { href: `#item-${item.id}`, text: item.title })))),
  ]);
}

export function digestPanel(digest, items) {
  if (!digest) return null;
  const byId = new Map(items.map((item) => [item.id, item]));
  const [first, ...rest] = digest.paragraphs || [];
  const refs = sources(digest, byId);
  const sameYear = digest.to.slice(0, 4) === digest.from.slice(0, 4);
  return h("section", { class: "quote", "aria-labelledby": "h-digest" }, [
    h("div", { class: "quote-head" }, [
      h("p", { class: "label" }, [icon("clock", 16), h("span", { text: digestName(digest) })]),
      h("h2", { id: "h-digest" }, unsplit(digest.title)),
      h("p", { class: "count", text: `${koreanDate(digest.from)} ~ ${koreanDate(digest.to, !sameYear)}` }),
    ]),
    h("div", { class: "quote-body" }, [
      first ? h("p", { text: first }) : null,
      rest.length || refs ? h("details", { class: "quote-rest" }, [
        h("summary", { text: "요약 이어서 읽기" }),
        ...rest.map((text) => h("p", { text })),
        refs,
      ]) : null,
    ]),
  ]);
}
