// 품목별 가이던스. EU 집행위원회가 CBAM 대상 품목마다 낸 가이던스를 표로 놓는다. 문서 이름을 누르면 화면에서 바로 본다.
import { h, safeLink, table } from "../../ui/dom.js";
import { bytes } from "../../ui/format.js";
import { icon } from "../../ui/icons.js";
import { stackable } from "../../ui/stack.js";
import { canView, openViewer } from "../../ui/viewer.js";

// [아이콘, 품목 이름, 가이던스 번호]
const SECTORS = [["steel", "철강", "5d"], ["aluminium", "알루미늄", "5e"], ["cement", "시멘트", "5a"], ["fertilisers", "비료", "5c"], ["hydrogen", "수소", "5b"], ["electricity", "전력", "5f"]];

function find(documents, no) {
  return documents.find((item) => new RegExp(`Guidance No\\.? ?${no}\\b`, "i").test(`${item.title} ${item.filename}`));
}

// 문서 이름에서 번호 뒤의 영문 제목만
function english(doc) {
  return String(doc.title).replace(/^Guidance No\.? ?\w+\s*-\s*/i, "");
}

function size(doc) {
  return [doc.format, doc.pages ? `${doc.pages}쪽` : "", doc.bytes ? bytes(doc.bytes) : ""].filter(Boolean).join(", ");
}

function row([key, name, no], doc) {
  const label = h("th", { scope: "row" }, h("span", { class: "g-sector" }, [icon(key, 18), h("span", { text: name })]));
  if (!doc) {
    return h("tr", {}, [label, h("td", {}, h("a", { href: "#docs", text: `가이던스 ${no} (원문 대장에서 찾기)` })), h("td", {}), h("td", {})]);
  }
  const viewable = Boolean(doc.stored) && doc.format === "PDF";
  const open = safeLink(doc.download, `가이던스 ${no}`, viewable ? { class: "g-open", title: `${doc.title} 바로 보기` } : { class: "g-open", target: null, download: doc.filename });
  if (open && viewable) {
    open.addEventListener("click", (event) => {
      if (!canView() || event.metaKey || event.ctrlKey || event.shiftKey) return; // 새 탭으로 열려는 누름은 그대로 둔다
      event.preventDefault();
      openViewer({ title: doc.title, meta: size(doc), url: open.href, filename: doc.filename });
    });
  }
  const save = safeLink(doc.download, "내려받기", { class: "g-save", target: null, download: doc.filename, "aria-label": `${doc.title} 내려받기` });
  if (save) save.prepend(icon("download", 15));
  return h("tr", {}, [
    label,
    h("td", {}, [open || h("span", { text: `가이던스 ${no}` }), h("span", { class: "count", lang: "en", text: english(doc) })]),
    h("td", { class: "g-size", text: size(doc) }),
    h("td", { class: "g-get" }, save),
  ]);
}

export function guidance(documents) {
  const wrap = table(["품목", "문서", "분량", "받기"], SECTORS.map((sector) => row(sector, find(documents, sector[2]))));
  wrap.classList.add("guidance");
  return h("section", { class: "stack", "aria-labelledby": "h-guidance" }, [
    h("div", { class: "sec-head" }, [h("h2", { id: "h-guidance", text: "품목별 가이던스" }), h("a", { href: "#docs", text: "원문 대장 전체 보기" })]),
    h("p", { class: "sec-lead", text: "EU 집행위원회가 CBAM 대상 품목마다 낸 가이던스의 원문입니다. 문서 이름을 누르면 내려받지 않고 바로 볼 수 있습니다." }),
    stackable(wrap),
  ]);
}
