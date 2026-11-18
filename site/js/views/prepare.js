// 역할별 준비 목록. 역할(신고인·수입자, 제3국 사업자, 검증기관, 영국 수입자)마다 법령이 정한 일을 차례로 놓고,
// 항목마다 해설서의 절과 근거 조문, 의무 일정으로 잇는다. 글은 해설서와 의무 일정에서 온 것이다(tools/publish/prepare.py가 대조한다).
// 주소: #prepare(첫 역할), #prepare-<역할>, #prepare-<역할>.<항목>(그 항목으로 옮겨 가 잠깐 표시한다).
// '확인함' 표시는 이 브라우저에만 남는다(js/prepare/done.js. 저장소를 쓸 수 없으면 화면을 떠날 때까지만 기억한다). 항목 한 줄은 views/prepare/item.js, 다가오는 날짜는 views/prepare/soon.js가 그린다.
import * as data from "../data.js";
import { cleared, keeper, pruned, toggled } from "../prepare/done.js";
import { hrefOf, itemsOf, placeOf, progress, resolve, upcoming } from "../prepare/plan.js";
import { rename } from "../router.js";
import { band } from "../ui/band.js";
import { empty, fill, h } from "../ui/dom.js";
import { today } from "../ui/format.js";
import { icon } from "../ui/icons.js";
import { groupTabs } from "../ui/tabs.js";
import { itemRow } from "./prepare/item.js";
import { soon } from "./prepare/soon.js";

const TITLE = "역할별 준비 목록";
const FLASH_MS = 2200;

function storage() {
  try { return window.localStorage; } catch (error) { return null; }
}

// 그 항목으로 옮겨 가 잠깐 표시한다
function reach(id) {
  const node = document.getElementById(`prep-${id}`);
  if (!node) return;
  const calm = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  node.scrollIntoView({ block: "center", behavior: calm ? "auto" : "smooth" });
  node.dataset.flash = "true";
  node.focus({ preventScroll: true });
  setTimeout(() => { delete node.dataset.flash; }, FLASH_MS);
}

export async function render(main, arg) {
  const [book, duties, refs] = await Promise.all([data.prepare(), data.duties(), data.refs()]);
  const roles = book.roles || [];
  if (!roles.length) {
    fill(main, band(TITLE, "", groupTabs("prepare")), empty("준비 목록을 읽지 못했습니다."));
    return TITLE;
  }
  const place = placeOf(arg, roles);
  const role = roles.find((one) => one.key === place.role);
  if (arg && String(arg).split(".")[0] !== role.key) rename(hrefOf(roles, role.key));   // 없는 역할을 적은 주소는 첫 역할의 주소로 고쳐 둔다
  const now = today();
  const keep = keeper(storage());
  const known = new Set(roles.flatMap(itemsOf).map((item) => item.id));   // 모든 역할의 항목(없어진 항목의 표시는 적을 때 거른다)
  let done = keep.read();
  const rowsByGroup = (role.groups || []).map((group) => ({ name: group.name, rows: (group.items || []).map((item) => resolve(item, duties.duties, now)) }));
  const rows = rowsByGroup.flatMap((group) => group.rows);
  const state = h("span", { class: "count", role: "status" });
  const clear = h("button", { type: "button", class: "linklike", text: "표시 지우기" });
  const counts = rowsByGroup.map(() => h("span", { class: "count" }));

  const ahead = upcoming(rows, now, 1)[0];
  const dutyYear = ahead ? ahead.date.slice(0, 4) : now.slice(0, 4);

  function tell() {
    const all = progress(rows, done);
    state.textContent = all.done ? `확인한 항목 ${all.done}/${all.all}` : `항목 ${all.all}개`;
    clear.hidden = !all.done;
    rowsByGroup.forEach((group, at) => {
      const part = progress(group.rows, done);
      counts[at].textContent = part.done ? `${part.done}/${part.all}` : `${part.all}개`;
    });
  }

  // 화면의 표시와 수를 지금의 묶음에 맞춘다(다른 탭에서 한 표시도 여기서 드러난다)
  function show() {
    for (const node of main.querySelectorAll(".prep-item")) {
      const on = done.has(node.id.slice("prep-".length));
      if (on) node.dataset.done = "true"; else delete node.dataset.done;
      node.querySelector(".prep-box").checked = on;
    }
    tell();
  }

  // 적기 전에 저장소를 다시 읽는다(다른 탭에서 한 표시를 덮어쓰지 않게)
  function check(id, on) {
    done = pruned(toggled(keep.read(), id, on), known);
    keep.write(done);
    show();
  }

  clear.addEventListener("click", () => {
    done = pruned(cleared(keep.read(), rows.map((row) => row.id)), known);
    keep.write(done);
    show();
    state.focus();
  });
  state.tabIndex = -1;

  fill(main,
    band(TITLE, book.lead || "", groupTabs("prepare")),
    h("nav", { class: "chips prep-roles", "aria-label": "역할 고르기" }, roles.map((one) =>
      h("a", { class: "chip", href: hrefOf(roles, one.key), "aria-current": one.key === role.key ? "true" : null }, [
        h("span", { text: one.name }), h("span", { class: "n", text: itemsOf(one).length }),
      ]))),
    role.about ? h("p", { class: "prep-about", text: role.about }) : null,
    soon(upcoming(rows, now), reach, (id) => hrefOf(roles, role.key, id)),
    h("div", { class: "prep-bar" }, [
      h("div", { class: "prep-state" }, [state, clear]),
      h("button", { type: "button", class: "btn", onclick: () => window.print() }, [icon("download", 15), h("span", { text: "인쇄하거나 PDF로 저장" })]),
    ]),
    rowsByGroup.map((group, at) => h("section", { class: "prep-group", "aria-labelledby": `h-prep-${at}` }, [
      h("div", { class: "sec-head" }, [h("h2", { id: `h-prep-${at}`, text: group.name }), counts[at]]),
      h("ol", { class: "prep-list" }, group.rows.map((row) => itemRow(row, done.has(row.id), check, row.duty ? (refs.duties || {})[row.duty.id] : null))),
    ])),
    h("p", { class: "prep-note" }, [
      h("span", { text: book.note || "" }),
      h("span", { text: " 확인함 표시는 이 브라우저에만 남고 사이트로 보내지 않습니다." }),
    ]),
    h("p", { class: "prep-links" }, [
      h("a", { href: `#calendar-${dutyYear}.role-${role.key}` }, [icon("calendar", 15), h("span", { text: `${role.name}의 의무 일정` })]),
      h("a", { href: role.key === "uk" ? "#handbook-uk" : "#handbook-roles" }, [icon("guide", 15), h("span", { text: role.key === "uk" ? "해설서: 영국 CBAM" : "해설서: 누가 무엇을 하는지" })]),
    ]),
  );
  tell();
  if (place.item) {
    // 항목까지 적힌 주소로 왔으면 그 항목으로 옮겨 가고, 주소에서는 항목을 뗀다(돌아왔을 때 다시 표시하지 않게)
    setTimeout(() => { reach(place.item); rename(hrefOf(roles, role.key)); }, 0);
  }
  return `${TITLE}: ${role.name}`;
}
