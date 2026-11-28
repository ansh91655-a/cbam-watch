// 수치 올리기. 글 안의 숫자 하나를 시작 값에서 제 값까지 짧게 올린다(끝나면 처음의 글로 되돌려 놓는다).
// 글의 앞뒤("+", "일 남음")와 소수 자릿수는 그대로 둔다. 시작 값은 data-count-from에 적고, 없으면 0에서 시작한다.
// 화면 낭독기에는 처음부터 제 값을 알린다(aria-label). 숫자가 없는 글("오늘")이면 아무것도 하지 않는다.
const NUMBER = /\d[\d,]*(?:\.\d+)?/;
const DURATION_MS = 950;

const ease = (t) => 1 - (1 - t) ** 3;

export function countUp(node, { delay = 0 } = {}) {
  const whole = node.textContent;
  const found = whole.match(NUMBER);
  if (!found || node.dataset.counting) return;
  const to = Number(found[0].replace(/,/g, ""));
  const start = Number(node.dataset.countFrom);
  const from = Number.isFinite(start) && node.dataset.countFrom !== "" && node.dataset.countFrom !== undefined ? Math.abs(start) : 0;
  if (!Number.isFinite(to) || to === from) return;
  const digits = (found[0].split(".")[1] || "").length;
  const grouped = found[0].includes(",");
  const head = whole.slice(0, found.index);
  const tail = whole.slice(found.index + found[0].length);
  const show = (value) => {
    const text = grouped ? value.toLocaleString("en-US", { minimumFractionDigits: digits, maximumFractionDigits: digits }) : value.toFixed(digits);
    node.textContent = `${head}${text}${tail}`;
  };
  node.dataset.counting = "true";
  const labelled = !node.hasAttribute("aria-label");
  if (labelled) node.setAttribute("aria-label", whole);
  show(from);
  let began = null;
  const step = (now) => {
    if (!node.isConnected) return;
    if (began === null) began = now + delay;
    const t = Math.min(Math.max((now - began) / DURATION_MS, 0), 1);
    if (t >= 1) {
      node.textContent = whole;
      delete node.dataset.counting;
      if (labelled) node.removeAttribute("aria-label");
      return;
    }
    show(from + (to - from) * ease(t));
    requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}
