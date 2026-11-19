// 소식 카드의 미리보기 그림. 모든 그림은 주제 색을 짙게 깐 같은 바탕을 쓴다.
// 원문 화면을 줄인 그림(item.thumb)이 있으면 그 위에 창처럼(법령 PDF의 첫 장은 종이처럼) 얹고,
// 없으면 주제 아이콘을 크게 깔고 종류와 출처 이름을 적는다. 꾸밈이므로 읽어 주지 않는다.
import { h, safeLink } from "./dom.js";
import { icon } from "./icons.js";
import { hasPage } from "./itemlink.js";
import { topicName } from "./topics.js";

function drawn(box, item, topic) {
  box.classList.add("thumb-art");
  box.replaceChildren(...[
    h("span", { class: "thumb-mark" }, icon(topic, 96)),
    h("span", { class: "thumb-kind", text: item.kind || topicName(topic) }),
    item.sourceName ? h("span", { class: "thumb-src", text: item.sourceName }) : null,
  ].filter(Boolean));
}

export function thumb(item, topic) {
  // 제목과 같은 곳으로 간다: 국문 요약 화면이 있는 소식은 그 화면, 한 줄 소식은 원문.
  const attrs = { class: "thumb", tabindex: "-1", "aria-hidden": "true" };
  const box = (hasPage(item) ? h("a", { href: `#item-${item.id}`, ...attrs }) : safeLink(item.link, "", attrs)) || h("span", { class: "thumb", "aria-hidden": "true" });
  if (!item.thumb) {
    drawn(box, item, topic);
    return box;
  }
  const paper = item.thumbKind === "pdf";
  box.classList.add("thumb-shot");
  box.dataset.kind = paper ? "pdf" : "page";
  box.append(h("span", { class: "thumb-frame" }, [
    paper ? null : h("span", { class: "thumb-bar" }, [h("i"), h("i"), h("i")]),
    h("img", {
      src: item.thumb, alt: "", loading: "lazy", decoding: "async", width: 480, height: 300,
      onerror: () => { // 그림을 받지 못하면 그린 그림으로 바꾼다
        box.classList.remove("thumb-shot");
        delete box.dataset.kind;
        drawn(box, item, topic);
      },
    }),
  ]));
  return box;
}
