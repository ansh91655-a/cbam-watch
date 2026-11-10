// 시작 지점. 데이터베이스를 한 번 읽어 화면을 그리고, 메뉴를 바꾸면 같은 데이터로 다시 그린다.
import { load } from "./model.js";
import { empty } from "./ui/dom.js";
import { minute } from "./ui/format.js";
import { render as summary } from "./views/summary.js";
import { render as holds } from "./views/holds.js";
import { render as items } from "./views/items.js";
import { render as runs } from "./views/runs.js";
import { render as candidates } from "./views/candidates.js";

const VIEWS = { summary, holds, items, runs, candidates };
let model = null;

function current() {
  const name = location.hash.replace(/^#/, "");
  return VIEWS[name] ? name : "summary";
}

function show() {
  const name = current();
  for (const link of document.querySelectorAll(".site-nav a")) {
    if (link.dataset.view === name) link.setAttribute("aria-current", "page");
    else link.removeAttribute("aria-current");
  }
  const main = document.getElementById("main");
  if (!model) return;
  VIEWS[name](main, model);
}

async function start() {
  const freshness = document.getElementById("freshness");
  try {
    model = await load();
    freshness.dataset.state = "ok";
    freshness.textContent = `데이터베이스를 읽음 ${minute(new Date(Date.now() + 9 * 3600000).toISOString())} · 새로 보려면 화면을 다시 여세요`;
  } catch (error) {
    freshness.dataset.state = "bad";
    freshness.textContent = "데이터베이스를 읽지 못했습니다. 이 화면의 주인 계정으로 로그인했는지 확인하세요.";
    document.getElementById("main").replaceChildren(empty("데이터베이스에 닿지 못했습니다."));
    return;
  }
  show();
}

window.addEventListener("hashchange", show);
start();
