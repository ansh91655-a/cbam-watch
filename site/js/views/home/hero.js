// 첫 화면의 큰 머리. 왼쪽에 가장 최근의 요약(제목과 첫 문단, 나머지는 펼쳐서 읽는다), 오른쪽에 한국에서 EU로 가는 길을 그린 지도와 사이트 소개.
import { h } from "../../ui/dom.js";
import { koreanDate, today } from "../../ui/format.js";
import { heroMap } from "../../ui/heromap.js";

// 펼치지 않고 보여 주는 문단의 수. 첫 문단은 늘 보인다. 둘째 문단은 넓은 화면에서, 둘을 합쳐도 길지 않을 때만 보인다
// (큰 머리가 옆의 지도보다 길어지거나, 좁은 화면에서 아래의 수치와 조회가 멀어지지 않게 한다).
const SHOWN_CHARS = 300;
function shownCount(paragraphs) {
  if (paragraphs.length < 2 || window.matchMedia("(max-width: 979px)").matches) return 1;
  return paragraphs[0].length + paragraphs[1].length <= SHOWN_CHARS ? 2 : 1;
}
const ABOUT = "EU 탄소국경조정제도(CBAM)의 법령, 가이던스, 인증서 가격, 일정을 평일마다 확인해 원문과 함께 국문으로 정리합니다.";

// 가장 최근 주의 요약
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
  return h("div", { class: "hero-refs" }, [
    h("p", { text: `이 요약에 든 소식 ${found.length}건` }),
    h("ul", {}, found.map((item) => h("li", {}, h("a", { href: `#item-${item.id}`, text: item.title })))),
  ]);
}

function copy(digest, byId) {
  if (!digest) {
    return h("div", { class: "hero-copy" }, [
      h("h1", { id: "h-hero", text: "EU 탄소국경조정제도의 규제 동향을 원문과 함께" }),
      h("p", { class: "hero-lead", text: ABOUT }),
    ]);
  }
  const paragraphs = digest.paragraphs || [];
  const count = shownCount(paragraphs);
  const shown = paragraphs.slice(0, count);
  const rest = paragraphs.slice(count);
  const refs = sources(digest, byId);
  return h("div", { class: "hero-copy" }, [
    h("p", { class: "hero-kicker" }, [
      h("strong", { text: digestName(digest) }),
      h("span", { text: `${koreanDate(digest.from)} ~ ${koreanDate(digest.to, digest.to.slice(0, 4) !== digest.from.slice(0, 4))}` }),
    ]),
    h("h1", { id: "h-hero", text: digest.title }),
    ...shown.map((text) => h("p", { class: "hero-lead", text })),
    rest.length || refs ? h("details", { class: "hero-rest" }, [
      h("summary", { text: "요약 이어서 읽기" }),
      ...rest.map((text) => h("p", { text })),
      refs,
    ]) : null,
  ]);
}

// strip: 큰 머리의 맨 아래에 붙일 지표 줄
export function hero(digest, items, strip) {
  const byId = new Map(items.map((item) => [item.id, item]));
  return h("section", { class: "hero bleed", "aria-labelledby": "h-hero" }, h("div", { class: "hero-inner" }, [
    h("div", { class: "hero-top" }, [
      copy(digest, byId),
      h("figure", { class: "hero-figure" }, [
        heroMap(),
        h("figcaption", {}, [
          digest ? h("p", { class: "hero-about", text: ABOUT }) : null,
          h("p", { class: "hero-legend" }, [
            h("span", {}, [h("i", {}), "EU 회원국"]),
            h("span", {}, [h("i", { class: "kr" }), "한국"]),
            h("span", {}, [h("i", { class: "route" }), "CBAM 대상 제품이 EU로 수입되는 길"]),
          ]),
          h("p", { class: "hero-fresh", "data-fresh": "" }),
        ]),
      ]),
    ]),
    strip,
  ]));
}
