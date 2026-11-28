// 입력 칸의 예시를 타자 치듯 바꿔 가며 보여 준다(품목 코드 조회). 무엇을 넣으면 되는지를 움직임으로 알린다.
// 칸에 글이 있거나 초점이 있으면 멈추고 처음의 예시로 돌아간다. 움직임 줄이기를 켠 사람에게는 처음의 예시만 보인다.
import { moving } from "./motion.js";

const TYPE_MS = 95;     // 한 글자를 치는 간격
const ERASE_MS = 45;    // 한 글자를 지우는 간격
const STAY_MS = 1900;   // 다 친 뒤에 머무는 시간
const GAP_MS = 420;     // 다 지운 뒤 다음 예시를 치기까지

// prefix는 늘 보이는 앞말("CN 코드 예: "), samples는 번갈아 보여 줄 예시들(첫째가 처음에 보이는 것).
export function typeHint(input, prefix, samples) {
  if (!moving() || samples.length < 2) return;
  let which = 0;
  let shown = samples[0].length;
  let typing = false;
  const show = () => input.setAttribute("placeholder", `${prefix}${samples[which].slice(0, shown)}`);
  const tick = () => {
    if (!input.isConnected) return;
    let wait;
    if (document.hidden || input.value || document.activeElement === input) {
      which = 0;
      shown = samples[0].length;
      typing = false;
      wait = STAY_MS;
    } else if (typing) {
      shown += 1;
      wait = TYPE_MS;
      if (shown >= samples[which].length) {
        typing = false;
        wait = STAY_MS;
      }
    } else {
      shown -= 1;
      wait = ERASE_MS;
      if (shown <= 0) {
        shown = 0;
        which = (which + 1) % samples.length;
        typing = true;
        wait = GAP_MS;
      }
    }
    show();
    window.setTimeout(tick, wait);
  };
  window.setTimeout(tick, STAY_MS);
}
