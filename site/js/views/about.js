// 안내. 이 사이트에서 볼 수 있는 것과 이용할 때 알아 둘 점을 적는다. 문구는 이 파일 한 곳에서만 정한다.
import { band } from "../ui/band.js";
import { fill, h } from "../ui/dom.js";
import { icon } from "../ui/icons.js";

// 화면마다 무엇을 볼 수 있는지: [아이콘, 이름, 설명, 주소]
const SCREENS = [
  ["news", "소식", "CBAM 소식을 주제별로 정리해 원문 링크와 함께 싣습니다.", "#news"],
  ["price", "가격", "EU 집행위원회가 게시하는 CBAM 인증서 가격과 추세를 보여 줍니다.", "#price"],
  ["calendar", "일정", "신고 기한과 시행일처럼 날짜가 정해진 일정을 모았습니다.", "#calendar"],
  ["file", "원문 대장", "EU 집행위원회의 가이던스와 서식을 내려받을 수 있습니다.", "#docs"],
  ["terms", "용어집", "CBAM 용어의 국문 표기를 찾아볼 수 있습니다.", "#terms"],
  ["sources", "출처", "이 사이트가 살펴보는 기관과 화면의 목록입니다.", "#sources"],
];

const SECTIONS = [
  ["who", "운영", [
    "개인이 운영하는 비공식 사이트입니다. 유럽연합(EU)과 그 기관의 공식 사이트가 아니며, 그 기관들과 관계가 없습니다.",
  ]],
  ["limits", "이용할 때 알아 둘 점", [
    "요약과 번역은 인공지능으로 작성한 참고 자료이며, 오류가 있을 수 있습니다. 모든 소식에 원문 링크를 붙였으니 정확한 내용은 원문에서 확인해 주세요.",
    "신고, 산정, 계약처럼 결과에 책임이 따르는 일에는 반드시 원문과 관할 당국의 안내를 확인해 주세요.",
    "이 사이트의 내용은 법률 자문이 아닙니다.",
  ]],
  ["reuse", "자료의 출처와 재이용", [
    "EU 기관의 공식 자료는 출처를 밝히고 재이용합니다. 민간·협회 자료는 제목과 링크만 싣습니다.",
    "원문의 저작권과 재이용 조건은 각 출처를 따릅니다.",
  ]],
];

function screens() {
  return h("section", { class: "stack", "aria-labelledby": "h-screens" }, [
    h("h2", { id: "h-screens", text: "이 사이트에서 볼 수 있는 것" }),
    h("div", { class: "steps" }, SCREENS.map(([key, name, text, href]) => h("a", { class: "step", href }, [
      h("span", { class: "chipicon" }, icon(key, 22)),
      h("h3", { text: name }),
      h("p", { text }),
    ]))),
  ]);
}

function section([key, title, paragraphs]) {
  return h("section", { class: "panel about-card" }, [
    h("h2", {}, [h("span", { class: "chipicon" }, icon(key, 20)), h("span", { text: title })]),
    ...paragraphs.map((text) => h("p", { text })),
  ]);
}

export async function render(main) {
  fill(main,
    band("안내", "이 사이트에서 볼 수 있는 것과 이용할 때 알아 둘 점입니다."),
    screens(),
    h("div", { class: "about-grid" }, SECTIONS.map(section)),
  );
}
