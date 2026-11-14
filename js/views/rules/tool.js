// 규제에 이어 주는 도구. 규제 자료의 tool에 이름이 적힌 규제만 보여 준다(이름은 tools/publish/regulations.py의 TOOLS와 같다).
import { h } from "../../ui/dom.js";
import { icon } from "../../ui/icons.js";

const TOOLS = {
  calc: { href: "#calc", name: "인증서 비용 추정", text: "이 규정의 값으로 품목별 인증서 수와 비용을 어림해 볼 수 있습니다." },
};

export function tool(rule) {
  const one = TOOLS[rule.tool];
  if (!one) return null;
  return h("a", { class: "rule-tool", href: one.href }, [
    h("span", { class: "chipicon" }, icon("emissions", 20)),
    h("span", { class: "rule-tool-body" }, [h("strong", { text: one.name }), h("span", { text: one.text })]),
    icon("next", 18),
  ]);
}
