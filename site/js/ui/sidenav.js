// 화면 왼쪽의 고르기(.side-nav: 소식의 주제, 규제의 묶음). 좁은 화면에서는 가로로 넘겨 보는 줄이 된다(css/components.css).
// 고른 것이 줄의 밖에 있으면(끝에 있는 '국내 공지·자료', '최근 변화') 보이는 자리로 옮긴다. 화면을 그린 뒤에 app.js가 부른다.
export function showPicked(root) {
  for (const nav of root.querySelectorAll(".side-nav")) {
    const on = nav.querySelector('[aria-current="true"]');
    if (!on || nav.scrollWidth <= nav.clientWidth) continue;
    const left = on.getBoundingClientRect().left - nav.getBoundingClientRect().left;   // 줄의 왼쪽 끝에서 고른 것까지
    nav.scrollLeft = Math.max(0, nav.scrollLeft + left - (nav.clientWidth - on.offsetWidth) / 2);
  }
}
