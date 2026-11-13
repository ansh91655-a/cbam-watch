// 달라진 곳 보기: 문서(법령이나 EU 집행위원회 문서)의 앞선 판과 뒤의 판에서 달라진 문단만 골라 옛 글과 새 글을 나란히 보여 준다.
// 주소는 #changes-<문서 id>이고, 대조가 여럿이면 #changes-<문서 id>.<몇 번째>로 지난 대조를 본다(1이 가장 새 것).
// 달라진 낱말에는 표시를 한다: 옛 글에서 빠진 말은 지운 줄로, 새 글에 들어온 말은 밑줄로(js/laws/worddiff.js).
// 자료는 사이트를 만들 때 받아 둔 두 판의 글을 문단마다 견줘 만든 것이다(tools/laws/revisions.py).
import * as data from "../data.js";
import { wordDiff } from "../laws/worddiff.js";
import { band } from "../ui/band.js";
import { empty, fill, h, safeLink } from "../ui/dom.js";
import { count } from "../ui/format.js";
import { icon } from "../ui/icons.js";
import { libraryTabs } from "../ui/tabs.js";

const OPS = [["", "전체"], ["changed", "바뀜"], ["added", "더해짐"], ["removed", "빠짐"]];
const OP_NAME = { changed: "바뀜", added: "더해짐", removed: "빠짐" };
const MODES = [["both", "원문과 국문"], ["en", "원문"], ["ko", "국문"]];
const FOLDED = { front: "제목과 근거", recitals: "전문", closing: "맺음", notes: "각주", cover: "표지와 일러두기" };
const isAct = (body) => (body.group || "act") === "act";

// 달라진 낱말에 표시를 한 글. tag는 옛 글이면 del, 새 글이면 ins다.
function marked(pieces, tag) {
  return pieces.map(([text, changed]) => (changed ? h(tag, { text }) : text));
}

// 글 하나(원문이나 국문)의 문단. 견줄 짝이 있으면 달라진 낱말에 표시를 한다.
function text(mine, other, side, lang) {
  if (!mine) return null;
  const pieces = other ? wordDiff(side === "old" ? mine : other, side === "old" ? other : mine)[side] : [[mine, false]];
  return h("p", { class: lang === "en" ? "chg-en" : "chg-ko", lang: lang === "en" ? "en" : null }, marked(pieces, side === "old" ? "del" : "ins"));
}

// 한쪽 칸: 그 판의 원문과 국문. pair는 [원문, 국문], other는 견줄 쪽의 것(없으면 null)
function cell(side, label, pair, other, row) {
  const name = h("span", { class: "chg-side", text: label });
  if (!pair) {
    return h("div", { class: "chg-cell chg-none", "data-side": side }, [name, h("p", { class: "chg-blank", text: row.op === "added" ? "앞선 판에는 없던 문단입니다." : "지금의 판에서 빠진 문단입니다." })]);
  }
  const [en, ko] = pair;
  const untranslated = !ko;
  return h("div", { class: "chg-cell", "data-side": side, "data-wait": untranslated || ko === en ? "" : null }, [
    name,
    text(en, other ? other[0] : "", side, "en"),
    untranslated ? h("p", { class: "chg-ko chg-wait", text: side === "old" ? "앞선 판의 이 문단은 아직 국문으로 옮기지 않았습니다." : "이 문단은 아직 국문으로 옮기지 않았습니다." })
      : (ko === en ? null : text(ko, other && other[1] && other[1] !== other[0] ? other[1] : "", side, "ko")),
  ]);
}

function rowNode(row, part, labels, actId) {
  const here = !part.gone && row.new && row.at ? h("a", { class: "chg-go", href: `#law-${actId}.${part.id}.${row.at}`, text: "지금의 글에서 보기" }) : null;
  return h("div", { class: "chg-row", "data-op": row.op }, [
    h("p", { class: "chg-tag" }, [h("span", { class: "chg-op", "data-op": row.op, text: OP_NAME[row.op] }), row.at === 0 ? h("span", { class: "count", text: "이름" }) : null, here]),
    h("div", { class: "chg-pair" }, [
      cell("old", labels.from, row.old || null, row.new || null, row),
      cell("new", labels.to, row.new || null, row.old || null, row),
    ]),
  ]);
}

