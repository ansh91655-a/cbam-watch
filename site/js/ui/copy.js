// 글자를 복사하는 단추. 복사가 되면 단추의 글을 잠깐 바꿔 알려 준다.
import { h } from "./dom.js";
import { icon } from "./icons.js";

const BACK_MS = 2000;

// 글자를 복사한다. 됐는지를 돌려준다.
export async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch (error) {
    // 복사 권한이 없는 환경: 보이지 않는 입력 칸에 넣고 예전 방식으로 복사한다.
    const box = h("textarea", { class: "sr", readonly: true });
    box.value = text;
    document.body.append(box);
    box.select();
    let done = false;
    try { done = document.execCommand("copy"); } catch (again) { done = false; }
    box.remove();
    return done;
  }
}

export function copyButton(text, label = "복사", attrs = {}) {
  const words = h("span", { text: label });
  const button = h("button", { class: "btn btn-small", type: "button", ...attrs }, [icon("copy", 15), words]);
  let timer = null;
  button.addEventListener("click", async () => {
    const done = await copyText(text);
    words.textContent = done ? "복사했습니다" : "복사하지 못했습니다";
    button.dataset.state = done ? "done" : "failed";
    clearTimeout(timer);
    timer = setTimeout(() => { words.textContent = label; delete button.dataset.state; }, BACK_MS);
  });
  return button;
}
