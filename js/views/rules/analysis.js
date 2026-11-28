// 규제 하나의 분석 글: 배경, 주요 내용, 쟁점과 정세, 실무에서 볼 점.
// 문단마다 근거 자료의 번호를 달고 끝에 자료 목록을 둔다. 번호를 누르면 그 자료로 내려가 잠깐 표시한다.
// 규제의 단계나 연혁이 분석을 쓴 뒤에 달라졌으면(stale) 그렇다고 먼저 밝힌다.
// 절의 이름을 적은 줄(an-nav)은 글을 읽는 동안 머리글 아래에 붙어 있고, 지금 읽는 절의 이름이 강조된다.
import { h, moreHint, safeLink } from "../../ui/dom.js";
import { koreanDate } from "../../ui/format.js";
import { icon } from "../../ui/icons.js";

const FLASH_MS = 1800;

// 화면 주소(#…)를 바꾸지 않고 그 자리로 옮긴다(주소가 바뀌면 다른 화면으로 넘어간다).
function goTo(node, block = "center") {
  if (!node) return;
  node.scrollIntoView({ block, behavior: "smooth" });
  node.dataset.flash = "true";
  window.setTimeout(() => { delete node.dataset.flash; }, FLASH_MS);
}

// 문단 끝의 근거 번호들
function marks(refs, numbers, root) {
  const known = (refs || []).filter((key) => numbers.has(key));
  if (!known.length) return null;
  return h("span", { class: "an-refs" }, known.map((key) => {
    const { number, name } = numbers.get(key);
    return h("button", {
      type: "button", class: "an-ref", title: name, "aria-label": `근거 자료 ${number}: ${name}`, text: number,
      onclick: () => goTo(root().querySelector(`[data-source="${number}"]`)),
    });
  }));
}

function section(part, numbers, root) {
  const labelled = part.items.some((item) => item.label);
  // 이름이 붙은 문단이 하나라도 있으면 두 단(이름, 글)으로 놓는다. 그 절에서 이름이 없는 문단은 단을 가로질러 놓는다.
  const body = part.items.map((item) => {
    const text = h("p", {}, [item.text, marks(item.refs, numbers, root)]);
    if (!labelled) return text;
    return item.label ? h("div", { class: "an-point" }, [h("h4", { text: item.label }), text]) : h("div", { class: "an-point an-lead" }, text);
  });
  return h("section", { class: "an-sec", "data-part": part.key, "aria-labelledby": `h-an-${part.key}` }, [
    h("h3", { id: `h-an-${part.key}`, text: part.title }),
    h("div", { class: labelled ? "an-points" : "an-prose" }, body),
  ]);
}

function sources(list) {
  return h("section", { class: "an-sec an-src", "aria-labelledby": "h-an-src" }, [
    h("h3", { id: "h-an-src", text: "근거 자료" }),
    h("ol", {}, list.map((source, index) => {
      const link = safeLink(source.url, source.text) || h("span", { text: source.text });
      if (link.tagName === "A") link.append(icon("out", 13));
      return h("li", { "data-source": index + 1 }, [link, source.press ? h("span", { class: "tl-press", text: "언론 보도" }) : null]);
    })),
  ]);
}

// 지금 읽는 절을 알아내 그 이름의 단추를 강조한다. 화면의 위쪽 3분의 1 언저리를 지나는 절을 읽는 중으로 본다.
function follow(holder) {
  if (typeof IntersectionObserver !== "function") return;
  const buttons = new Map([...holder.querySelectorAll(".an-nav button")].map((button) => [button.dataset.to, button]));
  const inView = new Set();
  const spy = new IntersectionObserver((entries) => {
    if (!holder.isConnected) {
      spy.disconnect();
      return;
    }
    for (const entry of entries) {
      if (entry.isIntersecting) inView.add(entry.target.dataset.part);
      else inView.delete(entry.target.dataset.part);
    }
    // 띠에 걸친 절이 둘이면 문서에서 뒤에 있는 것(막 들어온 것)을 읽는 중으로 본다
    const now = [...buttons.keys()].filter((key) => inView.has(key)).pop();
    for (const [key, button] of buttons) {
      if (key === now) button.setAttribute("aria-current", "true");
      else button.removeAttribute("aria-current");
    }
  }, { rootMargin: "-30% 0px -62% 0px" });
  for (const part of holder.querySelectorAll(".an-sec[data-part]")) spy.observe(part);
}

// 분석 글이 없는 규제면 null
export function analysis(rule) {
  const book = rule.analysis;
  if (!book || !Array.isArray(book.sections) || !book.sections.length) return null;
  const numbers = new Map((book.sources || []).map((source, index) => [source.key, { number: index + 1, name: source.text }]));
  let holder = null;
  const root = () => holder;
  holder = h("div", { class: "rule-analysis" }, [
    book.stale ? h("p", { class: "an-stale" }, [icon("clock", 16), h("span", { text: "이 분석을 쓴 뒤에 이 규제의 단계나 연혁이 달라졌습니다. 가장 새로운 내용은 위의 '현재 상황'과 아래의 연혁에 있습니다." })]) : null,
    moreHint(h("div", { class: "an-nav", role: "group", "aria-label": "분석의 절" }, book.sections.map((part) => h("button", {
      type: "button", text: part.title, "data-to": part.key, onclick: () => goTo(holder.querySelector(`[data-part="${part.key}"] h3`), "start"),
    })))),
    ...book.sections.map((part) => section(part, numbers, root)),
    (book.sources || []).length ? sources(book.sources) : null,
    h("p", { class: "an-foot", text: `${koreanDate(book.asOf)} 기준으로 쓴 분석입니다. 원문을 바탕으로 정리한 참고 자료이므로, 정확한 내용은 근거 자료의 원문에서 확인해 주세요.` }),
  ]);
  follow(holder);
  return holder;
}
