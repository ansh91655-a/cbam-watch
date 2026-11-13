// 작은 창. 구독 안내, 의견 보내기, 전체 메뉴가 함께 쓴다. 한 번에 하나만 열고, 바깥을 누르거나 Esc를 누르면 닫힌다.
import { h } from "./dom.js";
import { icon } from "./icons.js";

let dialog = null;

export function canOpen() {
  return typeof HTMLDialogElement !== "undefined";
}

// kind는 창의 꼴이다(css/overlay.css): "menu"는 넓은 창.
export function openDialog(title, body, kind = "") {
  if (!canOpen()) return false;
  if (!dialog) {
    dialog = h("dialog", { class: "sheet", tabindex: "-1" });
    dialog.addEventListener("click", (event) => { if (event.target === dialog) dialog.close(); });
    document.body.append(dialog);
  }
  if (dialog.open) dialog.close();
  dialog.setAttribute("aria-labelledby", "sheet-title");
  dialog.dataset.kind = kind;
  dialog.replaceChildren(
    h("div", { class: "sheet-head" }, [
      h("h2", { id: "sheet-title", text: title }),
      h("button", { class: "sheet-close", type: "button", "aria-label": "닫기", onclick: () => dialog.close() }, icon("close", 18)),
    ]),
    h("div", { class: "sheet-body" }, body),
  );
  dialog.showModal();
  dialog.focus(); // 닫기 단추가 아니라 창 자체에 초점을 둔다(창의 제목부터 읽힌다)
  return true;
}

export function closeDialog() {
  if (dialog && dialog.open) dialog.close();
}
