// 시작 지점. 사이트 정보를 읽어 머리글과 바닥글을 채우고, 주소에 맞는 화면을 그린다.
import * as data from "./data.js";
import { markNav, onRoute } from "./router.js";
import { daysSince, minute } from "./ui/format.js";
import { empty, h } from "./ui/dom.js";
import { loadTopics } from "./ui/topics.js";
import { render as home } from "./views/home.js";
import { render as news } from "./views/news.js";
import { render as price } from "./views/price.js";
import { render as calendar } from "./views/calendar.js";
import { render as docs } from "./views/docs.js";
import { render as terms } from "./views/terms.js";
import { render as sources } from "./views/sources.js";
import { render as about } from "./views/about.js";
import { render as design } from "./views/design.js";

const VIEWS = { home, news, price, calendar, docs, terms, sources, about, design };
const STALE_DAYS = 5; // 이보다 오래 갱신되지 않으면 알린다.
const fresh = { text: "데이터를 읽는 중", state: "ok" };

// 화면마다 있는 '마지막 갱신' 자리를 채운다.
function stamp() {
  for (const node of document.querySelectorAll("[data-fresh], #freshness")) {
    node.textContent = fresh.text;
    node.dataset.state = fresh.state;
  }
}

async function fillChrome() {
  const site = await data.site();
  const stage = document.getElementById("stage");
  if (site.stage) {
    stage.textContent = site.stage;
    stage.hidden = false;
  }
  if (site.builtAt) {
    const age = daysSince(site.builtAt);
    const stale = age !== null && age > STALE_DAYS;
    fresh.state = stale ? "stale" : "ok";
    fresh.text = stale
      ? `마지막 갱신 ${minute(site.builtAt)}. ${age}일 동안 갱신되지 않았습니다. 최신 내용은 원문에서 확인하세요.`
      : `마지막 갱신 ${minute(site.builtAt)}${site.lastCollected ? `, 출처 확인 ${minute(site.lastCollected)}` : ""}`;
  } else {
    fresh.state = "bad";
    fresh.text = "게시 데이터를 읽지 못했습니다.";
  }
  stamp();
  document.getElementById("notice").textContent = site.notice || "";
  document.getElementById("independent").textContent = site.independent || "";
  const operator = document.getElementById("operator");
  if (site.operator) {
    operator.textContent = `운영 ${site.operator}`;
    operator.hidden = false;
  }
}

// 색 변형을 미리 보는 중이면 화면 아래에 어느 변형인지와 돌아갈 길을 보여 준다.
function previewBar() {
  const theme = window.CBAM_THEME || {};
  if (!theme.preview) return;
  document.body.append(h("div", { class: "preview-bar", role: "note" }, [
    h("span", { text: `'${theme.name}' 변형을 미리 보는 중입니다.` }),
    h("a", { href: "#design", text: "다른 변형 보기" }),
  ]));
}

async function show(route) {
  markNav(route.name);
  const main = document.getElementById("main");
  try {
    await VIEWS[route.name](main, route.arg);
  } catch (error) {
    main.replaceChildren(empty("화면을 그리지 못했습니다. 잠시 뒤에 다시 열어 주세요."));
  }
  stamp();
  window.scrollTo(0, 0);
}

fillChrome();
previewBar();
loadTopics().then(() => onRoute(show));