function partName(part) {
  return part.kind in FOLDED ? FOLDED[part.kind] : [part.ko, part.titleKo || part.title || ""].filter(Boolean).join(" ");
}

function partNode(part, labels, actId) {
  const english = part.kind === "section" ? part.title : [part.label, part.title].filter(Boolean).join(" · ");
  const tally = ["changed", "added", "removed"].map((op) => [op, part.rows.filter((row) => row.op === op).length]).filter(([, size]) => size);
  return h("section", { class: "chg-part", id: `c-${part.id}`, "data-gone": part.gone ? "" : null }, [
    h("div", { class: "law-top" }, [
      h("h2", { class: "law-head" }, [
        h("span", { class: "law-no", text: part.ko }),
        part.titleKo ? h("span", { text: part.titleKo }) : null,
        english ? h("span", { class: "law-head-en", lang: "en", text: english }) : null,
      ]),
      h("div", { class: "law-head-tools" }, [
        h("span", { class: "count", text: tally.map(([op, size]) => `${OP_NAME[op]} ${size}`).join(", ") }),
        part.gone ? h("span", { class: "pill", "data-tone": "warn", text: "지금의 판에 없는 부분" }) : h("a", { class: "law-page", href: `#law-${actId}.${part.id}`, text: "지금의 글 보기" }),
      ]),
    ]),
    ...part.rows.map((row) => rowNode(row, part, labels, actId)),
  ]);
}

function toc(revision) {
  return h("nav", { class: "law-toc", "aria-label": "달라진 부분의 차례" }, h("ul", {}, revision.parts.map((part) =>
    h("li", { "data-kind": part.kind, "data-part": part.id }, h("a", { href: `#c-${part.id}`, onclick: (event) => {
      event.preventDefault();
      const node = document.getElementById(`c-${part.id}`);
      if (node) node.scrollIntoView({ block: "start" });
    } }, [h("span", { text: partName(part) }), h("span", { class: "law-toc-en", text: `${count(part.rows.length)}곳` })])))));
}

function seg(label, options, current, onPick) {
  const buttons = options.map(([key, text]) => h("button", { type: "button", text, "aria-pressed": String(key === current), onclick: () => {
    buttons.forEach((button, index) => button.setAttribute("aria-pressed", String(options[index][0] === key)));
    onPick(key);
  } }));
  return h("div", { class: "field" }, [h("span", { text: label }), h("div", { class: "seg", role: "group", "aria-label": label }, buttons)]);
}

