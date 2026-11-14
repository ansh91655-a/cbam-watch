// 문서를 내려받지 않고 화면에서 바로 보여 준다. 브라우저에 든 PDF 보기 기능을 쓴다.
import { h } from "./dom.js";
import { icon } from "./icons.js";

let dialog = null;

// 화면 안에서 PDF를 보여 줄 수 있는 환경인지. 휴대전화의 브라우저는 대개 못 하므로, 그때는 문서를 새 탭으로 연다(링크의 원래 동작).
export function canView() {
  return typeof HTMLDialogElement !== "undefined" && navigator.pdfViewerEnabled !== false && window.matchMedia("(min-width: 760px)").matches;
}

export function openViewer({ title, meta, url, filename }) {
  if (!dialog) {
    dialog = h("dialog", { class: "viewer", "aria-label": "문서 보기" });
    dialog.addEventListener("click", (event) => { if (event.target === dialog) dialog.close(); }); // 바깥을 누르면 닫는다
    dialog.addEventListener("close", () => dialog.replaceChildren()); // 닫으면 문서를 내려놓는다
    document.body.append(dialog);
  }
  dialog.replaceChildren(
    h("div", { class: "viewer-head" }, [
      h("div", { class: "viewer-title" }, [h("strong", { text: title }), meta ? h("span", { text: meta }) : null]),
      h("div", { class: "viewer-actions" }, [
        h("a", { class: "viewer-btn", href: url, target: "_blank", rel: "noopener" }, [icon("out", 15), h("span", { text: "새 탭에서 열기" })]),
        h("a", { class: "viewer-btn", href: url, download: filename }, [icon("download", 15), h("span", { text: "내려받기" })]),
        h("button", { class: "viewer-btn viewer-close", type: "button", text: "닫기", autofocus: true, onclick: () => dialog.close() }),
      ]),
    ]),
    h("iframe", { class: "viewer-frame", src: `${url}#view=FitH`, title: `${title} 문서` }),
  );
  dialog.showModal();
}
