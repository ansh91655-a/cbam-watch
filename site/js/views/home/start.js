// 첫 화면의 길잡이. 처음 온 사람이 무엇부터 보면 되는지를 네 갈래로 알려 주고, 모든 화면을 펼쳐 보는 '전체 메뉴'로 잇는다.
// '접기'를 누르면 이 브라우저에서는 다시 보이지 않는다(브라우저의 저장소에 적어 둔다. 적지 못하는 환경에서는 그때만 접힌다).
import { h } from "../../ui/dom.js";
import { icon } from "../../ui/icons.js";

const KEY = "cbam.start.closed";
const WAYS = [
  { href: "#handbook", icon: "guide", title: "CBAM이 무엇인지", text: "제도가 돌아가는 차례를 해설서로 익힙니다." },
  { href: "#cn", icon: "search", title: "내 품목이 대상인지", text: "CN 코드로 대상 여부와 근거를 확인합니다." },
  { href: "#calc", icon: "emissions", title: "인증서가 얼마나 드는지", text: "품목과 물량으로 인증서 수와 비용을 어림합니다." },
  { href: "#calendar", icon: "calendar", title: "언제까지 무엇을 하는지", text: "신고 기한과 의무 일정을 달력으로 봅니다." },
];

function closed() {
  try { return localStorage.getItem(KEY) === "1"; } catch (error) { return false; }
}

function remember() {
  try { localStorage.setItem(KEY, "1"); } catch (error) { /* 적지 못해도 이번에는 접힌다 */ }
}

export function startGuide() {
  if (closed()) return null;
  const fold = () => {
    remember();
    node.remove();
    const main = document.getElementById("main");
    if (main) main.focus({ preventScroll: true });  // 초점이 사라진 단추에 남지 않게 본문으로 옮긴다
  };
  const node = h("section", { class: "start", "aria-labelledby": "h-start" }, [
    h("div", { class: "sec-head" }, [
      h("h2", { id: "h-start", text: "처음 오신 분께" }),
      h("span", { class: "start-tools" }, [
        h("button", { type: "button", class: "linklike", "data-open": "menu", text: "전체 메뉴 보기" }),
        h("button", { type: "button", class: "linklike", onclick: fold, text: "접기" }),
      ]),
    ]),
    h("div", { class: "start-ways" }, WAYS.map((way) => h("a", { class: "start-way", href: way.href }, [
      h("span", { class: "chipicon" }, icon(way.icon, 20)),
      h("span", { class: "start-text" }, [h("b", { text: way.title }), h("span", { text: way.text })]),
      icon("next", 16),
    ]))),
  ]);
  return node;
}
