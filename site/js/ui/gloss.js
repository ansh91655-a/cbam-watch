// 글 속 용어 풀이. 글에 나온 용어(해설서가 풀이한 용어와 용어집의 약어)에 표시를 하고, 누르거나 마우스를 올리면 풀이를 보여 준다.
// 화면을 그린 뒤에 부른다: 글을 담은 요소들의 글자 사이에서 용어를 찾아 단추로 바꾼다. 글자는 바꾸지 않는다(찾기와 복사가 그대로 된다).
// 자료는 data/gloss.json(tools/publish/gloss.py), 찾는 셈은 js/gloss/match.js, 풀이 칸은 ui/glosstip.js, 모양은 css/gloss.css다.
import * as data from "../data.js";
import { compile, find } from "../gloss/match.js";
import { h } from "./dom.js";
import { closeTip, isOpenFor, openTip, tipHovered } from "./glosstip.js";

// 이 안의 글에는 표시하지 않는다: 링크와 단추(누르는 것 안에 누르는 것을 넣지 않는다), 제목, 원문 그대로의 영문
const SKIP = "a, button, h1, h2, h3, h4, code, [lang='en'], [data-nogloss]";
const HOVER_OPEN = 350;   // 마우스를 올리고 이만큼 머물러야 연다(글 위를 지나가는 마우스에 열리지 않게)
const HOVER_CLOSE = 220;  // 마우스가 떠난 뒤 이만큼 기다렸다 닫는다(용어에서 풀이 칸으로 옮겨 갈 틈)

let ready = null;
function book() {
  if (!ready) ready = data.gloss().then((body) => compile(body.terms || []));
  return ready;
}

// 마우스로 가리키는 기기에서만 올려서 연다(손가락으로 누르는 기기에서는 누를 때만 연다)
const canHover = () => typeof window.matchMedia === "function" && window.matchMedia("(hover: hover) and (pointer: fine)").matches;

function trigger(text, term) {
  let timer = 0;
  const button = h("button", { type: "button", class: "gloss", "aria-haspopup": "dialog", "aria-expanded": "false", text });
  button.addEventListener("click", () => {
    window.clearTimeout(timer);
    if (isOpenFor(button) && button.dataset.held) closeTip();   // 눌러서 연 것을 다시 누르면 닫는다
    else {
      button.dataset.held = "true";
      openTip(button, term, true);
    }
  });
  button.addEventListener("pointerenter", (event) => {
    if (event.pointerType !== "mouse" || !canHover() || isOpenFor(button)) return;
    window.clearTimeout(timer);
    timer = window.setTimeout(() => { delete button.dataset.held; openTip(button, term, false); }, HOVER_OPEN);
  });
  button.addEventListener("pointerleave", () => {
    window.clearTimeout(timer);
    if (button.dataset.held) return;   // 눌러서 연 것은 마우스가 떠나도 닫지 않는다
    timer = window.setTimeout(() => { if (isOpenFor(button) && !tipHovered() && !button.matches(":hover")) closeTip(false); }, HOVER_CLOSE);
  });
  return button;
}

// 요소 하나의 글자 사이에서 용어를 찾아 단추로 바꾼다
function decorate(block, found, seen, skip) {
  const walker = document.createTreeWalker(block, NodeFilter.SHOW_TEXT);
  const texts = [];
  for (let node = walker.nextNode(); node; node = walker.nextNode()) {
    const parent = node.parentElement;
    if (parent && !parent.closest(".gloss") && (!parent.closest(SKIP) || !block.contains(parent.closest(SKIP)))) texts.push(node);
  }
  for (const node of texts) {
    const text = node.data;
    const hits = find(text, found, seen, skip);
    if (!hits.length) continue;
    const pieces = [];
    let from = 0;
    for (const hit of hits) {
      if (hit.start > from) pieces.push(text.slice(from, hit.start));
      pieces.push(trigger(text.slice(hit.start, hit.end), found.terms[hit.at]));
      from = hit.end;
    }
    if (from < text.length) pieces.push(text.slice(from));
    node.replaceWith(...pieces);
  }
}

// root 안에서 selector에 맞는 요소들의 글에 표시한다. 한 번 부를 때마다 용어 하나는 처음 나온 곳에만 표시한다(글 한 편에 한 번).
// options.skip(용어): 참이면 그 용어를 표시하지 않는다(해설서의 절은 그 절이 스스로 풀이한 용어를 건너뛴다).
// 자료를 받지 못했거나 그사이에 화면이 바뀌었으면 아무것도 하지 않는다.
export async function gloss(root, selector, options = {}) {
  const found = await book();
  if (!found.regex || !root) return;
  const seen = new Set();
  for (const block of root.querySelectorAll(selector)) decorate(block, found, seen, options.skip || null);
}
