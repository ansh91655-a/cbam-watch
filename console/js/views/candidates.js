// 후보. 자동 수집이 찾은 것 가운데 무엇을 쓰고 무엇을 뺐는지 본다.
import { empty, h, pill, safeLink, table } from "../ui/dom.js";
import { viewHead } from "../ui/head.js";
import { minute } from "../ui/format.js";

const TONE = { "작성됨": "accent", "제외": null, "묶음": "warn" };

export function render(main, model) {
  const rows = model.candidates.map((candidate) => h("tr", {}, [
    h("td", { class: "num", text: minute(candidate.at) }),
    h("td", { text: candidate.source || "" }),
    h("td", {}, [safeLink(candidate.url, candidate.text || candidate.id) || h("span", { text: candidate.text || candidate.id })]),
    h("td", {}, pill(candidate.status || "", TONE[candidate.status])),
    h("td", { text: candidate.reason || "" }),
  ]));
  main.replaceChildren(
    viewHead("후보", "최근 후보 300건까지 보여 줍니다. 제외한 후보는 사유와 함께 남습니다."),
    rows.length ? table([{ text: "처리", num: true }, "출처", "후보", "결과", "사유"], rows) : empty("아직 처리한 후보가 없습니다."),
  );
}
