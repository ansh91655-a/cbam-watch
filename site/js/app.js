// 시작 지점. 사이트 정보를 읽어 머리글과 바닥글을 채우고, 주소에 맞는 화면을 그린다.
import * as data from "./data.js";
import { markNav, onRoute } from "./router.js";
import { daysSince, minute } from "./ui/format.js";
import { empty, h } from "./ui/dom.js";
import { feedbackTab, openFeedback } from "./ui/feedback.js";
import { openSubscribe } from "./ui/subscribe.js";
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
  setContact(address);
  const operator = document.getElementById("operator");
  if (site.operator) {
    operator.textContent = `운영 ${site.operator}`;
    operator.hidden = false;
  }
}

// 구독 안내와 의견 보내기 창을 여는 단추(data-open). 바닥글과 안내 화면에 있고, 오른쪽 여백에는 의견 보내기 탭을 붙인다.
// 화면이 바뀌면서 새로 그려지는 단추도 듣도록 문서 전체에서 누름을 듣는다.
const contact = { address: "" };

function wireOpeners() {
  document.addEventListener("click", (event) => {
    const button = event.target instanceof Element ? event.target.closest("[data-open]") : null;
    if (!button) return;
    const kind = button.dataset.open;
    const opened = kind === "subscribe" ? openSubscribe() : (kind === "feedback" ? openFeedback(contact.address) : true);
    // 창을 띄울 수 없는 오래된 브라우저에서는 구독 주소나 메일 쓰기로 바로 보낸다.
    if (!opened) location.href = kind === "subscribe" ? "feed.xml" : `mailto:${contact.address}`;
  });
}

// 연락할 주소를 알게 되면 의견 보내기를 켠다. 주소가 없으면 바닥글의 단추를 감춘다.
function setContact(address) {
  contact.address = address;
  for (const button of document.querySelectorAll(".site-foot [data-open='feedback']")) button.hidden = !address;
  const tab = feedbackTab(address);
  if (tab) document.body.append(tab);
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

async function show(route) {
  markNav(route.name);
  const main = document.getElementById("main");
  let title = "";
  try {
    title = await VIEWS[route.name](main, route.arg);
  } catch (error) {
    main.replaceChildren(empty("화면을 그리지 못했습니다. 잠시 뒤에 다시 열어 주세요."));
  }
  document.title = [typeof title === "string" && title ? title : NAMES[route.name], SITE_NAME].filter(Boolean).join(" - ");
  stamp();
}

fillChrome();
wireOpeners();
wireSkip();
previewBar();
loadTopics().then(() => onRoute(show));
