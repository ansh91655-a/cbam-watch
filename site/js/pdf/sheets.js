// 원문 PDF와 번역 PDF의 쪽을 한 줄에 하나씩 나란히 그린다(PDF.js).
// 두 파일은 쪽 수와 쪽의 크기가 같으므로 한 번의 스크롤로 같은 자리를 함께 본다.
// 화면 가까이에 온 줄만 그리고, 멀어진 줄의 그림은 내려놓는다(쪽이 많은 문서에서도 기억을 적게 쓴다).
// 쪽의 그림 위에는 눈에 보이지 않는 글자 층을 얹는다. 그 글자를 끌어서 고르고 복사할 수 있고, 문서 안 찾기(pdf/find.js)가 찾은 곳을 거기에 칠한다.
import { h } from "../ui/dom.js";

const BASE = new URL("../../vendor/pdfjs/", import.meta.url);
const NEAR = "120% 0px";   // 화면 위아래로 이만큼은 미리 그려 둔다
const KEEP = 10;           // 그려 둔 채로 두는 줄 수
const SHARP = 2;           // 화면 점 하나에 그리는 점 수의 한도
const WIDEST = 1800;       // 그림 하나의 너비 한도(점)
const SIDES = { en: "원문", ko: "번역" };
let engine = null;

function library() {
  if (!engine) {
    engine = import(new URL("pdf.min.js", BASE).href).then((pdfjs) => {
      pdfjs.GlobalWorkerOptions.workerSrc = new URL("pdf.worker.min.js", BASE).href;
      return pdfjs;
    });
  }
  return engine;
}

// 사이트 안의 경로를 주소로(파일 이름의 빈칸과 기호를 싼다)
export function address(path) {
  return String(path).split("/").map(encodeURIComponent).join("/");
}

async function open(path) {
  const pdfjs = await library();
  const task = pdfjs.getDocument({ url: address(path), wasmUrl: new URL("wasm/", BASE).href, standardFontDataUrl: new URL("standard_fonts/", BASE).href, isEvalSupported: false });
  return { task, file: await task.promise };
}

