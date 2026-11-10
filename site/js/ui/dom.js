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

export function table(headers, rows) {
  const head = h("thead", {}, h("tr", {}, headers.map((header) =>
    h("th", { scope: "col", class: header.num ? "num" : null, text: header.text || header }))));
  return h("div", { class: "table-wrap" }, h("table", {}, [head, h("tbody", {}, rows)]));
}

export function viewHead(title, lead) {
  return h("div", { class: "view-head" }, [h("h1", { text: title }), lead ? h("p", { text: lead }) : null]);
}
