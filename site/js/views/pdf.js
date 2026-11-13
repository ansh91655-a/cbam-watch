// 문서 하나의 원문 PDF와 번역 PDF를 쪽마다 나란히 보는 화면. #pdf-<문서 id>.p<쪽> 꼴의 주소로 쪽을 바로 가리킬 수 있다.
// 번역 PDF는 원문과 같은 쪽, 같은 자리에 번역을 앉힌 것이라 한 번의 스크롤로 두 쪽을 함께 본다.
import * as data from "../data.js";
import { address, sheets } from "../pdf/sheets.js";
import { band } from "../ui/band.js";
import { empty, fill, h } from "../ui/dom.js";
import { bytes, count } from "../ui/format.js";
import { icon } from "../ui/icons.js";
import { groupTabs } from "../ui/tabs.js";

const MODES = [["both", "나란히"], ["en", "원문"], ["ko", "번역"]];
const ZOOMS = [0.75, 1, 1.25, 1.5, 2];
const NARROW = "(max-width: 760px)";
const NOTE = "번역 PDF는 이 사이트가 원문과 같은 자리에 번역을 앉혀 만든 비공식 자료입니다. 아직 옮기지 않은 문단과 일부 그림 안의 글자, 머리말·꼬리말은 원문 그대로입니다.";
const TITLE = "PDF 나란히 보기";
let open = null;  // 지금 열어 둔 것. 화면을 떠나면 닫는다

function close() {
  if (!open) return;
  open.pages.close();
  window.removeEventListener("scroll", open.onScroll);
  window.removeEventListener("resize", open.onResize);
  window.removeEventListener("hashchange", open.onLeave);
  open = null;
}

