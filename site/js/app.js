// 시작 지점. 사이트 정보를 읽어 머리글과 바닥글을 채우고, 주소에 맞는 화면을 그린다.
import * as data from "./data.js";
import { markNav, onRoute } from "./router.js";
import { daysSince, minute } from "./ui/format.js";
import { empty } from "./ui/dom.js";
import { render as home } from "./views/home.js";
import { render as news } from "./views/news.js";
import { render as docs } from "./views/docs.js";
import { render as calendar } from "./views/calendar.js";
import { render as terms } from "./views/terms.js";
import { render as sources } from "./views/sources.js";
import { render as about } from "./views/about.js";

const VIEWS = { home, news, docs, calendar, terms, sources, about };
const STALE_DAYS = 5; // 이보다 오래 갱신되지 않으면 머리글에 알린다.

async function fillChrome() {
  const site = await data.site();
  const stage = document.getElementById("stage");
  if (site.stage) {
    stage.textContent = site.stage;
    stage.hidden = false;
  }
  const freshness = document.getElementById("freshness");
  if (site.builtAt) {
    const age = daysSince(site.builtAt);
    const stale = age !== null && age > STALE_DAYS;
    freshness.dataset.state = stale ? "stale" : "ok";
    freshness.textContent = stale
      ? `마지막 갱신 ${minute(site.builtAt)} · ${age}일 동안 갱신되지 않았습니다. 최신 내용은 원문에서 확인하세요.`
      : `마지막 갱신 ${minute(site.builtAt)}${site.lastCollected ? ` · 출처 확인 ${minute(site.lastCollected)}` : ""}`;
  } else {
    freshness.dataset.state = "bad";
    freshness.textContent = "게시 데이터를 읽지 못했습니다.";
  }
  document.getElementById("notice").textContent = site.notice || "";
  const operator = document.getElementById("operator");
  if (site.operator) {
    operator.textContent = `운영 ${site.operator}`;
    operator.hidden = false;
  }
}

async function show(name) {
  markNav(name);
  const main = document.getElementById("main");
  try {
    await VIEWS[name](main);
  } catch (error) {
    main.replaceChildren(empty("화면을 그리지 못했습니다. 잠시 뒤에 다시 열어 주세요."));
  }
  window.scrollTo(0, 0);
}

fillChrome();
onRoute(show);
