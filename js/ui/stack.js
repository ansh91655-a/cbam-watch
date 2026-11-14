// 좁은 화면에서 표를 줄마다 한 칸씩 쌓아 보여 주게 한다. 칸마다 그 열의 머리글을 data-label로 적어 두면 CSS가 칸 앞에 이름을 붙인다.
// wideLast: 마지막 칸(긴 설명)을 한 줄 전체에 걸치게 한다.
export function stackable(wrap, { wideLast = false } = {}) {
  const labels = [...wrap.querySelectorAll("thead th")].map((cell) => cell.textContent);
  for (const row of wrap.querySelectorAll("tbody tr")) {
    [...row.children].forEach((cell, index) => cell.setAttribute("data-label", labels[index] || ""));
  }
  wrap.classList.add("table-stack");
  if (wideLast) wrap.classList.add("stack-wide-last");
  return wrap;
}
