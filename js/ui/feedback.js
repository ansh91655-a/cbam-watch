// 의견 보내기. 화면 오른쪽 여백의 탭이나 바닥글의 단추를 누르면 창이 열리고, 적은 내용을 메일로 보낸다.
// 메일 제목에 정해 둔 꼬리표를 붙여서, 받은 편지함에서 의견 메일만 골라 찾을 수 있게 한다.
// 주소는 설정에 둘로 나눠 둔 것을 여기에서 잇는다(자동 수집 프로그램에 덜 걸리도록).
import { copyButton } from "./copy.js";
import { canOpen, openDialog } from "./dialog.js";
import { h } from "./dom.js";
import { icon } from "./icons.js";

export const SUBJECT_TAG = "[CBAM 규제동향 의견]";
const KINDS = ["잘못된 내용", "빠진 소식", "고쳤으면 하는 점", "그 밖의 의견"];

function mailBody(text) {
  return `${text.trim() || "(여기에 의견을 적어 주세요)"}\n\n보고 있던 화면: ${location.href}\n`;
}

export function openFeedback(address) {
  if (!address) return false;
  const state = { kind: KINDS[0] };
  const text = h("textarea", { id: "fb-text", rows: 6, placeholder: "어느 화면의 무엇이 어떻게 잘못되었는지, 또는 무엇이 있으면 좋겠는지 적어 주세요." });
  const subject = () => `${SUBJECT_TAG} ${state.kind}`;
  const mail = h("a", { class: "btn btn-main" }, [icon("mail", 16), h("span", { text: "메일 앱으로 보내기" })]);
  const gmail = h("a", { class: "btn", target: "_blank", rel: "noopener" }, [h("span", { text: "Gmail에서 쓰기" }), icon("out", 14)]);
  // 누르는 때의 내용으로 링크를 맞춘다.
  const sync = () => {
    const query = `subject=${encodeURIComponent(subject())}&body=${encodeURIComponent(mailBody(text.value))}`;
    mail.href = `mailto:${address}?${query}`;
    gmail.href = `https://mail.google.com/mail/?view=cm&fs=1&to=${encodeURIComponent(address)}&su=${encodeURIComponent(subject())}&body=${encodeURIComponent(mailBody(text.value))}`;
  };
  const kinds = h("div", { class: "seg seg-wrap", role: "group", "aria-label": "의견의 종류" }, KINDS.map((kind) => h("button", {
    type: "button", text: kind, "aria-pressed": String(kind === state.kind),
    onclick: (event) => {
      state.kind = kind;
      for (const button of event.target.parentNode.children) button.setAttribute("aria-pressed", String(button === event.target));
      sync();
    },
  })));
  text.addEventListener("input", sync);
  sync();
  return openDialog("의견 보내기", [
    h("p", { text: "잘못된 내용이나 빠진 소식, 고쳤으면 하는 점을 알려 주세요. 아래에 적은 내용이 메일로 옮겨집니다." }),
    kinds,
    h("label", { class: "field", for: "fb-text" }, [h("span", { text: "내용" }), text]),
    h("div", { class: "sheet-actions" }, [mail, gmail]),
    h("div", { class: "sheet-note" }, [
      h("p", { text: "메일 앱이 열리지 않으면" }),
      h("div", { class: "feed-url" }, [
        h("input", { type: "text", readonly: true, value: address, "aria-label": "받는 주소", onfocus: (event) => event.target.select() }),
        copyButton(address, "주소 복사"),
      ]),
      h("p", { class: "count", text: `쓰시는 메일에서 위 주소로 보내 주세요. 제목 앞에 ${SUBJECT_TAG} 를 붙여 주시면 빨리 확인할 수 있습니다.` }),
    ]),
  ]);
}

// 화면 오른쪽 여백에 붙는 탭. 여백이 있는 넓은 화면에서만 보인다(좁은 화면에서는 바닥글의 단추를 쓴다).
export function feedbackTab(address) {
  if (!address || !canOpen()) return null;
  return h("button", { class: "edge-tab", type: "button", "aria-haspopup": "dialog", onclick: () => openFeedback(address) }, [icon("mail", 16), h("span", { text: "의견 보내기" })]);
}
