// 출처. 이 사이트가 살펴보는 기관과 화면의 목록이다.
import * as data from "../data.js";
import { band } from "../ui/band.js";
import { fill, h, safeLink, table } from "../ui/dom.js";
import { stackable } from "../ui/stack.js";

const TIER = { A: "EU 공식", B: "공공기관", C: "민간·협회" };

export async function render(main) {
  const sources = await data.sources();
  const groups = [...new Set(sources.map((source) => source.group))];
  const sections = groups.map((group) => h("section", { class: "stack" }, [
    h("h2", { text: group }),
    stackable(table(["출처", "성격"], sources.filter((source) => source.group === group).map((source) => h("tr", {}, [
      h("td", {}, [safeLink(source.url, source.name) || h("span", { text: source.name }), source.note ? h("p", { class: "count", text: source.note }) : null]),
      h("td", { text: TIER[source.tier] || "" }),
    ])))),
  ]));
  fill(main,
    band("출처", "이 사이트가 살펴보는 기관과 화면입니다. 민간·협회 자료는 제목과 링크만 싣습니다."),
    ...sections,
  );
}
