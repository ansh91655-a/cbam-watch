// 인증서 가격의 연평균: 그해의 것으로 게시된 가격을 평균한 값. 제3국에서 낸 탄소가격을 인증서 수로 바꿀 때 나누는 기준가격이 이렇게 정해진다.
// 공식 기준가격은 EU 집행위원회가 CBAM 등록부에 공개한다. 여기에 적는 값은 게시된 가격으로 이 사이트가 계산한 것이다(셈은 calc/prices.js).
import { pricedYears, yearMean } from "../../calc/prices.js";
import { h, table } from "../../ui/dom.js";
import { price } from "../../ui/format.js";
import { lawRefs } from "../../ui/lawrefs.js";
import { stackable } from "../../ui/stack.js";

const REFS = [{ act: "32026R2498", part: "art-7", label: "제3국 탄소가격 차감 이행규정 제7조(3)" }];
const KIND = { quarter: "분기 가격", week: "주간 가격" };

function note(row) {
  const of = `${KIND[row.kind] || "가격"} ${row.count}개의 평균`;
  return row.partial ? `${of}. 그해의 가격이 더 게시되면 달라집니다.` : `${of}.`;
}

// book: data/prices.json. 게시된 가격이 없으면 null
export function meansSection(book, unit) {
  const rows = pricedYears(book).map((year) => yearMean(book, year)).filter(Boolean).reverse();
  if (!rows.length) return null;
  return h("section", { class: "stack", "aria-labelledby": "h-means" }, [
    h("h2", { id: "h-means", text: "연평균 가격" }),
    h("p", { class: "sub", text: "제3국에서 낸 탄소가격을 인증서 수로 바꿀 때에는 수입한 해의 인증서 가격을 평균한 기준가격으로 나눕니다. 공식 기준가격은 EU 집행위원회가 CBAM 등록부에 공개하며, 아래는 게시된 가격으로 이 사이트가 계산한 값입니다." }),
    stackable(table(["수입한 해", { text: `평균(${unit})`, num: true }, "계산한 방법"], rows.map((row) => h("tr", {}, [
      h("td", { text: `${row.year}년` }),
      h("td", { class: "num" }, h("strong", { text: price(row.value) })),
      h("td", { text: note(row) }),
    ])), "해마다의 인증서 가격 평균")),
    lawRefs(REFS, "근거 조문"),
    h("p", {}, h("a", { class: "more", href: "#handbook-carbon-price.rules-to-come", text: "기준가격이 쓰이는 곳: 탄소가격 차감의 식" })),
  ]);
}
