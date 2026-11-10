// 안내. 이 사이트에서 볼 수 있는 것과 이용할 때 알아 둘 점을 적는다. 문구는 이 파일 한 곳에서만 정한다.
import * as data from "../data.js";
import { band } from "../ui/band.js";
import { fill, h } from "../ui/dom.js";
import { libraryTabs } from "../ui/tabs.js";

// 화면마다 무엇을 볼 수 있는지: [이름, 설명, 주소]
const SCREENS = [
  ["소식", "CBAM 소식을 주제별로 정리했습니다. 제목을 누르면 국문 요약을 먼저 보여 주고, 거기에서 원문으로 갈 수 있습니다.", "#news"],
  ["규제", "규제마다 지금 어느 단계에 있는지와 그동안의 연혁, 다음 단계를 정리했습니다.", "#rules"],
  ["가격", "EU 집행위원회가 게시하는 CBAM 인증서 가격과 추세를 보여 줍니다.", "#price"],
  ["일정", "신고 기한과 시행일처럼 날짜가 정해진 일정을 모았습니다.", "#calendar"],
  ["품목 코드 조회", "CN 코드를 넣으면 CBAM 대상 품목인지와 근거를 보여 줍니다.", "#cn"],
  ["원문 대장", "EU 집행위원회의 가이던스와 서식을 화면에서 바로 보거나 내려받을 수 있습니다.", "#docs"],
  ["용어집", "CBAM 용어의 국문 표기를 찾아볼 수 있습니다.", "#terms"],
];

// [제목, 문단들, 단추(이름과 여는 창)]
const SECTIONS = [
  ["운영", [
    "개인이 운영하는 비공식 사이트입니다. 유럽연합(EU)과 그 기관의 공식 사이트가 아니며, 그 기관들과 관계가 없습니다.",
    "평일 아침마다 새 소식과 바뀐 문서를 확인해 싣습니다.",
  ]],
  ["이용할 때 알아 둘 점", [
    "요약과 번역은 참고 자료이며, 오류가 있을 수 있습니다. 모든 소식에 원문 링크를 붙였으니 정확한 내용은 원문에서 확인해 주세요.",
    "신고, 산정, 계약처럼 결과에 책임이 따르는 일에는 반드시 원문과 관할 당국의 안내를 확인해 주세요.",
    "이 사이트의 내용은 법률 자문이 아닙니다.",
  ]],
  ["새 소식 받아 보기", [
    "새 소식과 규제의 변화를 RSS 주소로도 내보냅니다. RSS 구독 앱이나 협업 도구에 주소를 한 번 넣어 두면, 이 사이트에 들어오지 않아도 새 소식을 받아 볼 수 있습니다.",
  ], ["구독 주소 보기", "subscribe"]],
  ["의견 보내기", [
    "잘못된 내용이나 빠진 소식, 고쳤으면 하는 점은 메일로 알려 주세요. 보내 주신 의견은 사이트를 고치는 데 참고합니다.",
  ], ["의견 보내기", "feedback"]],
  ["자료의 출처와 재이용", [
    "EU 기관의 공식 자료는 출처를 밝히고 재이용합니다. 민간·협회 자료는 제목과 링크만 싣습니다.",
    "소식 카드의 미리보기 그림은 원문 화면이나 문서 첫 장의 윗부분을 줄인 것으로, EU 기관과 영국 정부(Open Government Licence v3.0)의 자료입니다. 그 밖의 소식에는 그림 대신 주제 아이콘을 씁니다.",
    "원문의 저작권과 재이용 조건은 각 출처를 따릅니다.",
  ]],
];

function screens() {
  return h("section", { class: "stack", "aria-labelledby": "h-screens" }, [
    h("h2", { id: "h-screens", text: "이 사이트에서 볼 수 있는 것" }),
    h("ul", { class: "guide-list" }, SCREENS.map(([name, text, href]) => h("li", {}, [h("a", { href, text: name }), h("span", { text })]))),
  ]);
}

function section([title, paragraphs, opener], canWrite) {
  if (opener && opener[1] === "feedback" && !canWrite) return null;
  return h("section", { class: "prose" }, [
    h("h2", { text: title }),
    ...paragraphs.map((text) => h("p", { text })),
    opener ? h("p", {}, h("button", { class: "btn", type: "button", "data-open": opener[1], text: opener[0] })) : null,
  ]);
}

export async function render(main) {
  const site = await data.site();
  const canWrite = Boolean(site.maker && site.maker.user && site.maker.host);
  fill(main,
    band("안내", "이 사이트에서 볼 수 있는 것과 이용할 때 알아 둘 점입니다.", libraryTabs("about")),
    screens(),
    h("div", { class: "about-text" }, SECTIONS.map((entry) => section(entry, canWrite))),
  );
}
