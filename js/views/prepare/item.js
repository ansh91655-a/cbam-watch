// 준비 목록의 항목 한 줄: '확인함' 표시, 제목과 날짜, 글, 그리고 이어지는 곳(해설서의 절, 근거 조문, 일정, 사이트의 화면).
import { dutyHref } from "../../laws/refs.js";
import { h } from "../../ui/dom.js";
import { countdown, koreanDate } from "../../ui/format.js";
import { icon } from "../../ui/icons.js";
import { lawRefs } from "../../ui/lawrefs.js";

const NOTE_NAMES = { supplier: "생산자가 준비할 것", verifier: "검증기관이 알아 둘 것" };

// 날짜가 있는 항목의 날짜 표시: 날짜, 남은 날 수, 종류(기한·시행), 해마다
function when(row) {
  if (!row.duty) return [];
  const duty = row.duty;
  return [
    h("span", { class: "prep-date", id: `prep-when-${row.id}`, "data-tone": duty.kind === "기한" ? "due" : null }, [
      h("time", { datetime: duty.date, text: koreanDate(duty.date) }),
      h("span", { class: "prep-left", text: countdown(duty.date) }),
    ]),
    h("span", { class: "pill", text: duty.kind }),
    duty.repeat ? h("span", { class: "pill", text: "해마다" }) : null,
  ];
}

// 이어지는 곳(한 줄에 이어 놓고, 좁으면 줄을 바꾼다). dutyRefs는 그 일정의 근거 조문(항목이 근거를 따로 적지 않았을 때 쓴다)
function links(row, dutyRefs) {
  const refs = row.refs.length ? row.refs : (dutyRefs || []);
  const read = row.sections.length ? h("p", { class: "ref-links prep-read" }, [
    h("span", { class: "ref-name" }, [icon("guide", 14), h("span", { text: "해설서" })]),
    ...row.sections.map((section) => h("a", { href: section.href, title: `${section.chapter}: ${section.title}`, text: section.title })),
  ]) : null;
  const more = [
    row.duty ? h("a", { href: dutyHref(row.duty) }, [icon("calendar", 14), h("span", { text: "일정에서 보기" })]) : null,
    row.tool ? h("a", { href: row.tool.href }, [icon("next", 14), h("span", { text: row.tool.text })]) : null,
  ].filter(Boolean);
  return h("div", { class: "prep-ways" }, [read, lawRefs(refs, "근거 조문"), more.length ? h("p", { class: "prep-more" }, more) : null]);
}

// row는 plan.js의 resolve가 만든 꼴. done은 표시되어 있는지, onCheck(id, on)은 표시를 바꿀 때 부르는 함수.
export function itemRow(row, done, onCheck, dutyRefs) {
  // 화면 낭독기는 표시 칸에서 제목을 읽고, 날짜가 있으면 이어서 날짜와 남은 날 수를 읽는다
  const box = h("input", { type: "checkbox", class: "prep-box", "aria-label": `확인함: ${row.title}`, "aria-describedby": row.duty ? `prep-when-${row.id}` : null, checked: done || null });
  const node = h("li", { class: "prep-item", id: `prep-${row.id}`, tabindex: "-1", "data-done": done ? "true" : null, "data-past": row.past ? "true" : null }, [
    h("label", { class: "prep-check" }, box),
    h("div", { class: "prep-body" }, [
      h("p", { class: "prep-head" }, [h("strong", { text: row.title }), ...when(row)]),
      row.noteKind ? h("p", { class: "prep-text prep-noted" }, [h("b", { text: NOTE_NAMES[row.noteKind] || "" }), h("span", { text: row.text })]) : h("p", { class: "prep-text", text: row.text }),
      links(row, dutyRefs),
    ]),
  ]);
  box.addEventListener("change", () => {
    if (box.checked) node.dataset.done = "true"; else delete node.dataset.done;
    onCheck(row.id, box.checked);
  });
  return node;
}