export async function render(main, arg) {
  const [id, at = ""] = String(arg || "").split(".");
  close();
  const [acts, docs] = await Promise.all([data.laws(), data.pdfs()]);
  const act = acts.find((one) => one.id === id);
  const entry = docs[id];
  if (!act || !entry) {
    fill(main, band(TITLE, "", groupTabs("laws")), empty("이 문서의 PDF를 찾지 못했습니다."),
      h("p", {}, h("a", act ? { href: `#law-${id}`, text: "이 문서를 글로 보기" } : { href: "#laws", text: "규정 원문의 목록으로" })));
    return TITLE;
  }
  document.body.dataset.wide = "";
  const state = { mode: window.matchMedia(NARROW).matches ? "ko" : "both", zoom: 1 };
  const failed = h("p", { class: "pdf-failed", role: "alert", hidden: "" });
  const pages = sheets(entry, state, (side) => {
    failed.textContent = `${side === "en" ? "원문" : "번역"} PDF를 불러오지 못했습니다. 아래의 내려받기 링크로 파일을 열어 보실 수 있습니다.`;
    failed.hidden = false;
  });
  // 보는 방식과 크기는 이 틀에 적어 두고 꾸밈이 따라간다
  const frame = h("div", { class: "pdf-view", "data-mode": state.mode, style: "--pdf-zoom: 1" }, [
    h("div", { class: "pdf-heads", "aria-hidden": "true" }, [h("span", { "data-side": "en", text: "원문" }), h("span", { "data-side": "ko", text: "번역(비공식)" })]),
    h("div", { class: "pdf-frame" }, pages.node),
  ]);

  const modes = MODES.map(([key, text]) => h("button", { type: "button", text, "aria-pressed": String(key === state.mode), onclick: () => {
    const number = pages.page(bar.getBoundingClientRect().bottom + 8);
    state.mode = key;
    frame.dataset.mode = key;
    modes.forEach((button, index) => button.setAttribute("aria-pressed", String(MODES[index][0] === key)));
    pages.go(number);
    pages.refresh();
  } }));
  const zoomText = h("span", { class: "pdf-zoom", "aria-live": "polite", text: "100%" });
  const zoom = (step) => {
    const index = Math.min(ZOOMS.length - 1, Math.max(0, ZOOMS.indexOf(state.zoom) + step));
    if (ZOOMS[index] === state.zoom) return;
    const number = pages.page(bar.getBoundingClientRect().bottom + 8);
    state.zoom = ZOOMS[index];
    frame.style.setProperty("--pdf-zoom", String(state.zoom));
    zoomText.textContent = `${Math.round(state.zoom * 100)}%`;
    pages.go(number);
    pages.refresh();
  };
  const pick = h("input", { id: "pdf-page", type: "number", min: "1", max: String(entry.pages), value: "1", inputmode: "numeric", onchange: (event) => pages.go(Number(event.target.value) || 1) });
  const jump = (number) => {
    const page = Math.min(Math.max(1, number), entry.pages);
    pick.value = String(page);
    pages.go(page);
  };
  const bar = h("div", { class: "pdf-bar" }, [
    h("div", { class: "field" }, [h("span", { text: "보는 방식" }), h("div", { class: "seg", role: "group", "aria-label": "보는 방식" }, modes)]),
    h("div", { class: "field" }, [h("span", { text: "크기" }), h("div", { class: "pdf-zooms" }, [
      h("button", { type: "button", class: "btn", "aria-label": "작게", text: "−", onclick: () => zoom(-1) }), zoomText,
      h("button", { type: "button", class: "btn", "aria-label": "크게", text: "+", onclick: () => zoom(1) })])]),
    h("label", { class: "field", for: "pdf-page" }, [h("span", { text: "쪽" }), h("span", { class: "pdf-pick" }, [pick, h("span", { text: `/ ${count(entry.pages)}` })])]),
  ]);

  fill(main,
    band(act.name, `${act.official || ""}${act.official ? ", " : ""}${count(entry.pages)}쪽`, groupTabs("laws")),
    h("p", { class: "crumbs" }, [h("a", { href: "#laws", text: "규정 원문" }), h("span", { text: "›" }), h("a", { href: `#law-${id}`, text: act.name }), h("span", { text: "›" }), h("span", { text: TITLE })]),
    h("div", { class: "law-note" }, [
      h("p", { text: NOTE }),
      h("p", { class: "law-note-links" }, [
        h("a", { href: `#law-${id}`, text: "글로 보기(문단마다 원문과 번역)" }),
        h("a", { href: address(entry.en), target: "_blank", rel: "noopener nofollow", text: `원문 PDF 열기(${bytes(entry.enBytes)})` }),
        h("a", { href: address(entry.ko), target: "_blank", rel: "noopener nofollow", text: `번역 PDF 열기(${bytes(entry.koBytes)})` }),
      ]),
    ]),
    bar, failed, frame,
  );
  for (const link of main.querySelectorAll(".law-note-links a[target]")) link.append(icon("out", 14));

  let waiting = 0;
  const onScroll = () => {
    if (waiting) return;
    waiting = requestAnimationFrame(() => {
      waiting = 0;
      if (document.activeElement !== pick) pick.value = String(pages.page(bar.getBoundingClientRect().bottom + 8));
    });
  };
  // 도구 줄은 사이트 머리 아래에 붙어 있고, 쪽으로 옮겨 갈 때는 그 아래에서 멈춘다
  const place = () => {
    const head = document.querySelector(".site-head");
    const top = head ? head.offsetHeight : 0;
    bar.style.top = `${top + 6}px`;
    frame.style.setProperty("--pdf-top", `${top + bar.offsetHeight + 18}px`);
  };
  place();
  let resized = 0;
  const onResize = () => { clearTimeout(resized); resized = setTimeout(() => { place(); pages.refresh(); }, 200); };
  const onLeave = () => { if (!location.hash.startsWith(`#pdf-${id}`)) close(); };
  window.addEventListener("scroll", onScroll, { passive: true });
  window.addEventListener("resize", onResize);
  window.addEventListener("hashchange", onLeave);
  open = { pages, onScroll, onResize, onLeave };

  const first = /^p(\d+)$/.exec(at);
  if (first) {
    // 화면 위쪽이 마저 그려지면 쪽이 밀리므로, 그사이에 스크롤하지 않았으면 한 번 더 맞춘다
    setTimeout(() => {
      jump(Number(first[1]));
      const from = window.scrollY;
      setTimeout(() => { if (open && open.pages === pages && Math.abs(window.scrollY - from) < 4) jump(Number(first[1])); }, 500);
    }, 0);
  }
  return `${act.name} ${TITLE}`;
}
