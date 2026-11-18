// PDF 나란히 보기의 문서 안 찾기. 쪽마다 글자를 읽어 낱말을 찾고, 그려 둔 쪽의 글자 층(pdf/sheets.js)에 찾은 곳을 칠한다.
// 쪽은 화면 가까이에 올 때만 그려지므로 브라우저의 찾기로는 보이는 쪽밖에 찾지 못한다. 그래서 문서 전체를 여기에서 찾는다.

const ALL = "pdf-find";       // 찾은 곳 모두에 칠하는 이름(CSS의 ::highlight)
const NOW = "pdf-find-now";   // 지금 가리키는 곳
const CAN_PAINT = typeof CSS !== "undefined" && Boolean(CSS.highlights) && typeof Highlight === "function";

// 쪽의 글자 조각들을 한 줄의 글로 잇는다. 견주기 좋게 소문자로 바꾸고 빈칸은 하나로 줄인다.
// 줄 끝의 붙임표로 나뉜 영문 낱말(imple- menting)은 이어 붙인다.
// 돌려주는 것: { text, at } — at[i]는 text의 i번째 글자가 [몇째 조각, 그 조각의 몇째 글자]인지.
export function flatten(items) {
  let text = "";
  const at = [];
  items.forEach((item, index) => {
    const str = typeof item.str === "string" ? item.str : "";
    for (let offset = 0; offset < str.length; offset += 1) {
      const char = str[offset];
      if (/\s/.test(char)) {
        if (text && !text.endsWith(" ")) { text += " "; at.push([index, offset]); }
      } else {
        text += char.toLowerCase()[0];   // 소문자로 바꾸면 글자 수가 늘어나는 드문 글자는 첫 글자만 쓴다
        at.push([index, offset]);
      }
    }
    if (!item.hasEOL) return;
    const next = items[index + 1];
    if (/[a-z]-$/.test(text) && next && /^[a-z]/.test(next.str || "")) {
      text = text.slice(0, -1);
      at.pop();
    } else if (text && !text.endsWith(" ")) {
      text += " ";
      at.push([index, str.length]);
    }
  });
  return { text, at };
}

// 찾을 말을 쪽의 글과 같은 꼴로
export function needle(query) {
  return String(query || "").toLowerCase().replace(/\s+/g, " ").trim();
}

// 한 쪽에서 찾은 곳들: [{ from: [조각, 자리], to: [조각, 끝 자리(그 글자는 들지 않는다)] }]
export function hits(flat, wanted) {
  const found = [];
  if (!wanted) return found;
  let start = flat.text.indexOf(wanted);
  while (start >= 0) {
    const last = flat.at[start + wanted.length - 1];
    found.push({ from: flat.at[start], to: [last[0], last[1] + 1] });
    start = flat.text.indexOf(wanted, start + wanted.length);
  }
  return found;
}

// 글자 층의 조각(span)이 쪽의 글자 조각과 같은 차례인지 맞춰, 조각 번호 → span을 돌려준다
function spans(layer) {
  if (layer.divs.length === layer.items.length) return (index) => layer.divs[index];
  const where = [];
  let cursor = 0;
  layer.items.forEach((item, index) => {
    while (cursor < layer.strs.length && layer.strs[cursor] !== item.str) cursor += 1;
    if (cursor < layer.strs.length) { where[index] = layer.divs[cursor]; cursor += 1; }
  });
  return (index) => where[index];
}

function rangeOf(layer, hit) {
  const span = spans(layer);
  const first = span(hit.from[0]);
  const last = span(hit.to[0]);
  const begin = first && first.firstChild;
  const end = last && last.firstChild;
  if (!begin || !end || begin.nodeType !== 3 || end.nodeType !== 3) return null;
  const range = document.createRange();
  range.setStart(begin, Math.min(hit.from[1], begin.length));
  range.setEnd(end, Math.min(hit.to[1], end.length));
  return range;
}

