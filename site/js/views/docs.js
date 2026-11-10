// 원문 대장. EU 집행위원회가 올린 문서의 목록이다. 문서 이름을 누르면 파일을 내려받는다.
// 문서가 바뀌어 판이 둘 이상이면 바뀐 곳과 이전 판을 볼 수 있다.
import * as data from "../data.js";
import { band } from "../ui/band.js";
import { empty, fill, h, pill, safeLink } from "../ui/dom.js";
import { bytes, count } from "../ui/format.js";
import { icon } from "../ui/icons.js";
import { libraryTabs } from "../ui/tabs.js";

const LABEL = { added: "더해짐", removed: "빠짐", changed: "바뀜" };

function diffView(result) {
  if (!result) return empty("비교 결과를 읽지 못했습니다.");
  const stats = result.stats || {};
  return h("div", { class: "diff" }, [
    h("p", { class: "count", text: `${result.fromDate} 판과 ${result.toDate} 판의 비교: 바뀜 ${stats.changed || 0}, 더해짐 ${stats.added || 0}, 빠짐 ${stats.removed || 0}${result.truncated ? " (앞부분만 표시)" : ""}` }),
    ...(result.blocks || []).map((block) => h("div", { class: "diff-block", "data-op": block.op }, [
      h("span", { class: "diff-label", text: LABEL[block.op] || block.op }),
      block.old ? h("p", { class: "diff-old", text: block.old }) : null,
      block.new ? h("p", { text: block.new }) : null,
    ])),
  ]);
}

// 문서 이름 아래의 한 줄. 문서 이름이 파일 이름에서 온 것이면 파일 이름을 되풀이하지 않는다.
function meta(doc) {
  const stem = String(doc.filename).replace(/\.[^.]+$/, "").replace(/_/g, " ").replace(/\s+/g, " ").trim();
  return [stem === doc.title ? "" : doc.filename, doc.pages ? `${count(doc.pages)}쪽` : "", doc.bytes ? bytes(doc.bytes) : "", doc.date ? `${doc.date} 기준` : "", doc.stored ? "" : "EU 사이트로 연결"].filter(Boolean).join(", ");
}

function row(doc) {
  const detail = h("div", { hidden: true });
  const main = safeLink(doc.download, "", { class: "doc-main", target: null, download: doc.filename, title: `${doc.filename} 내려받기` });
  if (main) {
    fill(main,
      h("span", { class: "doc-type", "data-type": doc.format || null, text: doc.format || "파일" }),
      h("span", { class: "doc-title", text: doc.title }),
      h("span", { class: "doc-meta", text: meta(doc) }),
      h("span", { class: "doc-get" }, [icon("download", 16), h("span", { text: "내려받기" })]),
    );
  }
  const changed = doc.diff ? h("button", {
    class: "btn", type: "button", text: "바뀐 곳 보기", "aria-expanded": "false",
    onclick: async (event) => {
      const open = detail.hidden;
      detail.hidden = !open;
      event.target.setAttribute("aria-expanded", String(open));
      if (open && !detail.childNodes.length) {
        detail.replaceChildren(h("p", { class: "count", text: "읽는 중" }));
        detail.replaceChildren(diffView(await data.diff(doc.diff)));
      }
    },
  }) : null;
  const extra = [
    doc.versions > 1 ? h("span", { text: `${doc.versions}번째 판` }) : null,
    changed,
    ...(doc.earlier || []).map((version) => safeLink(version.download, `${version.date} 판 내려받기`, { target: null })),
    doc.linked === false ? pill("원래 화면에서 링크가 사라짐", "warn") : null,
  ].filter(Boolean);
  return h("li", { class: "doc", "data-text": `${doc.title} ${doc.filename}`.toLowerCase() }, [
    main || h("span", { class: "doc-main" }, h("span", { class: "doc-title", text: doc.title })),
    extra.length ? h("div", { class: "doc-extra" }, extra) : null,
    detail,
  ]);
}

export async function render(main) {
  const [documents, pageOf, unreachable] = await Promise.all([data.documents(), data.documentPages(), data.unreachableDocuments()]);
  const head = band("원문 대장", "EU 집행위원회가 올린 CBAM 문서입니다. 문서 이름을 누르면 파일을 내려받습니다. 문서가 바뀌면 바뀐 곳을 함께 보여 줍니다.", libraryTabs("docs"));
  if (!documents.length) {
    fill(main, head, empty("문서 목록을 준비하고 있습니다."));
    return;
  }
  // 문서가 걸려 있는 EU 집행위원회 화면별로 묶는다.
  const sourceOf = new Map(Object.entries(pageOf));
  const pages = [...new Set(documents.map((doc) => doc.page || ""))].sort((a, b) => (sourceOf.get(a)?.order ?? 999) - (sourceOf.get(b)?.order ?? 999));
  const status = h("p", { class: "count", role: "status", text: `문서 ${documents.length}건` });
  const sections = pages.map((page) => {
    const source = sourceOf.get(page);
    const mine = documents.filter((doc) => (doc.page || "") === page).sort((a, b) => String(a.title).localeCompare(String(b.title), "en", { numeric: true }));
    return h("section", { class: "stack", "data-group": "true" }, [
      h("div", { class: "sec-head" }, [
        h("h2", { text: source ? source.name : "그 밖의 문서" }),
        source ? safeLink(source.url, "EU 집행위원회의 원래 화면 열기") : null,
      ]),
      h("ul", { class: "doc-list" }, mine.map(row)),
      unreachable[page] ? h("p", { class: "count", text: `이 목록에 없는 문서가 ${unreachable[page]}건 더 있습니다. 위의 화면 링크에서 받을 수 있습니다.` }) : null,
    ]);
  });
  const none = h("div", { hidden: true }, empty("찾는 문서가 없습니다. 다른 낱말로 찾아보세요."));

  function filter(text) {
    const words = text.toLowerCase().split(/\s+/).filter(Boolean);
    let shown = 0;
    for (const section of sections) {
      let inGroup = 0;
      for (const item of section.querySelectorAll(".doc")) {
        const hit = words.every((word) => item.dataset.text.includes(word));
        item.hidden = !hit;
        if (hit) inGroup += 1;
      }
      section.hidden = inGroup === 0;
      shown += inGroup;
    }
    status.textContent = words.length ? `문서 ${documents.length}건 가운데 ${shown}건` : `문서 ${documents.length}건`;
    none.hidden = shown > 0;
  }

  fill(main,
    head,
    h("div", { class: "filters" }, [
      h("label", { class: "field", for: "doc-q" }, [h("span", { text: "문서 찾기" }), h("input", { id: "doc-q", type: "search", placeholder: "예: guidance, default values, 5d", oninput: (event) => filter(event.target.value) })]),
      status,
    ]),
    ...sections,
    none,
  );
}
