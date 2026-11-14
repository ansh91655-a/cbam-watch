// 문단이나 조각(조, 절, 부속서) 하나를 인용하는 글을 만든다. 붙여 넣으면 원문, 국문, 출처(문서·조·쪽), 주소가 한 번에 들어간다.
// 화면 요소를 다루지 않으므로 node로 시험한다(tests/test_sitejs.py).
//
// 글의 꼴(문단 하나)
//   [원문] By 30 September of each year, …
//   [국문] 매년 9월 30일까지 …
//   [출처] CBAM 규정 제6조 CBAM 신고 (Regulation (EU) 2023/956, 2025-10-20 통합본)
//   [주소] https://…/#law-32023R0956.art-6.2
//   ※ 국문은 CBAM 규제동향이 옮긴 비공식 번역입니다.
// 아직 옮기지 않은 문단은 [국문] 줄과 마지막 줄이 없다.

const SITE = "CBAM 규제동향";
const NOTE = `※ 국문은 ${SITE}이 옮긴 비공식 번역입니다.`;
const CUT = "※ 이 부속서는 앞부분만 실려 있습니다. 전체는 EUR-Lex의 원문에서 확인하세요.";
const isAct = (act) => (act.group || "act") === "act";
const FOLDED = { front: "제목과 근거", recitals: "전문", closing: "맺음", notes: "각주", cover: "표지와 일러두기" };

// 조각의 이름: "제6조 CBAM 신고", "부속서 IV 내재배출량의 산정 방법", "4.3.1 생산공정에 관한 확정기간 규칙"
export function partName(part) {
  if (!part) return "";
  if (FOLDED[part.kind]) return FOLDED[part.kind];
  return [part.ko, part.titleKo || part.title || ""].filter(Boolean).join(" ");
}

// 출처 한 줄. page는 그 문단이 있는 PDF의 쪽(없으면 조각이 시작하는 쪽).
export function source(act, part, page) {
  const where = [act.name, partName(part)].filter(Boolean).join(" ");
  const sheet = !isAct(act) && page ? `, PDF ${page}쪽` : "";
  const edition = isAct(act) ? (act.consolidated ? `${act.consolidated} 통합본` : "") : ["EU 집행위원회", act.received ? `${act.received}에 받은 판` : ""].filter(Boolean).join(", ");
  const detail = [act.official, edition].filter(Boolean).join(", ");
  return `${where}${sheet}${detail ? ` (${detail})` : ""}`;
}

// 그 자리로 바로 가는 주소. at은 조각 안에서 몇 번째 문단인지(1부터). 주지 않으면 조각의 머리로 간다.
export function address(base, act, part, at = 0) {
  return `${String(base || "").replace(/#.*$/, "")}#law-${act.id}.${part.id}${at ? `.${at}` : ""}`;
}

function pageOf(part, index) {
  return (part.pages && part.pages[index]) || part.page || 0;
}

// 문단 하나를 인용하는 글. index는 조각의 blocks에서의 차례(0부터).
export function citeBlock(act, part, index, base) {
  const [en, ko] = part.blocks[index] || ["", ""];
  const translated = Boolean(ko) && ko !== en;
  return [
    `[원문] ${en}`,
    translated ? `[국문] ${ko}` : null,
    `[출처] ${source(act, part, pageOf(part, index))}`,
    `[주소] ${address(base, act, part, index + 1)}`,
    translated ? NOTE : null,
  ].filter(Boolean).join("\n");
}

// 조각 하나(조, 절, 부속서)를 통째로 인용하는 글: 원문을 모두 적고, 이어서 국문을 모두 적는다.
export function citePart(act, part, base) {
  const english = part.blocks.map(([en]) => en).filter(Boolean);
  const korean = part.blocks.map(([en, ko]) => ko || en).filter(Boolean);
  const translated = part.blocks.some(([en, ko]) => Boolean(ko) && ko !== en);
  const head = [partName(part), part.kind in FOLDED ? "" : [part.label, part.title].filter(Boolean).join(" ")].filter(Boolean);
  return [
    ...head,
    "",
    "[원문]", ...english,
    ...(translated ? ["", "[국문]", ...korean] : []),
    "",
    `[출처] ${source(act, part, part.page || 0)}`,
    `[주소] ${address(base, act, part)}`,
    translated ? NOTE : null,
    part.cut ? CUT : null,   // 받아 둘 때 뒷부분을 뺀 부속서: 통째로 인용한 글이 전부가 아님을 밝힌다
  ].filter((line) => line !== null).join("\n");
}