export async function render(main, arg) {
  const [actId, nth = "1"] = String(arg || "").split(".");
  const acts = await data.laws();
  const act = acts.find((one) => one.id === actId);
  const body = act && act.changes ? await data.changes(actId) : null;   // 달라진 곳이 있는 문서만 자료를 받는다(없는 파일을 청하지 않는다)
  if (!body || !body.revisions || !body.revisions.length) {
    fill(main, band("달라진 곳", "", libraryTabs("laws")),
      empty(act ? "이 문서는 앞선 판을 받아 둔 것이 없어 견줄 수 없습니다. 문서가 새 판으로 바뀌면 달라진 곳을 여기에 싣습니다." : "이 문서를 찾지 못했습니다."),
      h("p", {}, h("a", { href: act ? `#law-${actId}` : "#laws", text: act ? "이 문서의 원문과 번역 보기" : "규정 원문의 목록으로" })));
    return "달라진 곳";
  }
  document.body.dataset.wide = "";
  const which = Math.min(Math.max(Number(nth) || 1, 1), body.revisions.length) - 1;
  const revision = body.revisions[which];
  const labels = { from: revision.from.label, to: revision.to.label };
  const stats = revision.stats;
  const list = h("div", { class: "chg-body", "data-mode": "both", "data-show": "" }, revision.parts.map((part) => partNode(part, labels, actId)));
  const none = h("p", { class: "empty", hidden: true, text: "고른 갈래의 문단이 없습니다." });
  const contents = toc(revision);
  const pick = (op) => {
    list.dataset.show = op;
    let shown = 0;
    const rows = new Map();   // 조각마다 고른 갈래의 문단 수. 차례도 이 수로 맞춘다(없는 조각은 숨긴다: 눌러도 갈 곳이 없다)
    for (const part of list.querySelectorAll(".chg-part")) {
      const mine = part.querySelectorAll(op ? `.chg-row[data-op="${op}"]` : ".chg-row").length;
      part.hidden = Boolean(op) && !mine;
      rows.set(part.id.replace(/^c-/, ""), mine);
      shown += op ? mine : 1;
    }
    for (const entry of contents.querySelectorAll("li[data-part]")) {
      const mine = rows.get(entry.dataset.part) || 0;
      entry.hidden = Boolean(op) && !mine;
      const tally = entry.querySelector(".law-toc-en");
      if (tally) tally.textContent = `${count(mine)}곳`;
    }
    none.hidden = shown > 0;
  };
  const source = safeLink(revision.from.url, "앞선 판의 원문 보기");
  if (source) source.append(icon("out", 14));
  fill(main,
    band(`${body.name}: 달라진 곳`, `${labels.from}과 ${labels.to}을 문단마다 견줬습니다.`, libraryTabs("laws")),
    h("div", { class: "law-bar" }, [
      h("p", { class: "crumbs" }, [h("a", { href: "#laws", text: "규정 원문" }), h("span", { text: "›" }), h("a", { href: `#law-${actId}`, text: body.name }), h("span", { text: "›" }), h("span", { text: "달라진 곳" })]),
      h("div", { class: "law-tools" }, [
        seg("볼 것", OPS, "", pick),
        seg("보는 글", MODES, "both", (mode) => { list.dataset.mode = mode; }),
      ]),
    ]),
    body.revisions.length > 1 ? h("nav", { class: "chips", "aria-label": "대조 고르기" }, body.revisions.map((one, index) =>
      h("a", { class: "chip", href: `#changes-${actId}.${index + 1}`, "aria-current": index === which ? "true" : null, text: `${one.from.label} → ${one.to.label}` }))) : null,
    h("div", { class: "law-note" }, [
      h("p", { class: "chg-stats" }, [
        h("span", {}, [h("span", { class: "chg-op", "data-op": "changed", text: "바뀜" }), h("b", { text: count(stats.changed) })]),
        h("span", {}, [h("span", { class: "chg-op", "data-op": "added", text: "더해짐" }), h("b", { text: count(stats.added) })]),
        h("span", {}, [h("span", { class: "chg-op", "data-op": "removed", text: "빠짐" }), h("b", { text: count(stats.removed) })]),
        h("span", { class: "count", text: `그대로인 문단 ${count(stats.same)}개, 달라진 부분 ${count(stats.parts)}곳` }),
      ]),
      h("p", { text: isAct(body)
        ? "조와 부속서의 글을 문단마다 견줬습니다. 전문과 각주는 견주지 않았고, 각주 번호나 줄바꿈만 다른 곳은 싣지 않았습니다. 통합본은 EU 출판국이 참고용으로 낸 글이며 법적 효력은 유럽연합 관보에 실린 글에 있습니다."
        : "본문의 글을 문단마다 견줬습니다. 표지와 각주 번호, 줄바꿈만 다른 곳은 싣지 않았습니다. 그림과 식은 원문 PDF에서 확인해 주십시오." }),
      h("p", { text: "옛 글에서 빠진 말은 지운 줄로, 새 글에 들어온 말은 밑줄로 표시했습니다. 국문은 이 사이트가 옮긴 비공식 번역입니다." }),
      h("p", { class: "law-note-links" }, [h("a", { href: `#law-${actId}`, text: "지금의 글을 원문과 번역으로 보기" }), source]),
    ]),
    h("div", { class: "law-layout" }, [contents, h("div", { class: "stack" }, [list, none])]),
    h("p", { class: "law-source", text: isAct(body)
      ? "원문: © European Union, EUR-Lex. 출처를 밝히고 재이용합니다. 번역: 이 사이트(용어집의 표기를 따릅니다)."
      : "원문: © European Union, EU 집행위원회 조세·관세동맹 총국. 출처를 밝히고 재이용합니다. 번역: 이 사이트(용어집의 표기를 따릅니다)." }),
  );
  return `${body.name}: 달라진 곳`;
}
