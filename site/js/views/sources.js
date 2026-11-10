// 출처. 어디를 얼마나 자주 확인하는지와 마지막 확인 결과를 보여 준다.
import * as data from "../data.js";
import { band } from "../ui/band.js";
import { fill, h, pill, safeLink, table } from "../ui/dom.js";
import { minute } from "../ui/format.js";
import { stackable } from "../ui/stack.js";

const TIER = { A: "EU 공식", B: "공공기관", C: "민간·협회" };
const HOW = { github: "자동 수집", claude: "자동 열람", off: "준비 중" };

function statusPill(source) {
  if (source.collector === "off") return pill("준비 중", "warn");
  if (source.ok === true) return pill("정상", "ok");
  if (source.ok === false) return source.failCount >= 3 ? pill("확인 못 함", "bad") : pill("확인 지연", "warn");
  return pill("확인 전");
}

export async function render(main) {
  const sources = await data.sources();
  const groups = [...new Set(sources.map((source) => source.group))];
  const sections = groups.map((group) => h("section", { class: "stack" }, [
    h("h2", { text: group }),
    stackable(table(["출처", "성격", "확인 방법", { text: "마지막 확인", num: true }, "상태"], sources.filter((source) => source.group === group).map((source) => h("tr", {}, [
      h("td", {}, [safeLink(source.url, source.name) || h("span", { text: source.name }), source.note ? h("p", { class: "count", text: source.note }) : null]),
      h("td", { text: TIER[source.tier] || "" }),
      h("td", { text: HOW[source.collector] || "" }),
      h("td", { class: "num", text: minute(source.lastChecked) }),
      h("td", {}, statusPill(source)),
    ])))),
  ]));
  fill(main,
    band("출처", "평일마다 아래 출처를 확인해 새로 올라오거나 바뀐 내용을 찾습니다. 민간·협회 자료는 제목과 링크만 다루고 본문을 옮기지 않습니다. 확인이 세 번 이어서 실패하면 '확인 못 함'으로 표시합니다."),
    ...sections,
  );
}
