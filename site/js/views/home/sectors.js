// 품목별 가이던스. 품목마다 그림이 있는 칸을 짙은 띠에 놓는다. 누르면 그 품목의 가이던스 원문을 내려받지 않고 화면에서 바로 본다.
// 화면 안에서 PDF를 보여 줄 수 없는 환경(휴대전화)에서는 새 탭으로 열리고, 대장에 없는 문서는 원문 대장으로 간다.
import { fill, h, safeLink } from "../../ui/dom.js";
import { bytes } from "../../ui/format.js";
import { icon } from "../../ui/icons.js";
import { canView, openViewer } from "../../ui/viewer.js";

// CBAM 대상 품목과 EU 집행위원회의 품목별 가이던스 번호
const SECTORS = [["steel", "철강", "5d"], ["aluminium", "알루미늄", "5e"], ["cement", "시멘트", "5a"], ["fertilisers", "비료", "5c"], ["hydrogen", "수소", "5b"], ["electricity", "전력", "5f"]];

function size(doc) {
  return [doc.format, doc.pages ? `${doc.pages}쪽` : "", doc.bytes ? bytes(doc.bytes) : ""].filter(Boolean).join(", ");
}

function tile([key, name, no], doc) {
  const viewable = Boolean(doc && doc.stored) && doc.format === "PDF";
  const body = [
    h("span", { class: "sector-art", "aria-hidden": "true" }, icon(key, 92)),
    h("span", { class: "sector-body" }, [
      h("span", { class: "tile-name", text: name }),
      // 좁은 칸에서 "PDF 65쪽"이 둘로 갈라지지 않게 한 덩어리로 둔다
      h("span", { class: "tile-sub" }, doc ? [`가이던스 ${no}, `, h("span", { class: "nb", text: `${doc.format}${doc.pages ? ` ${doc.pages}쪽` : ""}` })] : `가이던스 ${no}`),
      h("span", { class: "get" }, [icon(doc ? (viewable ? "file" : "download") : "next", 15), h("span", { text: doc ? (viewable ? "바로 보기" : "내려받기") : "원문 대장에서 찾기" })]),
    ]),
  ];
  if (!doc) return h("a", { class: "sector", "data-sector": key, href: "#docs" }, body);
  const link = safeLink(doc.download, "", viewable
    ? { class: "sector", "data-sector": key, title: `${doc.title} 바로 보기` }
    : { class: "sector", "data-sector": key, target: null, download: doc.filename, title: `${doc.filename} 내려받기` });
  if (!link) return h("a", { class: "sector", "data-sector": key, href: "#docs" }, body);
  if (viewable) {
    link.addEventListener("click", (event) => {
      if (!canView() || event.metaKey || event.ctrlKey || event.shiftKey) return; // 새 탭으로 열려는 누름은 그대로 둔다
      event.preventDefault();
      openViewer({ title: doc.title, meta: size(doc), url: link.href, filename: doc.filename });
    });
  }
  return fill(link, body);
}

export function sectors(documents) {
  const find = (no) => documents.find((item) => new RegExp(`Guidance No\\.? ?${no}\\b`, "i").test(`${item.title} ${item.filename}`));
  return h("section", { class: "showcase bleed", "aria-labelledby": "h-sectors" }, h("div", { class: "showcase-inner" }, [
    h("div", { class: "sec-head" }, [h("h2", { id: "h-sectors", text: "품목별 가이던스" }), h("a", { href: "#docs", text: "원문 대장 전체 보기" })]),
    h("p", { class: "sec-lead", text: "EU 집행위원회가 CBAM 대상 품목마다 낸 가이던스의 원문입니다. 누르면 내려받지 않고 바로 볼 수 있습니다." }),
    h("div", { class: "sectors" }, SECTORS.map((sector) => tile(sector, find(sector[2])))),
  ]));
}
