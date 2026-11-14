// 안내. 이 사이트에서 볼 수 있는 것과 이용할 때 알아 둘 점을 적는다. 문구는 이 파일 한 곳에서만 정한다.
import * as data from "../data.js";
import { allScreens } from "../nav/map.js";
import { band } from "../ui/band.js";
import { fill, h } from "../ui/dom.js";
import { icon } from "../ui/icons.js";
import { groupTabs } from "../ui/tabs.js";

// 화면마다 무엇을 볼 수 있는지. 이름과 설명(detail)은 화면의 묶음을 적은 표(js/nav/map.js)에 있고, 설명이 있는 화면만 싣는다.
const SCREENS = allScreens().filter((one) => one.detail);

// 새 소식 받아 보기를 열어 둔 동안에만 보이는 안내
const SUBSCRIBE = ["news", "새 소식 받아 보기", [
  "RSS 리더에 이 사이트의 구독 주소를 넣으면 새 소식과 규제의 변화를 받아 볼 수 있습니다. 화면 맨 아래의 '새 소식 받아 보기(RSS)'를 누르면 주소와 넣는 곳을 알려 줍니다.",
]];

const SECTIONS = [
  ["who", "운영", [
    "개인이 운영하는 비공식 사이트입니다. 유럽연합(EU)과 그 기관의 공식 사이트가 아니며, 그 기관들과 관계가 없습니다.",
  ]],
  ["limits", "이용할 때 알아 둘 점", [
    "요약과 번역은 참고 자료이며, 오류가 있을 수 있습니다. 모든 소식에 원문 링크를 붙였으니 정확한 내용은 원문에서 확인해 주세요.",
    "규정 원문의 국문은 이 사이트가 옮긴 비공식 번역입니다. 법적 효력은 EU 관보에 실린 원문에만 있습니다.",
    "신고, 산정, 계약처럼 결과에 책임이 따르는 일에는 반드시 원문과 관할 당국의 안내를 확인해 주세요.",
    "이 사이트의 내용은 법률 자문이 아닙니다.",
  ]],
  ["reuse", "자료의 출처와 재이용", [
    "EU 기관의 공식 자료는 출처를 밝히고 재이용합니다. 민간 기업과 협회, 유료 매체의 자료는 제목이 알려 주는 사실 한 줄과 링크만 싣습니다.",
    "소식 카드의 미리보기 그림 가운데 원문 화면이나 문서 첫 장을 줄여 실은 것은 EU 기관과 영국 정부(Open Government Licence v3.0)의 자료입니다. 그 밖의 소식에는 이 사이트가 직접 그린 그림을 씁니다.",
    "원문의 저작권과 재이용 조건은 각 출처를 따릅니다.",
  ]],
];

function screens() {
  return h("section", { class: "stack", "aria-labelledby": "h-screens" }, [
    h("h2", { id: "h-screens", text: "이 사이트에서 볼 수 있는 것" }),
    h("div", { class: "steps" }, SCREENS.map((one) => h("a", { class: "step", href: one.href }, [
      h("span", { class: "chipicon" }, icon(one.icon, 22)),
      h("h3", { text: one.title }),
      h("p", { text: one.detail }),
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
  const features = (await data.site()).features || {};
  const sections = features.subscribe ? [...SECTIONS.slice(0, 2), SUBSCRIBE, ...SECTIONS.slice(2)] : SECTIONS;
  fill(main,
    band("안내", "이 사이트에서 볼 수 있는 것과 이용할 때 알아 둘 점입니다.", groupTabs("about")),
    screens(),
    h("div", { class: "about-grid" }, sections.map(section)),
  );
}
