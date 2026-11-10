// 원문 대장. 추적하는 원문 문서와 판 이력, 판 사이에 바뀐 곳을 보여 준다.
import * as data from "../data.js";
import { empty, h, pill, safeLink, table, viewHead } from "../ui/dom.js";
import { bytes, count } from "../ui/format.js";

const LABEL = { added: "더해짐", removed: "빠짐", changed: "바뀜" };

function diffView(result) {
  if (!result) return empty("비교 결과를 읽지 못했습니다.");
  const stats = result.stats || {};
  const head = h("p", { class: "count", text: `${result.fromDate} 판과 ${result.toDate} 판의 비교: 바뀜 ${stats.changed || 0}, 더해짐 ${stats.added || 0}, 빠짐 ${stats.removed || 0}${result.truncated ? " (앞부분만 표시)" : ""}` });
  const blocks = (result.blocks || []).map((block) => h("div", { class: "diff-block", "data-op": block.op }, [
    h("span", { class: "diff-label", text: LABEL[block.op] || block.op }),
    block.old ? h("p", { class: "diff-old", text: block.old }) : null,
    block.new ? h("p", { text: block.new }) : null,
  ]));
  return h("div", { class: "diff" }, [head, ...blocks]);
}

function row(doc, detailCell) {
  const versions = doc.versions || [];
  const latest = versions[versions.length - 1] || {};
  const withDiff = [...versions].reverse().find((version) => version.diff);
  const button = withDiff ? h("button", {
    class: "btn", type: "button", text: "바뀐 곳 보기",
    onclick: async () => { detailCell.replaceChildren(h("p", { class: "count", text: "읽는 중" })); detailCell.replaceChildren(diffView(await data.diff(withDiff.diff))); },
  }) : null;
  return h("tr", {}, [
    h("td", {}, [safeLink(doc.url, doc.title) || h("span", { text: doc.title }), doc.linked === false ? h("p", {}, pill("원문 화면에서 링크가 사라짐", "warn")) : null]),
    h("td", { class: "num", text: latest.date || "" }),
    h("td", { class: "num", text: latest.pages ? `${count(latest.pages)}쪽` : "" }),
    h("td", { class: "num", text: bytes(latest.bytes) }),
    h("td", { class: "num", text: `${versions.length}` }),
    h("td", {}, [
      safeLink(latest.file, "사본") || h("span", { class: "count", text: "사본 없이 변경 여부만 확인" }),
      latest.text ? h("span", { text: " · " }) : null, safeLink(latest.text, "본문"), button ? h("p", {}, button) : null,
    ]),
  ]);
}

export async function render(main) {
  const documents = await data.documents();
  if (!documents.length) {
    main.replaceChildren(viewHead("원문 대장", "추적하는 원문 문서가 아직 등록되지 않았습니다."), empty("원문 문서 목록을 준비하고 있습니다."));
    return;
  }
  const body = [];
  for (const doc of [...documents].sort((a, b) => String(a.title).localeCompare(String(b.title)))) {
    const detailCell = h("td", { colspan: "6" });
    body.push(row(doc, detailCell), h("tr", {}, detailCell));
  }
  main.replaceChildren(
    viewHead("원문 대장", "EU 집행위원회가 올린 법령 관련 문서와 가이던스의 사본을 보관하고, 문서가 바뀌면 이전 판과 비교합니다. 문서 이름을 누르면 원래 올라온 곳이 열립니다."),
    h("p", { class: "count", text: `문서 ${documents.length}건. 판 수가 2 이상이면 바뀐 곳을 볼 수 있습니다.` }),
    table(["문서", { text: "최근 판", num: true }, { text: "쪽수", num: true }, { text: "크기", num: true }, { text: "판 수", num: true }, "보관본"], body),
  );
}
