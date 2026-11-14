// 새 소식 한 줄. 가장 최근의 소식 제목 몇 개를 한 줄에 하나씩 차례로 보여 준다(첫 화면의 큰 머리).
// 가리키거나 초점을 두면 멈추고, 탭이 가려져 있으면 넘기지 않는다. 움직임 줄이기를 켠 사람에게는 첫 줄만 보여 준다.
// 보이는 줄만 초점을 받고 읽힌다. 같은 소식은 아래의 '최근 소식'에도 모두 있다.
import { h } from "./dom.js";
import { day } from "./format.js";
import { hasPage } from "./itemlink.js";
import { moving } from "./motion.js";

const EVERY_MS = 4200;
const LINES = 5;

function line(item, index) {
  const when = item.published || item.listed;
  const href = hasPage(item) ? `#item-${item.id}` : "#news";
  return h("a", { class: "ticker-line", href, "data-on": index === 0 ? "true" : null, tabindex: index === 0 ? null : "-1", "aria-hidden": index === 0 ? null : "true" }, [
    when ? h("time", { datetime: day(when), text: day(when).slice(5) }) : null,
    h("span", { text: item.title }),
  ]);
}

export function ticker(items) {
  const picked = items.slice(0, LINES);
  if (!picked.length) return null;
  const lines = picked.map(line);
  const root = h("div", { class: "ticker", role: "group", "aria-label": "방금 올라온 소식" }, [
    h("span", { class: "ticker-tag" }, [h("i", { "aria-hidden": "true" }), "새 소식"]),
    h("div", { class: "ticker-view" }, lines),
  ]);
  if (lines.length < 2 || !moving()) return root;
  let at = 0;
  let held = false;
  const hold = (value) => () => { held = value; };
  root.addEventListener("pointerenter", hold(true));
  root.addEventListener("pointerleave", hold(false));
  root.addEventListener("focusin", hold(true));
  root.addEventListener("focusout", hold(false));
  const timer = window.setInterval(() => {
    if (!root.isConnected) { window.clearInterval(timer); return; }
    if (held || document.hidden) return;
    const before = lines[at];
    at = (at + 1) % lines.length;
    const now = lines[at];
    for (const node of lines) node.removeAttribute("data-off");
    before.removeAttribute("data-on");
    before.setAttribute("data-off", "true");
    before.setAttribute("tabindex", "-1");
    before.setAttribute("aria-hidden", "true");
    now.setAttribute("data-on", "true");
    now.removeAttribute("tabindex");
    now.removeAttribute("aria-hidden");
  }, EVERY_MS);
  return root;
}
