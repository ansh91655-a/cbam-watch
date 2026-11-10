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
        h("li", { text: "메일: RSS를 메일로 보내 주는 서비스(Blogtrottr, Feedrabbit 등)에 주소와 받을 메일 주소를 넣습니다." }),
      ]),
    ]),
    h("p", { class: "count", text: "주소를 브라우저에서 바로 열면 기계가 읽는 글자(XML)가 보이는데, 정상입니다. 이 사이트가 직접 메일을 보내지는 않습니다. 위에 든 앱과 서비스는 이 사이트와 관계없는 외부 서비스입니다." }),
  ]);
}
