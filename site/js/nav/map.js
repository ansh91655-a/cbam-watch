// 사이트의 화면과 그 묶음. 머리글의 주 메뉴와 펼침 목록, 화면 안의 탭, 전체 메뉴, 바닥 메뉴, 안내 화면, 화면 찾기(검색)가 모두 이 표 하나를 따른다.
// 화면을 더하거나 묶음을 바꿀 때에는 여기를 고치고, index.html의 주 메뉴(처음 그릴 때 깜박이지 않게 적어 둔 것)를 맞춘다. 둘이 어긋나면 시험이 알린다(tests/test_nav.py).
// 화면 요소를 다루지 않으므로 node로 시험한다.

// 화면: 메뉴에 적는 이름(name), 길게 부를 때의 이름(title), 아이콘, 한 줄 설명(about), 안내 화면에 싣는 설명(detail), 그 화면을 찾을 때 쓸 만한 말(words).
export const SCREENS = {
  home: { name: "최신 동향", icon: "home", about: "새로 달라진 점과 주요 소식", words: ["첫 화면", "home"] },
  news: { name: "소식", icon: "news", about: "2025년 1월부터의 소식과 국문 요약", words: ["뉴스", "기사", "news"],
    detail: "CBAM 소식을 주제별로 정리했습니다. 제목을 누르면 국문 요약을 먼저 보여 주고, 거기에서 원문으로 갈 수 있습니다." },
  rules: { name: "규제", icon: "legis", about: "규제마다의 지금 단계와 남은 절차", words: ["진행 상황", "진행 단계", "입법"],
    detail: "규제마다 지금 어느 단계에 있는지와 그동안의 연혁, 다음 단계를 정리했습니다." },
  calendar: { name: "일정", icon: "calendar", about: "출처에 날짜가 적힌 일정과 법령의 의무 기한", words: ["달력", "기한", "마감", "calendar", "deadline"],
    detail: "신고 기한과 시행일처럼 날짜가 정해진 일정을 모았습니다. 역할을 고르면 그 역할이 챙길 의무 일정만 볼 수 있습니다." },
  cn: { name: "품목 코드 조회", icon: "search", about: "CN 코드가 CBAM 대상 품목인지 확인", words: ["품목", "대상 품목", "cn", "hs"],
    detail: "CN 코드를 넣으면 CBAM 대상 품목인지와 근거를 보여 줍니다." },
  sector: { name: "부문별 보기", icon: "steel", about: "부문마다의 대상 품목, 안내 문서, 기본값, 소식", words: ["부문", "부문별", "품목별", "업종", "sector"],
    detail: "CBAM 대상 부문마다 대상 품목과 EU 집행위원회의 가이던스, 기본값, 소식을 한곳에 모았습니다." },
  price: { name: "인증서 가격", title: "CBAM 인증서 가격", icon: "price", about: "EU 집행위원회가 게시한 인증서 가격과 추세", words: ["가격", "price"],
    detail: "EU 집행위원회가 게시하는 CBAM 인증서 가격과 추세를 보여 줍니다." },
  calc: { name: "비용 추정", title: "인증서 비용 추정", icon: "emissions", about: "품목과 물량으로 어림하는 인증서 수와 비용", words: ["비용", "추정", "계산", "계산기", "calculator", "cost"],
    detail: "품목과 물량, 연도를 넣으면 제출할 CBAM 인증서 수와 비용을 어림해 볼 수 있습니다. 법령의 기본값과 벤치마크로 계산한 참고용 추정입니다." },
  handbook: { name: "해설서", title: "CBAM 해설서", icon: "guide", about: "제도가 돌아가는 차례를 조문과 함께 풀이", words: ["해설", "입문", "제도 설명", "handbook"],
    detail: "CBAM이 무엇이고 누가 언제 무엇을 해야 하는지를 차례로 풀어 썼습니다. 절마다 근거가 된 조문으로 이어집니다." },
  terms: { name: "용어집", icon: "terms", about: "국문 정리에 쓰는 용어의 표기 기준", words: ["용어", "표기", "glossary"],
    detail: "CBAM 용어의 국문 표기를 찾아볼 수 있습니다." },
  about: { name: "안내", icon: "who", about: "이 사이트에서 볼 수 있는 것과 알아 둘 점", words: ["사이트 안내", "소개", "about"] },
  laws: { name: "규정 원문", icon: "law", about: "CBAM 법령과 가이던스의 원문과 국문 번역", words: ["법령", "규정", "조문", "번역", "가이던스", "guidance", "regulation"],
    detail: "CBAM 법령과 EU 집행위원회의 가이던스를 문단마다 원문과 국문 번역으로 나란히 실었습니다. 개정으로 달라진 곳을 견줘 볼 수 있고, 가이던스는 원문 PDF와 번역 PDF를 쪽마다 나란히 볼 수 있습니다." },
  docs: { name: "원문 대장", icon: "file", about: "EU 집행위원회가 올린 CBAM 문서", words: ["문서", "자료", "pdf", "내려받기", "다운로드", "download"],
    detail: "EU 집행위원회의 가이던스와 서식을 화면에서 바로 보거나 내려받을 수 있습니다." },
};

// 주 메뉴의 묶음(차례대로). 묶음의 첫 화면이 주 메뉴를 눌렀을 때 열리는 화면이다. about은 전체 메뉴와 바닥 메뉴에 적는 한 줄이다.
export const GROUPS = [
  { key: "home", name: "최신 동향", views: ["home"] },
  { key: "news", name: "소식", views: ["news"] },
  { key: "rules", name: "규제", views: ["rules"] },
  { key: "calendar", name: "일정", views: ["calendar"] },
  { key: "goods", name: "품목·비용", about: "내 품목이 대상인지, 인증서가 얼마나 드는지", views: ["cn", "sector", "price", "calc"] },
  { key: "handbook", name: "해설서", about: "제도를 처음부터 차례로", views: ["handbook", "terms", "about"] },
  { key: "library", name: "원문·자료", about: "법령과 문서의 원문", views: ["laws", "docs"] },
];

// 메뉴에 없는 화면이 어느 화면 아래인지: 소식 하나를 보는 화면은 '소식' 아래, 법령 하나를 보는 화면은 '규정 원문' 아래로 본다.
export const UNDER = { item: "news", law: "laws", changes: "laws", pdf: "laws" };

// 그 화면이 든 묶음. 메뉴에 없는 화면(색 변형, 검색)은 null.
export function groupOf(view) {
  const key = UNDER[view] || view;
  return GROUPS.find((group) => group.views.includes(key)) || null;
}

// 화면 하나를 메뉴에 싣는 꼴로: { view, href, name, title, icon, about, detail, words }
export function screen(view) {
  const one = SCREENS[view];
  return { view, href: `#${view}`, title: one.name, detail: "", ...one };
}

export const screensOf = (group) => group.views.map(screen);
// 메뉴에 실린 모든 화면(메뉴의 차례)
export const allScreens = () => GROUPS.flatMap(screensOf);
