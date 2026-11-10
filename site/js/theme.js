// 색 변형 고르기. 주소에 ?theme=navy, ?theme=white, ?theme=midnight를 붙이면 그 변형으로 보여 준다. 없으면 기본값이다.
// 화면이 그려지기 전에 정해야 깜박이지 않으므로 머리에서 먼저 실행한다(모듈이 아닌 보통 스크립트).
(function () {
  var THEMES = { navy: "네이비", white: "화이트", midnight: "미드나잇" };
  var DEFAULT = "navy"; // 변형을 정하면 이 값을 바꾼다
  var picked = null;
  try { picked = new URLSearchParams(location.search).get("theme"); } catch (error) { picked = null; }
  var key = THEMES[picked] ? picked : DEFAULT;
  document.documentElement.setAttribute("data-theme", key);
  // 브라우저의 주소창 색도 변형의 머리 색에 맞춘다.
  var BAR = { navy: "#071236", white: "#ffffff", midnight: "#060b22" };
  var meta = document.querySelector('meta[name="theme-color"]');
  if (meta) meta.setAttribute("content", BAR[key]);
  window.CBAM_THEME = { key: key, name: THEMES[key], preview: Boolean(THEMES[picked]) };
})();
