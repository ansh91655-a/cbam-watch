// '새 소식 받아 보기' 창. RSS가 무엇이고 주소를 어디에 넣는지 알려 주고, 주소를 복사하게 한다.
import { copyButton } from "./copy.js";
import { openDialog } from "./dialog.js";
import { h } from "./dom.js";

// [이름, 파일, 무엇이 들어오는가]
const FEEDS = [
  ["새 소식", "feed.xml", "새로 실린 소식이 들어옵니다."],
  ["규제 변화", "rules.xml", "규제의 단계가 바뀌거나 연혁에 새 줄이 생기면 들어옵니다."],
];

function feedRow([name, file, about]) {
  const url = new URL(file, document.baseURI).href;
  return h("li", { class: "feed-row" }, [
    h("div", { class: "feed-text" }, [h("strong", { text: name }), h("span", { text: about })]),
    h("div", { class: "feed-url" }, [
      h("input", { type: "text", readonly: true, value: url, "aria-label": `${name} 주소`, onfocus: (event) => event.target.select() }),
      copyButton(url, "주소 복사"),
    ]),
  ]);
}

export function openSubscribe() {
  return openDialog("새 소식 받아 보기", [
    h("p", { text: "이 사이트에 들어오지 않아도 새 소식을 받아 볼 수 있게 RSS 주소를 내보내고 있습니다. 아래 주소를 RSS 구독 앱이나 협업 도구에 한 번 넣어 두면, 새 소식이 실릴 때마다 그곳에 올라옵니다." }),
    h("ul", { class: "feed-list" }, FEEDS.map(feedRow)),
    h("div", { class: "sheet-note" }, [
      h("p", { text: "넣는 곳" }),
      h("ul", {}, [
        h("li", { text: "RSS 구독 앱(Feedly, Inoreader 등): 구독 추가에 주소를 붙여 넣습니다." }),
        h("li", {}, ["Slack: RSS 앱을 더한 뒤 받을 채널에 ", h("code", { text: "/feed subscribe 주소" }), "를 보냅니다."]),
      ]),
    ]),
    h("p", { class: "count", text: "주소를 브라우저에서 바로 열면 기계가 읽는 글자(XML)가 보이는데, 정상입니다. 메일로 받아 보는 기능은 아직 없습니다." }),
  ]);
}
