// 디자인 시안 고르기. 시안 다섯 개의 참고 자료와 색, 글꼴을 보여 주고 그 시안으로 사이트를 열어 볼 수 있게 한다.
// 시안을 정하면 이 화면과 js/theme.js의 기본값을 정리한다.
import { fill, h, safeLink, viewHead } from "../ui/dom.js";

const PROPOSALS = [
  {
    key: "1", name: "표준형", line: "EU 집행위원회 웹사이트의 색과 질서를 따른, 가장 무난한 안",
    about: "진한 파랑 머리띠 아래에 노랑 선 하나. 본문은 흰 바탕에 회색 글, 파랑 링크. 모서리는 거의 각지고 장식이 없다. 공공 정보 사이트로 읽힌다.",
    reference: ["Europa Component Library 색 지침", "https://ec.europa.eu/component-library/ec/guidelines/colours/"],
    fonts: "Noto Sans KR",
    colors: [["#004494", "#fff"], ["#FFD617", "#1d1d1b"], ["#262B33", "#fff"], ["#F2F5F9", "#262b33"], ["#FFFFFF", "#262b33"]],
  },
  {
    key: "2", name: "관보형", line: "유럽연합 관보와 EUR-Lex처럼 문서를 읽는 느낌의 안",
    about: "제목은 명조, 본문은 고딕. 카드 대신 가는 줄로 나누고, 날짜와 주제를 왼쪽 여백에 둔다. 색은 엠블럼 파랑과 형광펜처럼 쓰는 노랑뿐이다. 글을 오래 읽기에 편하다.",
    reference: ["기관 간 편집 지침(Interinstitutional Style Guide)", "https://style-guide.europa.eu/"],
    fonts: "Noto Serif KR(제목), Noto Sans KR(본문)",
    colors: [["#003399", "#fff"], ["#FFCC00", "#14213d"], ["#14213D", "#fff"], ["#F4F6FA", "#14213d"], ["#FFFFFF", "#14213d"]],
  },
  {
    key: "3", name: "깃발형", line: "EU 엠블럼의 파랑과 노랑을 그대로, 크게 쓴 안",
    about: "머리와 요약 띠를 진한 파랑 면으로 채우고, 숫자와 단추에 노랑을 쓴다. 굵은 고딕 제목과 둥근 모서리. 한눈에 EU 자료임을 알 수 있고 가장 강하다.",
    reference: ["EU 깃발 안내와 엠블럼 그래픽 가이드의 색(파랑 #003399, 노랑 #FFCC00)", "https://european-union.europa.eu/principles-countries-history/symbols/european-flag_en"],
    recommended: true,
    fonts: "Gothic A1",
    colors: [["#003399", "#fff"], ["#FFCC00", "#0b1533"], ["#0B1533", "#fff"], ["#EAF0FB", "#0b1533"], ["#FFFFFF", "#0b1533"]],
  },
  {
    key: "4", name: "계기판형", line: "통계 포털처럼 수치와 표를 촘촘히 보여 주는 안",
    about: "연한 회청색 바탕에 흰 판. 글자를 조금 줄이고 간격을 좁히고, 넓은 화면에서는 소식 카드를 두 줄로 나란히 놓아 한 화면에 더 많이 담는다. 자주 들어와 확인하는 사람에게 맞다.",
    reference: ["Eurostat 시각 지침(Eurostat visual guide)", "https://ec.europa.eu/eurostat/web/user-guides/style-guides"],
    fonts: "IBM Plex Sans KR",
    colors: [["#0E47CB", "#fff"], ["#FFD617", "#16213a"], ["#16213A", "#fff"], ["#F1F4F9", "#16213a"], ["#FFFFFF", "#16213a"]],
  },
  {
    key: "5", name: "통관 서류형", line: "EU 세관 신고서의 칸 양식에서 가져온 안",
    about: "모든 것을 파란 잉크 선의 칸으로 나눈다. 소식 하나가 서류 한 장처럼 날짜, 주제, 종류 칸을 갖는다. 중요한 소식은 형광펜으로 칠한 듯 표시한다. CBAM이 신고와 인증서의 제도라는 점을 모양으로 보여 준다.",
    reference: ["단일 행정 문서(SAD) 양식 안내, EU 집행위원회", "https://taxation-customs.ec.europa.eu/system/files/2016-09/presentation_and_use_of_the_form_en.pdf"],
    fonts: "Nanum Gothic",
    colors: [["#1D3C8F", "#fff"], ["#FFE14D", "#12224f"], ["#12224F", "#fff"], ["#EEF2FA", "#12224f"], ["#FFFFFF", "#12224f"]],
  },
];

export async function render(main) {
  const current = (window.CBAM_THEME || {}).key || "1";
  fill(main, 
    viewHead("디자인 시안", "EU의 파랑과 노랑을 바탕으로 한 시안 다섯 개입니다. '이 시안으로 보기'를 누르면 사이트 전체가 그 시안으로 바뀝니다. 화면의 내용과 기능은 모두 같습니다."),
    h("div", { class: "proposals" }, PROPOSALS.map((proposal) => h("section", { class: "proposal", "data-current": proposal.key === current ? "true" : null, "aria-labelledby": `h-proposal-${proposal.key}` }, [
      h("h2", { id: `h-proposal-${proposal.key}` }, [h("span", { text: `시안 ${proposal.key}. ${proposal.name} ` }), proposal.recommended ? h("span", { class: "pill", "data-tone": "ok", text: "추천" }) : null]),
      h("p", {}, h("strong", { text: proposal.line })),
      h("p", { text: proposal.about }),
      h("div", { class: "swatches", "aria-hidden": "true" }, proposal.colors.map(([back, ink]) => h("span", { class: "swatch", style: `background:${back}; color:${ink}`, text: back }))),
      h("p", { class: "count" }, [h("span", { text: `글꼴: ${proposal.fonts}. 참고한 자료: ` }), safeLink(proposal.reference[1], proposal.reference[0])]),
      h("p", {}, proposal.key === current
        ? h("span", { class: "pill", "data-tone": "ok", text: "지금 보고 있는 시안" })
        : h("a", { class: "btn btn-main", href: `?theme=${proposal.key}#home`, text: "이 시안으로 보기" })),
    ]))),
    h("p", { class: "count", text: "EU 엠블럼(별 열두 개)과 EU 기관의 로고는 어느 시안에도 쓰지 않았습니다. 이 사이트가 EU의 공식 사이트로 보이지 않게 하려는 것입니다." }),
  );
}
