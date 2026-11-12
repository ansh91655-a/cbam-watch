// 화면 머리(제목과 설명 한 줄).
// 공개 사이트와 함께 쓰는 화면 도우미(dom.js)에 있던 것인데 사이트가 머리 띠로 바꾸면서 거기서 빠졌다.
// 사이트의 화면이 바뀌어도 운영 콘솔이 깨지지 않도록 콘솔이 따로 가진다.
import { h } from "./dom.js";

export function viewHead(title, lead) {
  return h("div", { class: "view-head" }, [h("h1", { text: title }), lead ? h("p", { text: lead }) : null]);
}
