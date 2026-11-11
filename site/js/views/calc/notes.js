// 계산 근거와 가정. 글은 자료(data/calc.json)에서 오고, 글마다 근거가 된 법령의 원문을 가리킨다.
import { h, safeLink } from "../../ui/dom.js";
import { icon } from "../../ui/icons.js";

function sourceLink(source) {
  const link = safeLink(source.url, source.text);
  if (link) link.append(icon("out", 13));
  return link || h("span", { text: source.text });
}

export function notes(book, factorBook) {
  return h("section", { class: "panel calc-notes", "aria-labelledby": "h-calc-notes" }, [
    h("h2", { id: "h-calc-notes", text: "계산 근거와 가정" }),
    h("p", { class: "calc-formula" }, [h("span", { text: book.formula.text }), sourceLink(book.formula.source)]),
    h("ul", {}, [
      ...book.notes.map((note) => h("li", {}, [h("span", { text: note.text }), sourceLink(note.source)])),
      h("li", {}, [
        h("span", { text: "CBAM 계수는 현행 지침의 값과 개정안의 값을 골라 볼 수 있습니다. 개정안은 심의 중이어서 바뀔 수 있습니다." }),
        ...factorBook.paths.map((path) => sourceLink(path.source)),
        h("a", { href: "#rules-ets-review", text: "두 값을 견준 그림 보기" }),
      ]),
    ]),
    h("p", { class: "count", text: `자료 기준일 ${book.asOf}. 품목 ${book.goods.length}개의 CBAM 벤치마크와 기본값을 법령의 표에서 옮겼고, 품목 이름은 법령의 영문 그대로입니다.` }),
  ]);
}
