// 인증서 비용 추정의 넣는 칸을 짓는 작은 도우미: 고르는 단추 줄, 이름 붙은 칸, 수를 넣는 칸, 칸들의 묶음.
import { h } from "../../ui/dom.js";

// 여럿 가운데 하나를 고르는 단추 줄. 누르면 눌린 표시를 스스로 옮기고 onPick을 부른다.
// 누른 뒤에 칸들을 다시 그리는 경우에도 초점을 되찾을 수 있게, 단추마다 줄의 이름과 값을 적어 둔다(data-seg).
export function seg(name, label, options, current, onPick) {
  const buttons = options.map(([key, text]) => h("button", { type: "button", text, "data-seg": `${name}:${key}`, "aria-pressed": String(key === current), onclick: () => {
    buttons.forEach((button) => button.setAttribute("aria-pressed", String(button.dataset.seg === `${name}:${key}`)));
    onPick(key);
  } }));
  return h("div", { class: "seg seg-wrap", role: "group", "aria-label": label }, buttons);
}

// 이름과 칸, 그 아래의 도움말. 도움말은 칸의 설명으로 읽히게 잇는다(aria-describedby).
export function field(id, label, control, hint) {
  const note = hint ? h("p", { class: "count", id: `${id}-hint` }, [].concat(hint)) : null;
  if (note) control.setAttribute("aria-describedby", note.id);
  return h("div", { class: "calc-field" }, [h("label", { class: "field", for: id }, [h("span", { text: label }), control]), note]);
}

// 0 이상의 수를 넣는 칸. 값이 바뀔 때마다 onChange(빈 칸이면 "", 아니면 수)를 부른다.
export function numberInput(id, value, onChange, extra = {}) {
  const input = h("input", { id, type: "number", inputmode: "decimal", min: "0", step: "any", value: value === "" || value === null || value === undefined ? null : value, ...extra });
  input.addEventListener("input", () => onChange(input.value === "" ? "" : Number(input.value)));
  return input;
}

// 고르는 칸. options: [[값, 글]]
export function selectInput(id, options, current, onChange) {
  const select = h("select", { id }, options.map(([value, text]) => h("option", { value, selected: String(value) === String(current), text })));
  select.addEventListener("change", () => onChange(select.value));
  return select;
}

// 한 줄: 작은 이름과 그 아래의 단추 줄이나 글
export function row(label, children) {
  return h("div", { class: "calc-row" }, [h("p", { class: "calc-label", text: label }), ...[].concat(children)]);
}

// 칸들의 묶음(실제 배출량, 전구물질, 탄소가격 차감): 제목과 그 아래의 칸들
export function group(id, title, children) {
  return h("section", { class: "calc-group", "aria-labelledby": id }, [h("h3", { id, text: title }), ...[].concat(children)]);
}