// entry는 목록의 한 줄({ en, ko, pages, size, odd }), state는 { mode: "both" | "en" | "ko" }.
// 돌려주는 것: { node, refresh(): 크기나 보는 방식이 바뀐 뒤 다시 그린다, go(쪽), page(): 지금 보는 쪽, close(),
//   words(쪽, 번호): 그 쪽의 글자 조각들, layer(쪽, 번호): 그려 둔 글자 층({ node, divs, strs }), onLayers(부를 것): 글자 층이 생기거나 사라질 때 부른다 }
export function sheets(entry, state, onFail) {
  const files = {};
  const rows = [];
  const drawn = [];       // 그려 둔 줄(오래된 것부터)
  const read = {};        // 읽어 둔 글자 조각: "en:3" → Promise
  let closed = false;
  let layersChanged = () => {};

  const file = (side) => {
    if (!files[side]) {
      files[side] = open(entry[side]);
      files[side].catch((error) => { if (!closed) onFail(side, error); });
    }
    return files[side].then((opened) => opened.file);
  };

  for (let number = 1; number <= entry.pages; number += 1) {
    const [width, height] = (entry.odd || {})[String(number)] || entry.size;
    const boxes = Object.fromEntries(Object.entries(SIDES).map(([side, name]) => [side,
      h("div", { class: "pdf-sheet", "data-side": side, style: `aspect-ratio: ${width} / ${height}`, role: "group", "aria-label": `${name} ${number}쪽` })]));
    const node = h("div", { class: "pdf-row", "data-page": String(number), id: `pdf-p${number}` }, [boxes.en, boxes.ko]);
    rows.push({ number, node, boxes, tasks: {}, texts: {}, layers: {}, near: false });
  }
  const node = h("div", { class: "pdf-pages" }, rows.map((row) => row.node));

  // 그 쪽의 글자 조각들(PDF.js의 textContent). 한 번 읽은 것은 그대로 둔다(찾기와 글자 층이 함께 쓴다)
  const words = (side, number) => {
    const key = `${side}:${number}`;
    if (!read[key]) read[key] = file(side).then((opened) => opened.getPage(number)).then((page) => page.getTextContent());
    return read[key];
  };

  function release(row) {
    let had = false;
    for (const side of Object.keys(SIDES)) {
      if (row.tasks[side]) row.tasks[side].cancel();
      if (row.texts[side]) row.texts[side].cancel();
      had = had || Boolean(row.layers[side]);
      row.tasks[side] = null;
      row.texts[side] = null;
      row.layers[side] = null;
      row.boxes[side].replaceChildren();
      delete row.boxes[side].dataset.scale;
    }
    if (had) layersChanged();
  }

  // 번역 PDF의 글자는 사이트와 같은 글꼴(Pretendard)로 찍혀 있다. 글자 층도 그 글꼴로 놓아야 낱말의 자리가 그림과 맞는다.
  // 글꼴은 쓰이는 글자의 묶음만 받아 오므로, 이 쪽의 글자에 필요한 묶음을 먼저 받는다(받지 못하면 브라우저의 글꼴로 놓인다).
  async function inSiteFont(content) {
    const family = getComputedStyle(document.documentElement).getPropertyValue("--font").trim();
    if (!family) return content;
    const text = content.items.map((item) => item.str || "").join("").slice(0, 6000);
    try { await document.fonts.load(`16px ${family}`, text); } catch { return content; }
    return { ...content, styles: Object.fromEntries(Object.entries(content.styles || {}).map(([name, style]) => [name, { ...style, fontFamily: family }])) };
  }

  // 쪽의 그림 위에 글자 층을 얹는다. 글자는 보이지 않고(그림의 글자와 같은 자리에 놓인다) 고르고 복사할 수 있다
  async function write(row, side, page, base, width) {
    const box = row.boxes[side];
    const pdfjs = await library();
    const got = await words(side, row.number);
    const content = side === "ko" ? await inSiteFont(got) : got;
    if (closed || !row.near || !box.firstChild) return;
    const unit = width / base.width;   // PDF의 1pt가 화면의 몇 px인가
    box.style.setProperty("--total-scale-factor", unit.toFixed(4));
    // 글자 층의 언어를 적어 둔다. PDF.js는 조각의 너비를 이 언어로 재는데, 브라우저는 언어에 따라 serif 같은 글꼴 이름을 다른 글꼴로 푼다.
    // 화면의 언어(한국어)를 그대로 물려받으면 잰 글꼴과 놓인 글꼴이 달라져 영문 조각이 그림의 글자보다 넓게 놓인다.
    const lang = side === "ko" ? "ko" : "en";
    const node = h("div", { class: "textLayer pdf-text", lang });
    const text = new pdfjs.TextLayer({ textContentSource: { ...content, lang }, container: node, viewport: page.getViewport({ scale: unit }) });
    if (row.texts[side]) row.texts[side].cancel();
    row.texts[side] = text;
    await text.render();
    if (row.texts[side] !== text || closed) return;
    box.querySelector(".pdf-text")?.remove();
    box.append(node);
    row.layers[side] = { node, divs: text.textDivs || [...node.querySelectorAll("span")], strs: text.textContentItemsStr || [], items: content.items };
    layersChanged();
  }

  async function draw(row, side) {
    const box = row.boxes[side];
    const width = box.clientWidth;
    if (!width || closed) return;   // 감춰 둔 쪽(보는 방식)은 그리지 않는다
    try {
      const page = await (await file(side)).getPage(row.number);
      const base = page.getViewport({ scale: 1 });
      const sharp = Math.min(window.devicePixelRatio || 1, SHARP, WIDEST / width);
      const scale = (width * sharp) / base.width;
      const key = scale.toFixed(4);
      if (box.dataset.scale === key || closed || !row.near) return;
      if (row.tasks[side]) row.tasks[side].cancel();
      const viewport = page.getViewport({ scale });
      const canvas = h("canvas", { width: String(Math.round(viewport.width)), height: String(Math.round(viewport.height)), "aria-hidden": "true" });
      const task = page.render({ canvas, canvasContext: canvas.getContext("2d"), viewport });
      row.tasks[side] = task;
      await task.promise;
      if (row.tasks[side] !== task || closed) return;
      row.tasks[side] = null;
      row.layers[side] = null;
      box.replaceChildren(canvas);
      box.dataset.scale = key;
      // 글자 층은 그림이 보인 뒤에 따로 얹는다. 얹지 못해도 그림은 그대로 보인다
      write(row, side, page, base, width).catch((error) => { if (!error || error.name !== "AbortException") box.dataset.plain = ""; });
    } catch (error) {
      if (error && error.name === "RenderingCancelledException") return;
      box.dataset.failed = "";
    }
  }

  function show(row) {
    if (!drawn.includes(row)) drawn.push(row);
    while (drawn.length > KEEP) {
      const far = drawn.findIndex((other) => !other.near);
      if (far < 0) break;
      release(drawn.splice(far, 1)[0]);
    }
    for (const side of Object.keys(SIDES)) if (state.mode === "both" || state.mode === side) draw(row, side);
  }

  const watcher = new IntersectionObserver((entries) => {
    for (const seen of entries) {
      const row = rows[Number(seen.target.dataset.page) - 1];
      row.near = seen.isIntersecting;
      if (row.near) show(row);
    }
  }, { rootMargin: NEAR });
  for (const row of rows) watcher.observe(row.node);

  return {
    node,
    refresh() { for (const row of rows) if (row.near) show(row); },
    go(number) {
      const row = rows[Math.min(Math.max(1, number), rows.length) - 1];
      if (row) row.node.scrollIntoView({ block: "start" });
    },
    // 화면의 line 높이(위에서부터의 px)에 걸린 쪽
    page(line) {
      let low = 0;
      let high = rows.length - 1;
      while (low < high) {
        const middle = (low + high) >> 1;
        if (rows[middle].node.getBoundingClientRect().bottom > line) high = middle;
        else low = middle + 1;
      }
      return rows[low] ? rows[low].number : 1;
    },
    words,
    layer(side, number) { const row = rows[number - 1]; return row ? row.layers[side] : null; },
    onLayers(call) { layersChanged = call; },
    close() {
      closed = true;
      layersChanged = () => {};
      watcher.disconnect();
      for (const row of rows) release(row);
      for (const opened of Object.values(files)) opened.then(({ task }) => task.destroy()).catch(() => {});
    },
  };
}
