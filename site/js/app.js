// 시작 지점. 사이트 정보를 읽어 머리글과 바닥글을 채우고, 주소에 맞는 화면을 그린다.
import * as data from "./data.js";
import { markNav, onRoute } from "./router.js";
import { daysSince, minute } from "./ui/format.js";
import { empty, h } from "./ui/dom.js";
import { watch } from "./ui/motion.js";
import { navInk } from "./ui/navink.js";
import { scrollCue } from "./ui/scrollcue.js";
import { loadTopics } from "./ui/topics.js";
import { render as home } from "./views/home.js";
import { render as news } from "./views/news.js";
import { render as item } from "./views/item.js";
import { render as rules } from "./views/rules.js";
import { render as price } from "./views/price.js";
import { render as calendar } from "./views/calendar.js";
import { render as docs } from "./views/docs.js";
import { render as terms } from "./views/terms.js";
import { render as cn } from "./views/cn.js";
import { render as about } from "./views/about.js";
import { render as design } from "./views/design.js";

const VIEWS = { home, news, item, rules, price, calendar, docs, terms, cn, about, design };
// 브라우저 탭에 적는 화면 이름. 화면이 이름을 돌려주면(소식 하나의 제목 등) 그것을 쓴다.
const NAMES = { news: "소식", item: "소식", rules: "규제", price: "인증서 가격", calendar: "일정", docs: "원문 대장", terms: "용어집", cn: "품목 코드 조회", about: "안내", design: "색 변형" };
const SITE_NAME = "CBAM 규제동향";
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
      : `마지막 갱신 ${minute(site.builtAt)}`;
  } else {
    fresh.state = "bad";
    fresh.text = "게시 데이터를 읽지 못했습니다.";
  }
  stamp();
  document.getElementById("notice").textContent = site.notice || "";
  document.getElementById("independent").textContent = site.independent || "";
  // 만든 사람의 이름과 연락처. 주소는 설정 파일에 둘로 나눠 두고 여기에서 잇는다(자동 수집 프로그램에 덜 걸리도록).
  const maker = document.getElementById("maker");
  const address = site.maker && site.maker.user && site.maker.host ? `${site.maker.user}@${site.maker.host}` : "";
  if (address) {
    maker.replaceChildren(h("span", { text: `Made by ${site.maker.name || ""}`.trim() }), h("a", { href: `mailto:${address}`, text: address }));
    maker.hidden = false;
  }
  openFeatures(site.features || {}, address);
  const operator = document.getElementById("operator");
  if (site.operator) {
    operator.textContent = `운영 ${site.operator}`;
    operator.hidden = false;
  }
}

// 새 소식 받아 보기(구독 안내 창)와 의견 보내기(오른쪽 여백의 탭과 창). 설정(site.config.json의 features)에서 켠 것만 연다.
// 꺼 둔 기능은 단추도 만들지 않고 그 모듈도 불러오지 않는다. 지금은 둘 다 임시로 닫아 두었다.
async function openFeatures(features, address) {
  const subscribe = Boolean(features.subscribe);
  const feedback = Boolean(features.feedback) && Boolean(address);
  if (!subscribe && !feedback) return;
  const foot = document.getElementById("foot-feeds");
  foot.replaceChildren(...[
    subscribe ? h("button", { type: "button", class: "linklike", "data-open": "subscribe", text: "새 소식 받아 보기(RSS)" }) : null,
    feedback ? h("button", { type: "button", class: "linklike", "data-open": "feedback", text: "의견 보내기" }) : null,
  ].filter(Boolean));
  foot.hidden = false;
  if (subscribe) {  // 피드 리더가 주소를 찾을 수 있게 알린다
    for (const [title, href] of [["CBAM 규제동향: 새 소식", "feed.xml"], ["CBAM 규제동향: 규제 변화", "rules.xml"]]) {
      document.head.append(h("link", { rel: "alternate", type: "application/atom+xml", title, href }));
    }
  }
  if (feedback) {
    const { feedbackTab } = await import("./ui/feedback.js");
    const tab = feedbackTab(address);
    if (tab) document.body.append(tab);
  }
  // 화면이 바뀌면서 새로 그려지는 단추(data-open)도 듣도록 문서 전체에서 누름을 듣는다.
  document.addEventListener("click", async (event) => {
    const button = event.target instanceof Element ? event.target.closest("[data-open]") : null;
    if (!button) return;
    const kind = button.dataset.open;
    let opened = true;
    if (kind === "subscribe" && subscribe) opened = (await import("./ui/subscribe.js")).openSubscribe();
    if (kind === "feedback" && feedback) opened = (await import("./ui/feedback.js")).openFeedback(address);
    // 창을 띄울 수 없는 오래된 브라우저에서는 구독 주소나 메일 쓰기로 바로 보낸다.
    if (!opened) location.href = kind === "subscribe" ? "feed.xml" : `mailto:${address}`;
  });
}

// '본문으로 건너뛰기'는 주소를 바꾸지 않고 본문으로 초점만 옮긴다(주소가 바뀌면 화면을 다시 그리게 된다).
function wireSkip() {
  const skip = document.querySelector(".skip");
  if (!skip) return;
  skip.addEventListener("click", (event) => {
    event.preventDefault();
    const main = document.getElementById("main");
    main.focus();
    main.scrollIntoView();
  });
}

// 색 변형을 미리 보는 중이면 화면 아래에 어느 변형인지와 돌아갈 길을 보여 준다.
function previewBar() {
  const theme = window.CBAM_THEME || {};
  if (!theme.preview) return;
  document.body.append(h("div", { class: "preview-bar", role: "note" }, [
    h("span", { text: `'${theme.name}' 색으로 보는 중입니다.` }),
    h("a", { href: "#design", text: "다른 색 보기" }),
  ]));
}

// 주 메뉴의 밑줄을 옮기는 것과, 스크롤에 따라 바뀌는 것(머리글 그림자, 읽는 자리 표시, 맨 위로 가는 단추)
const placeInk = navInk(document.querySelector(".site-nav"));
const cueView = scrollCue();

async function show(route) {
  markNav(route.name);
  placeInk();
  const main = document.getElementById("main");
  let title = "";
  try {
    title = await VIEWS[route.name](main, route.arg);
  } catch (error) {
    main.replaceChildren(empty("화면을 그리지 못했습니다. 잠시 뒤에 다시 열어 주세요."));
  }
  document.title = [typeof title === "string" && title ? title : NAMES[route.name], SITE_NAME].filter(Boolean).join(" - ");
  stamp();
  watch(main);  // 새로 그린 것들이 화면에 들어올 때 차례로 나타나게 한다(ui/motion.js)
  cueView();
}

fillChrome();
wireSkip();
previewBar();
loadTopics().then(() => onRoute(show));