// pages는 sheets()가 돌려준 것, count는 문서의 쪽 수, sides()는 지금 화면에 보이는 쪽들(["en", "ko"] 등),
// onChange({ query, total, at, busy })는 찾은 수나 가리키는 곳이 바뀔 때, top()은 쪽이 가려지지 않는 화면 위쪽의 높이(px).
export function finder(pages, count, sides, onChange, top) {
  const flats = {};      // "en:3" → Promise<{ text, at }>
  let wanted = "";
  let found = [];        // [{ side, page, hit }] 쪽, 쪽 안의 차례대로
  let at = -1;
  let run = 0;           // 찾기를 새로 시작할 때마다 늘린다(앞의 찾기는 그만둔다)
  let busy = false;
  let reveal = false;    // 가리키는 곳이 그려지면 그리로 옮겨 가야 하는가

  const flat = (side, number) => {
    const key = `${side}:${number}`;
    if (!flats[key]) flats[key] = pages.words(side, number).then((content) => flatten(content.items));
    return flats[key];
  };
  const tell = () => onChange({ query: wanted, total: found.length, at, busy });

  function show(range) {
    const box = range.getBoundingClientRect();
    const head = top();
    if (box.top >= head + 12 && box.bottom <= window.innerHeight - 40) return;
    window.scrollBy({ top: box.top - (head + (window.innerHeight - head) * 0.3), behavior: "auto" });
  }

  // 그려 둔 쪽들에 찾은 곳을 칠한다. 글자 층이 새로 생기거나 사라질 때마다 다시 부른다.
  function paint() {
    const all = [];
    let now = null;
    document.querySelectorAll(".pdf-hit").forEach((span) => span.classList.remove("pdf-hit", "pdf-hit-now"));
    found.forEach((one, index) => {
      const layer = pages.layer(one.side, one.page);
      if (!layer) return;
      const range = rangeOf(layer, one.hit);
      if (!range) return;
      if (index === at) now = range; else all.push(range);
      if (!CAN_PAINT) {   // 칠하는 기능이 없는 브라우저에서는 조각째로 표시한다
        const span = range.startContainer.parentElement;
        span.classList.add("pdf-hit");
        if (index === at) span.classList.add("pdf-hit-now");
      }
    });
    if (CAN_PAINT) {
      CSS.highlights.set(ALL, new Highlight(...all));
      if (now) CSS.highlights.set(NOW, new Highlight(now)); else CSS.highlights.delete(NOW);
    }
    if (now && reveal) {
      reveal = false;
      show(now);
    }
  }

  function point(index) {
    if (!found.length) return;
    at = (index + found.length) % found.length;
    reveal = true;
    tell();
    const one = found[at];
    if (!pages.layer(one.side, one.page)) pages.go(one.page);   // 그 쪽이 그려지면 paint가 찾은 곳으로 옮긴다
    paint();
  }

  async function search(query) {
    const mine = (run += 1);
    wanted = needle(query);
    found = [];
    at = -1;
    busy = Boolean(wanted);
    reveal = false;
    tell();
    paint();
    if (!wanted) return;
    const looking = sides();
    let first = true;
    for (let number = 1; number <= count; number += 1) {
      const part = [];
      for (const side of looking) {
        let got = [];
        try {
          got = hits(await flat(side, number), wanted);   // eslint-disable-line no-await-in-loop
        } catch { got = []; }
        if (mine !== run) return;
        for (const hit of got) part.push({ side, page: number, hit });
      }
      if (part.length) {
        found = found.concat(part);
        if (first) { first = false; point(0); } else if (number % 8 === 0) tell();
      }
    }
    busy = false;
    tell();
    paint();
  }

  return {
    search,
    next() { point(at + 1); },
    previous() { point(at - 1); },
    paint,
    get total() { return found.length; },
    close() {
      run += 1;
      found = [];
      if (CAN_PAINT) { CSS.highlights.delete(ALL); CSS.highlights.delete(NOW); }
    },
  };
}
