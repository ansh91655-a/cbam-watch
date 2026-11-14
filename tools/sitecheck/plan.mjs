// 무엇을 검사할지 정한다. 화면의 목록은 만든 사이트의 데이터에서 뽑아, 규제나 주제가 늘어도 따라간다.
import { readFileSync } from "node:fs";
import { join } from "node:path";

function read(site, name, fallback) {
  try { return JSON.parse(readFileSync(join(site, "data", name), "utf8")); } catch (error) { return fallback; }
}

// 해설서의 그림: 그림의 종류마다 한 번은 화면에서 보이게, 아직 못 본 종류를 가장 많이 가진 장부터 고른다.
export function figureChapters(book) {
  const kinds = (chapter) => new Set((chapter.sections || []).map((one) => one.figure && one.figure.kind).filter(Boolean));
  const left = new Set(book.flatMap((chapter) => [...kinds(chapter)]));
  const picked = [];
  while (left.size) {
    const news = (chapter) => [...kinds(chapter)].filter((kind) => left.has(kind)).length;
    const best = book.reduce((found, chapter) => (news(chapter) > news(found) ? chapter : found), book[0]);
    picked.push(best);
    for (const kind of kinds(best)) left.delete(kind);
  }
  return picked;
}

export function plan(site) {
  const items = (read(site, "items.json", { items: [] }).items || []).filter((item) => !item.withdrawn);
  const rules = read(site, "regulations.json", { groups: [], regulations: [] });
  const topics = read(site, "topics.json", { topics: [] }).topics || [];
  const calc = read(site, "calc.json", { goods: [] });
  // 소식 화면은 가장 최근에 나온 소식으로 본다(날마다 새 글로 검사하게 된다)
  const newest = [...items].sort((a, b) => String(b.published || "").localeCompare(String(a.published || "")))[0];
  const item = newest ? `#item-${newest.id}` : null;
  // 글에 나온 법령과 조문을 규정 원문으로 잇는 줄이 있는 소식 하나(요약 화면이 있는 것)
  const linked = Object.keys(read(site, "refs.json", { items: {} }).items || {}).map((id) => items.find((one) => one.id === id)).find((one) => one && !one.brief);
  const itemWithRefs = linked && (!newest || linked.id !== newest.id) ? `#item-${linked.id}` : null;
  const good = (calc.goods || []).some((row) => row[0] === "72081000") ? "#calc-72081000" : null;
  // 요약에 풀이가 달릴 용어(내재배출량)가 나오는 소식 하나
  const glossed = items.find((one) => !one.brief && String(one.summary || "").includes("내재배출량"));
  // 품목 한 장 보기: 품목 하나(값과 비용의 어림), 세부 품목이 여럿인 품목, 값의 표가 없는 부문(전력)의 품목. 코드 아래의 여러 품목은 #cn-7208이 본다
  const twoRows = (calc.goods || []).find((row) => row[5].length > 1);
  const unpriced = (read(site, "cn.json", { current: [] }).current || []).find((row) => row.sector === "electricity");
  const sheets = [good ? "#cn-72081000" : null, twoRows ? `#cn-${twoRows[0]}` : null, unpriced ? `#cn-${unpriced.codes[0]}` : null];
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
  // 해설서: 차례, 절이 가장 많은 장(식과 표가 있는 장), 절 하나를 가리키는 주소, 없는 장.
  // 다른 제도를 다루는 장(scope가 있는 장: 영국 CBAM)은 따로 본다(글 속 용어 풀이가 그 장에서는 그 범위의 용어만 쓴다)
  const book = read(site, "handbook.json", { chapters: [] }).chapters || [];
  const own = book.filter((chapter) => !chapter.scope);
  const longest = [...own].sort((a, b) => b.sections.length - a.sections.length)[0];
  const tabled = own.find((chapter) => chapter.sections.some((one) => one.table) && (!longest || chapter.id !== longest.id));
  const handbook = book.length ? ["#handbook", longest ? `#handbook-${longest.id}` : null, tabled ? `#handbook-${tabled.id}.${tabled.sections.find((one) => one.table).id}` : null, "#handbook-none"] : [];
  const glossBody = read(site, "gloss.json", { terms: [] });
  const scoped = book.filter((chapter) => chapter.scope).map((chapter) => `#handbook-${chapter.id}`);
  // 그 범위의 용어가 실제로 있는 장: 풀이 칸이 그 장으로만 이어지는지 다뤄 본다
  const scopedGloss = book.filter((chapter) => chapter.scope && (glossBody.terms || []).some((term) => term.scope === chapter.scope));
  // 해설서 전체를 한 화면에 놓는 화면(인쇄용): 가로 넘침과 화면 오류만 본다(접근성은 장 화면에서 본다)
  const whole = book.length ? "#handbook-all" : null;
  // 그림이 있는 장: 그림의 종류를 모두 한 번씩 본다(위에서 이미 보는 장은 뺀다)
  const drawn = figureChapters(book).map((chapter) => `#handbook-${chapter.id}`).filter((view) => !handbook.includes(view) && !scoped.includes(view));
  // 사이트 검색: 빈 화면, 여러 갈래에서 찾는 말, 품목 코드, 찾지 못하는 말
  const search = ["#search", `#search-${encodeURIComponent("기본값")}`, "#search-7208", "#search-zzzzqq"];
  // 없는 주소의 안내 화면: 찾으려던 화면을 어림할 수 있는 주소와 그럴 수 없는 주소
  const missing = ["#rule", "#nowhere-at-all"];
  return {
    // 가로 넘침과 화면 오류: 모든 화면을 일곱 너비로(폰 둘, 패드, 노트북 둘, 넓은 모니터 둘: 본문 폭이 넓어지는 1,560과 1,800의 단계)
    widths: [360, 390, 768, 1024, 1440, 1920, 2400],
    views: ["#home", "#news", topics[0] ? `#news-${topics[0].code}` : null, "#news-notices", "#news-recent", item, itemWithRefs, "#rules", ...(rules.groups || []).map((group) => `#rules-${group.code}`),
      "#rules-recent", "#rules-recent-90", ...missing,
      "#price", "#calc", good, "#calendar", "#calendar-2027", "#calendar-2027.role-verifier", "#calendar-2028", "#cn", "#cn-7208", ...sheets, "#sector", "#sector-aluminium", "#sector-electricity", ...handbook, ...drawn, ...scoped, whole, "#docs", ...laws, "#terms", "#about", "#design", ...search].filter(Boolean),
    // 규제 화면: 규제마다 네 너비로
    ruleWidths: [360, 768, 1440, 1920],
    rules: (rules.regulations || []).map(rule),
    // 접근성: 주요 화면을 두 너비, 세 가지 색으로
    axeWidths: [1280, 390],
    themes: ["", "?theme=white", "?theme=midnight"],
    axeViews: [...new Set(["#home", "#news", item, itemWithRefs, "#rules", "#rules-recent", missing[0], rule(withAnalysis), rule(withFigure), rule(withTable), "#price", "#calc", good,
      "#calendar", "#calendar-2027.role-verifier", "#cn-7208", sheets[0], "#sector", "#sector-electricity", handbook[0], handbook[1], ...drawn, ...scoped, "#docs", "#laws", law, revised ? `#changes-${revised.id}` : null, "#news-notices", "#news-recent", "#terms", "#about", search[1]].filter(Boolean))],
    good,
    // 글 속 용어 풀이를 다뤄 보는 화면: 해설서의 장 하나와, 요약에 용어가 나오는 소식 하나(용어의 자료가 있을 때), 범위가 있는 장
    glossViews: (glossBody.terms || []).length ? [handbook[1], glossed ? `#item-${glossed.id}` : null, ...scopedGloss.map((chapter) => `#handbook-${chapter.id}`)].filter(Boolean) : [],
    // 범위가 있는 장의 화면 → 그 장의 주소(풀이 칸의 링크는 이 주소로 시작해야 한다: 용어집은 EU CBAM의 용어라 잇지 않는다)
    glossScoped: Object.fromEntries(scopedGloss.map((chapter) => [`#handbook-${chapter.id}`, `#handbook-${chapter.id}.`])),
  };
}
