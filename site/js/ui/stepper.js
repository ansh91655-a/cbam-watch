// 단계 표시. 단계 이름을 차례로 늘어놓고 지금 단계를 강조한다. 작게 보일 때(compact)는 지금 단계의 이름만 글로 보인다.
import { h } from "./dom.js";

export function stepper(path, at, compact) {
  const label = `${path.length}단계 가운데 ${at + 1}단계: ${path[at]}`;
  return h("ol", { class: compact ? "stepper compact" : "stepper", "aria-label": label }, path.map((name, index) =>
    h("li", { "data-state": index < at ? "done" : index === at ? "now" : "todo", "aria-current": index === at ? "step" : null }, [
      h("span", { class: "dot", "aria-hidden": "true" }),
      h("span", { class: "name", text: name }),
    ])));
}
