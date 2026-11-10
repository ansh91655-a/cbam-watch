// 소식 카드의 미리보기 그림.
// 원문 화면이나 문서 첫 장을 줄인 그림(item.thumb)이 있으면 그것을 종이처럼 얹어 보여 주고,
// 없으면 주제의 색과 아이콘으로 그린 그림을 보여 준다. 꾸밈이므로 읽어 주지 않는다.
import { h, safeLink } from "./dom.js";
import { icon } from "./icons.js";

function art(item, topic) {
  return [icon(topic, 34), item.sourceName ? h("span", { class: "thumb-src", text: item.sourceName }) : null];
}

export function thumb(item, topic) {
  const box = safeLink(item.link, "", { class: "thumb", tabindex: "-1", "aria-hidden": "true" }) || h("span", { class: "thumb", "aria-hidden": "true" });
  if (!item.thumb) {
    box.classList.add("thumb-art");
    box.append(...art(item, topic).filter(Boolean));
    return box;
  }
  box.classList.add("thumb-shot");
  box.append(h("img", {
    src: item.thumb, alt: "", loading: "lazy", decoding: "async", width: 480, height: 300,
    onerror: () => { // 그림을 받지 못하면 그린 그림으로 바꾼다
      box.classList.replace("thumb-shot", "thumb-art");
      box.replaceChildren(...art(item, topic).filter(Boolean));
    },
  }));
  return box;
}
