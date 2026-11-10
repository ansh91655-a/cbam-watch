// 소식 카드의 미리보기 그림. 원문 화면(법령은 PDF 첫 장)의 윗부분을 줄인 그림(item.thumb)이 있으면 그대로 보여 주고,
// 없으면 주제 아이콘과 출처 이름을 적는다. 꾸밈이므로 읽어 주지 않는다.
import { h, safeLink } from "./dom.js";
import { icon } from "./icons.js";
import { hasPage } from "./itemlink.js";
import { topicName } from "./topics.js";

function drawn(box, item, topic) {
  box.classList.add("thumb-art");
  box.replaceChildren(
    h("span", { class: "thumb-mark" }, icon(topic, 32)),
    h("span", { class: "thumb-src", text: item.sourceName || item.kind || topicName(topic) }),
  );
}

export function thumb(item, topic) {
  // 그림을 눌러도 제목을 누른 것과 같은 곳으로 간다(국문 요약 화면, 한 줄 소식은 원문).
  const box = (hasPage(item) ? h("a", { class: "thumb", href: `#item-${item.id}`, tabindex: "-1", "aria-hidden": "true" }) : safeLink(item.link, "", { class: "thumb", tabindex: "-1", "aria-hidden": "true" }))
    || h("span", { class: "thumb", "aria-hidden": "true" });
  if (!item.thumb) {
    drawn(box, item, topic);
    return box;
  }
  box.classList.add("thumb-shot");
  box.dataset.kind = item.thumbKind === "pdf" ? "pdf" : "page";
  box.append(h("img", {
    src: item.thumb, alt: "", loading: "lazy", decoding: "async", width: 480, height: 300,
    onerror: () => { // 그림을 받지 못하면 그린 그림으로 바꾼다
      box.classList.remove("thumb-shot");
      delete box.dataset.kind;
      drawn(box, item, topic);
    },
  }));
  return box;
}
