// 조각 하나의 문단들을 그 꼴에 맞게 그린다: 문단, 작은 제목, 목록 항목, 표, 그림과 표의 제목, 각주, 그림 안의 이름표.
// 꼴은 자료의 shapes에 문단마다 적혀 있다(없으면 모두 문단이다).
// 표의 칸은 "th:표:줄:칸"이나 "td:표:줄:칸"이고, 칸 안에 든 목록 항목 같은 것은 뒤에 ":li1"처럼 붙는다.
// 문단의 줄에는 번호를 붙인다(id가 "b-<조각>-<몇 번째>"다). 주소로 문단 하나를 바로 가리키고(#law-…​.<조각>.<몇 번째>), 그 문단을 인용할 때 쓴다.
import { h } from "../ui/dom.js";
import { count } from "../ui/format.js";
import { split } from "./engine.js";

const CELL = /^t[hd]:/;

function marked(text, needles) {
  return needles.length ? split(text, needles).map(([piece, on]) => (on ? h("mark", { text: piece }) : piece)) : text;
}

function pair([en, ko], needles) {
  return [
    h("p", { class: "law-en", lang: "en" }, marked(en, needles)),
    ko ? h("p", { class: "law-ko" }, marked(ko, needles)) : h("p", { class: "law-ko law-wait" }, h("span", { class: "pill", text: "번역 준비 중" })),
  ];
}

// 꼴의 이름과 깊이: "li2" → ["li", "2"], "caption" → ["caption", null], "p" → [null, null]
function named(shape) {
  const hit = /^([a-z]+)(\d*)$/.exec(shape || "p");
  if (!hit || hit[1] === "p") return [null, null];
  return [hit[1], hit[1] === "li" && hit[2] ? hit[2] : null];
}

// where는 { id: 조각의 id, at: 조각 안에서의 차례(0부터), tool: 그 줄에 덧붙일 것을 만드는 함수 }다. 주지 않으면 번호 없는 줄이 된다(표와 그림 안의 줄).
function row(block, needles, shape, where) {
  const [name, depth] = named(shape);
  const extra = where && where.tool ? where.tool(where.at) : null;
  return h("div", { class: "law-row", id: where ? rowId(where.id, where.at) : null, "data-wait": block[1] ? null : "", "data-shape": name, "data-depth": depth },
    [...pair(block, needles), extra]);
}

// 문단의 줄에 붙는 id. at은 0부터 센 차례이고, 주소와 id에는 1부터 센 번호를 쓴다.
export function rowId(partId, at) {
  return `b-${partId}-${at + 1}`;
}

function table(blocks, shapes, needles) {
  const cells = new Map();  // "줄:칸" → { head, items, cols, rows }
  const lines = [];
  let width = 0;
  let spanned = false;
  blocks.forEach((block, at) => {
    const [kind, , line, column, inner, span] = shapes[at].split(":");
    const key = `${line}:${column}`;
    if (!cells.has(key)) {
      const [cols, deep] = span ? span.slice(1).split("x").map(Number) : [1, 1];
      cells.set(key, { head: kind === "th", items: [], cols, rows: deep });
      spanned = spanned || Boolean(span);
      width = Math.max(width, Number(column) + cols - 1);
      if (!lines.includes(Number(line))) lines.push(Number(line));
    }
    const [name, depth] = named(inner);
    cells.get(key).items.push(h("div", { class: "law-pair", "data-wait": block[1] ? null : "", "data-shape": name, "data-depth": depth }, pair(block, needles)));
  });
  const covered = new Set();  // 위나 왼쪽의 합쳐진 칸이 차지한 자리
  const body = lines.map((line) => {
    const made = [];
    let last = 0;
    for (let column = 1; column <= width; column += 1) if (cells.has(`${line}:${column}`)) last = column;
    for (let column = 1; column <= width; column += 1) {
      const key = `${line}:${column}`;
      if (covered.has(key)) continue;
      const cell = cells.get(key);
      if (!cell) {
        if (spanned || column < last) made.push(h("td", {}));
        continue;
      }
      // 합쳐진 칸의 정보가 없는 표에서 칸이 모자란 줄은 마지막 칸을 표의 끝까지 늘린다
      const cols = !spanned && column === last && last < width ? width - last + 1 : cell.cols;
      for (let down = 0; down < cell.rows; down += 1) for (let across = 0; across < cols; across += 1) covered.add(`${line + down}:${column + across}`);
      made.push(h(cell.head ? "th" : "td", { colspan: cols > 1 ? String(cols) : null, rowspan: cell.rows > 1 ? String(cell.rows) : null }, cell.items));
    }
    return h("tr", {}, made);
  });
  return h("div", { class: "law-table" }, h("table", {}, h("tbody", {}, body)));
}

function labels(blocks, needles) {
  return h("details", { class: "law-figure", open: needles.length ? "" : null }, [
    h("summary", {}, [h("span", { text: "그림 안의 글자" }), h("span", { class: "count", text: `${count(blocks.length)}개` })]),
    ...blocks.map((block) => row(block, needles, "figure", null)),
  ]);
}

// 조각의 문단들을 그린 것. needles는 찾은 낱말(그 낱말에 표시를 한다), tool은 문단의 줄마다 덧붙일 것을 만드는 함수(차례를 받는다. 없어도 된다)
export function rows(part, needles, tool = null) {
  const shapes = part.shapes || [];
  const made = [];
  let at = 0;
  while (at < part.blocks.length) {
    const shape = shapes[at] || "p";
    let end = at + 1;
    if (CELL.test(shape)) {
      const same = shape.split(":").slice(0, 2).join(":").replace(/^t[hd]/, "");  // 같은 표의 칸들을 한데 모은다
      while (end < part.blocks.length && CELL.test(shapes[end] || "") && shapes[end].split(":").slice(0, 2).join(":").replace(/^t[hd]/, "") === same) end += 1;
      made.push(table(part.blocks.slice(at, end), shapes.slice(at, end), needles));
    } else if (shape === "figure") {
      while (end < part.blocks.length && shapes[end] === "figure") end += 1;
      made.push(labels(part.blocks.slice(at, end), needles));
    } else {
      made.push(row(part.blocks[at], needles, shape, { id: part.id, at, tool }));
    }
    at = end;
  }
  return made;
}
