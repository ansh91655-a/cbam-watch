// 무엇을 검사할지 정한다. 화면의 목록은 만든 사이트의 데이터에서 뽑아, 규제나 주제가 늘어도 따라간다.
import { readFileSync } from "node:fs";
import { join } from "node:path";

function read(site, name, fallback) {
  try { return JSON.parse(readFileSync(join(site, "data", name), "utf8")); } catch (error) { return fallback; }
}

export function plan(site) {
  const items = (read(site, "items.json", { items: [] }).items || []).filter((item) => !item.withdrawn);
  const rules = read(site, "regulations.json", { groups: [], regulations: [] });
  const topics = read(site, "topics.json", { topics: [] }).topics || [];
  const calc = read(site, "calc.json", { goods: [] });
  // 소식 화면은 가장 최근에 나온 소식으로 본다(날마다 새 글로 검사하게 된다)
  const newest = [...items].sort((a, b) => String(b.published || "").localeCompare(String(a.published || "")))[0];
  const item = newest ? `#item-${newest.id}` : null;
  const good = (calc.goods || []).some((row) => row[0] === "72081000") ? "#calc-72081000" : null;
  const withFigure = (rules.regulations || []).find((rule) => rule.figure);
  const withTable = (rules.regulations || []).find((rule) => rule.positions);
  const withAnalysis = (rules.regulations || []).find((rule) => rule.analysis);
  const rule = (one) => (one ? `#rules-${one.id}` : null);
  // 규정 원문: 목록, 찾은 결과, 번역이 있는 법령(첫 법령)과 번역이 없는 조문이 섞인 화면
  const acts = read(site, "laws/index.json", { acts: [] }).acts || [];
  const law = acts[0] ? `#law-${acts[0].id}` : null;
  const guide = acts.find((act) => act.group === "guide");  // EU 집행위원회 안내 문서(절로 나뉜다)
  const manual = acts.find((act) => act.group === "manual");  // 등록부 이용 안내서
  const single = acts.find((act) => act.group !== "act" && act.toc.length === 1);  // 조각이 하나뿐인 짧은 문서(알림이 붙는 것이 많다)
  const revised = acts.find((act) => act.changes);  // 앞선 판을 받아 두어 달라진 곳을 볼 수 있는 문서
  // 원문과 번역 PDF를 나란히 보는 화면: 쪽이 적은 문서 하나(없는 문서의 화면도 본다)
  const pdfs = read(site, "laws/pdf.json", { docs: {} }).docs || {};
  const small = Object.keys(pdfs).sort((a, b) => pdfs[a].pages - pdfs[b].pages)[0];
  const laws = acts.length ? ["#laws", `#laws-${encodeURIComponent("내재배출량 검증")}`, law, acts[1] ? `#law-${acts[1].id}.art-1` : null,
    guide ? `#law-${guide.id}.${(guide.toc.find((part) => part.kind === "section") || {}).id || "cover"}` : null,
    manual ? `#law-${manual.id}` : null, single ? `#law-${single.id}` : null, small ? `#pdf-${small}.p2` : null, "#pdf-none",
    // 문단 하나를 가리키는 주소와, 앞선 판과 달라진 곳 보기(앞선 판을 받아 둔 문서가 있을 때)
    acts[0] ? `#law-${acts[0].id}.art-2.1` : null, revised ? `#changes-${revised.id}` : null, "#changes-none"] : [];
  // 사이트 검색: 빈 화면, 여러 갈래에서 찾는 말, 품목 코드, 찾지 못하는 말
  const search = ["#search", `#search-${encodeURIComponent("기본값")}`, "#search-7208", "#search-zzzzqq"];
  return {
    // 가로 넘침과 화면 오류: 모든 화면을 다섯 너비로
    widths: [360, 390, 768, 1024, 1440],
    views: ["#home", "#news", topics[0] ? `#news-${topics[0].code}` : null, "#news-notices", item, "#rules", ...(rules.groups || []).map((group) => `#rules-${group.code}`),
      "#price", "#calc", good, "#calendar", "#calendar-2027", "#calendar-2027.role-verifier", "#calendar-2028", "#cn", "#cn-7208", "#docs", ...laws, "#terms", "#about", "#design", ...search].filter(Boolean),
    // 규제 화면: 규제마다 세 너비로
    ruleWidths: [360, 768, 1440],
    rules: (rules.regulations || []).map(rule),
    // 접근성: 주요 화면을 두 너비, 세 가지 색으로
    axeWidths: [1280, 390],
    themes: ["", "?theme=white", "?theme=midnight"],
    axeViews: [...new Set(["#home", "#news", item, "#rules", rule(withAnalysis), rule(withFigure), rule(withTable), "#price", "#calc", good,
      "#calendar", "#calendar-2027.role-verifier", "#cn-7208", "#docs", "#laws", law, revised ? `#changes-${revised.id}` : null, "#news-notices", "#terms", "#about", search[1]].filter(Boolean))],
    good,
  };
}
