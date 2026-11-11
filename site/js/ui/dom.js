// 화면 요소를 만드는 작은 도우미. 데이터는 항상 textContent로 넣어 글 안의 태그가 실행되지 않게 한다.

export function h(tag, attrs = {}, children = []) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (value === null || value === undefined || value === false) continue;
    if (key === "text") node.textContent = String(value);
    else if (key === "class") node.className = value;
    else if (key.startsWith("on") && typeof value === "function") node.addEventListener(key.slice(2), value);
    else node.setAttribute(key, value === true ? "" : String(value));
  }
  for (const child of [].concat(children)) {
    if (child) node.append(child);
  }
  return node;
}

// 제목에 쓴다: 가운뎃점(·)으로 이어진 낱말("확대·우회방지")이 줄 끝에서 갈라지지 않게 묶은 자식들을 돌려준다.
// 글자는 바꾸지 않는다(화면에서 찾기와 복사가 그대로 된다). 묶음이 너무 길면 좁은 화면에서 넘칠 수 있어 그대로 둔다.
const UNSPLIT_MAX = 14;
export function unsplit(text) {
  const whole = String(text || "");
  if (!whole.includes("·")) return [whole];
  return whole.split(/(\s+)/).map((part) => (part.includes("·") && part.length <= UNSPLIT_MAX ? h("span", { class: "nb", text: part }) : part));
}

// 요소의 자식을 통째로 바꾼다. 빈 값(null, false)은 건너뛴다(그냥 넣으면 "null"이라는 글자가 찍힌다).
export function fill(node, ...children) {
  node.replaceChildren(...children.flat().filter(Boolean));
  return node;
}

// http(s) 주소만 링크로 만든다(이 사이트 안의 주소는 사이트 주소에 이어 붙인다). 그 밖의 값이면 null.
export function safeLink(url, text, attrs = {}) {
  try {
    if (!url) return null;
    const parsed = new URL(String(url), document.baseURI);
    if (parsed.protocol !== "https:" && parsed.protocol !== "http:") return null;
    return h("a", { href: parsed.href, rel: "noopener", target: "_blank", text, ...attrs });
  } catch (error) {
    return null;
  }
}

export function pill(text, tone) {
  return h("span", { class: "pill", "data-tone": tone || null, text });
}

export function empty(text) {
  return h("p", { class: "empty", text });
}

// 좁은 화면에서는 표가 옆으로 넘어가 감싼 칸을 옆으로 밀어 본다. 자판으로도 밀 수 있게, 넘칠 때에는 그 칸에 초점이 가도록 한다.
// 넘치지 않을 때에는 초점이 멈출 까닭이 없으므로 뺀다.
function focusWhenScrollable(node) {
  const set = () => { if (node.scrollWidth > node.clientWidth + 1) node.tabIndex = 0; else node.removeAttribute("tabindex"); };
  if (typeof ResizeObserver === "function") new ResizeObserver(set).observe(node);
  else node.tabIndex = 0;
}

export function table(headers, rows, name) {
  const head = h("thead", {}, h("tr", {}, headers.map((header) =>
    h("th", { scope: "col", class: header.num ? "num" : null, text: header.text || header }))));
  const wrap = h("div", { class: "table-wrap", role: "group", "aria-label": name || "표" }, h("table", {}, [head, h("tbody", {}, rows)]));
  focusWhenScrollable(wrap);
  return wrap;
}
