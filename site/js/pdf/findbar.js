// PDF 나란히 보기의 도구 줄에 놓는 찾기 칸: 찾을 말, 찾은 수, 앞·다음 단추. 찾는 일은 pdf/find.js가 한다.
import { h } from "../ui/dom.js";
import { count } from "../ui/format.js";
import { icon } from "../ui/icons.js";
import { finder } from "./find.js";

const WAIT = 280;   // 글자를 치다 멈춘 뒤 찾기 시작하기까지(ms)

// pages는 sheets()가 돌려준 것, pageCount는 쪽 수, sides()는 지금 보이는 쪽들, top()은 도구 줄 아래 끝의 높이(px).
// 돌려주는 것: { node, again(): 보는 방식이 바뀐 뒤 다시 찾는다, focus(), close() }
export function findBar(pages, pageCount, sides, top) {
  const input = h("input", { id: "pdf-find", type: "search", placeholder: "문서 안에서 찾기", autocomplete: "off", enterkeyhint: "search", spellcheck: "false" });
  const tally = h("span", { class: "pdf-find-count", role: "status" });
  const before = h("button", { type: "button", class: "btn pdf-find-step", "data-way": "up", "aria-label": "앞의 찾은 곳", disabled: "" }, icon("next", 18));
  const after = h("button", { type: "button", class: "btn pdf-find-step", "data-way": "down", "aria-label": "다음 찾은 곳", disabled: "" }, icon("next", 18));
  const find = finder(pages, pageCount, sides, ({ query, total, at, busy }) => {
    tally.textContent = !query ? "" : total ? `${count(at + 1)} / ${count(total)}${busy ? " …" : ""}` : busy ? "찾는 중" : "없음";
    tally.dataset.state = query && !total && !busy ? "none" : "";
    before.disabled = total < 2;
    after.disabled = total < 2;
  }, top);
  pages.onLayers(() => find.paint());

  let timer = 0;
  let sought = null;   // 찾기에 넘긴 말
  const start = () => { clearTimeout(timer); timer = 0; sought = input.value; find.search(sought); };
  input.addEventListener("input", () => { clearTimeout(timer); timer = setTimeout(start, WAIT); });
  input.addEventListener("keydown", (event) => {
    if (event.key !== "Enter") return;
    event.preventDefault();
    // 치던 말이 아직 찾기에 넘어가지 않았으면 먼저 찾고, 이미 찾은 말이면 다음(Shift와 함께면 앞) 곳으로 간다
    if (input.value !== sought) start();
    else if (event.shiftKey) find.previous();
    else find.next();
  });
  before.addEventListener("click", () => find.previous());
  after.addEventListener("click", () => find.next());

  const node = h("label", { class: "field pdf-find", for: "pdf-find" }, [
    h("span", { text: "찾기" }),
    h("span", { class: "pdf-find-box" }, [input, tally, before, after]),
  ]);
  return {
    node,
    again() { if (input.value.trim()) start(); },
    focus() { input.focus(); input.select(); },
    close() { clearTimeout(timer); find.close(); },
  };
}
