// 디자인 시안 고르기. 주소에 ?theme=1~5를 붙이면 그 시안으로 보여 준다. 없으면 기본 시안이다.
// 화면이 그려지기 전에 정해야 깜박이지 않으므로 머리에서 먼저 실행한다(모듈이 아닌 보통 스크립트).
(function () {
  var THEMES = {
    "1": { name: "표준형", fonts: "Noto+Sans+KR:wght@400;500;700" },
    "2": { name: "관보형", fonts: "Noto+Serif+KR:wght@500;600;700&family=Noto+Sans+KR:wght@400;500;700" },
    "3": { name: "깃발형", fonts: "Gothic+A1:wght@400;500;700;800" },
    "4": { name: "계기판형", fonts: "IBM+Plex+Sans+KR:wght@400;500;600;700" },
    "5": { name: "통관 서류형", fonts: "Nanum+Gothic:wght@400;700;800" }
  };
  var DEFAULT = "3"; // 시안을 정하면 이 값을 바꾼다
  var picked = null;
  try { picked = new URLSearchParams(location.search).get("theme"); } catch (error) { picked = null; }
  var key = THEMES[picked] ? picked : DEFAULT;
  document.documentElement.setAttribute("data-theme", key);
  var link = document.createElement("link");
  link.rel = "stylesheet";
  link.href = "https://fonts.googleapis.com/css2?family=" + THEMES[key].fonts + "&display=swap";
  document.head.appendChild(link);
  window.CBAM_THEME = { key: key, name: THEMES[key].name, preview: Boolean(THEMES[picked]), fallback: DEFAULT };
})();
