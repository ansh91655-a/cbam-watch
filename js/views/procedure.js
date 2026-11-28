// 입법 절차. EU의 법이 누구의 손을 거쳐 어떤 차례로 만들어지는지를 풀이하고, 진행 중인 규제가 지금 어느 단계에 있는지를 한곳에 모아 보여 준다.
// 글과 근거는 data/procedures.json에 있고(tools/publish/procedures.py가 검사해 싣는다), 규제마다의 단계는 규제 자료의 진행도에서 온다.
// 주소: #procedure(처음부터), #procedure-board(진행 중인 규제), #procedure-who(기관), #procedure-who.<기관>, #procedure-acts(법령의 종류), #procedure-acts.<종류>,
//       #procedure-<절차>(그 절차), #procedure-<절차>.<단계>(그 절차의 그 단계). 글 속 용어 풀이와 규제 화면의 '세부 절차'가 이 주소들로 이어진다.
// 진행 중인 규제는 views/procedure/board.js, 기관은 who.js, 법령의 종류는 acts.js, 절차는 kind.js가 그린다.
import * as data from "../data.js";
import { kindOf } from "../procedure/model.js";
import { band } from "../ui/band.js";
import { empty, fill, h } from "../ui/dom.js";
import { icon } from "../ui/icons.js";
import { groupTabs } from "../ui/tabs.js";
import { acts } from "./procedure/acts.js";
import { board } from "./procedure/board.js";
import { kinds } from "./procedure/kind.js";
import { who } from "./procedure/who.js";

const TITLE = "입법 절차";
const FLASH_MS = 1800;
const PARTS = { board: "pr-board", who: "pr-who", acts: "pr-acts" };   // 주소의 이름 → 그 자리의 id

// 주소가 가리키는 자리의 id. 절차의 이름이면 절차의 자리, 단계까지 적혀 있으면 그 단계.
function target(book, section, part) {
  if (section in PARTS) return part ? `${PARTS[section]}-${part}` : PARTS[section];
  const kind = kindOf(book, section);
  if (!kind) return "";
  return part && kind.steps.some((step) => step.key === part) ? `pr-step-${kind.key}-${part}` : "pr-kinds";
}

// 그 자리로 옮겨 가 잠깐 표시한다(주소로 바로 왔을 때 화면 낭독기가 그 자리부터 읽도록 초점도 옮긴다)
function reach(id) {
  const node = id ? document.getElementById(id) : null;
  if (!node) return;
  node.scrollIntoView({ block: "start" });
  node.focus({ preventScroll: true });
  node.dataset.flash = "true";
  setTimeout(() => { delete node.dataset.flash; }, FLASH_MS);
}

// 왼쪽의 차례: 이 화면의 네 묶음과 절차들
function side(book, section, picked) {
  const link = (href, on, picture, name) => h("a", { href, "aria-current": on ? "true" : null },
    [h("span", { class: "chipicon" }, icon(picture, 17)), h("span", { text: name }), h("span", { class: "n" })]);
  return h("nav", { class: "side-nav", "aria-label": "입법 절차 화면의 차례" }, [
    link("#procedure-board", section === "board" || !section, "clock", "진행 중인 규제"),
    link("#procedure-who", section === "who", "who", "기관"),
    link("#procedure-acts", section === "acts", "law", "법령의 종류"),
    ...book.kinds.map((kind, index) => {
      const one = link(`#procedure-${kind.key}`, picked === kind.key, "procedure", kind.name);
      if (!index) one.classList.add("side-apart");
      return one;
    }),
  ]);
}

export async function render(main, arg) {
  const [book, body] = await Promise.all([data.procedures(), data.regulations()]);
  if (!book.kinds.length) {
    fill(main, band(TITLE, "", groupTabs("procedure")), empty("입법 절차 자료를 불러오지 못했습니다. 잠시 뒤에 다시 열어 주세요."));
    return TITLE;
  }
  const [section, part = ""] = String(arg || "").split(".");
  const rules = body.regulations || [];
  const picked = kindOf(book, section) ? section : "";
  fill(main,
    band(TITLE, book.lead, groupTabs("procedure")),
    h("div", { class: "with-side proc-page" }, [
      h("aside", { class: "side" }, side(book, section, picked)),
      h("div", { class: "stack-l" }, [board(book, rules), who(book, rules), acts(book), kinds(book, picked, rules)]),
    ]),
  );
  // 화면을 바꾼 뒤에는 맨 위에서 시작하므로(router.js), 그다음에 주소가 가리키는 자리로 옮겨 간다
  const id = target(book, section, part);
  if (id) setTimeout(() => reach(id), 0);
  const kind = kindOf(book, section);
  return kind ? `${kind.name} - ${TITLE}` : TITLE;
}
