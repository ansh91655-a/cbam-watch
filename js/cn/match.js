// 품목 코드가 CBAM 대상인지 가리는 셈. 화면 요소를 다루지 않으므로 시험에서도 그대로 쓴다.
// 품목 목록의 한 줄은 { codes: ["7208"], ex: false, except: [{ codes: ["72022"] }] } 꼴이다. 코드는 숫자만 적은 앞자리다.

export function digits(text) {
  return String(text || "").replace(/\D/g, "").slice(0, 10);
}

// 질의 코드와 목록의 코드가 어떤 사이인지: 질의가 그 코드에 든다("in"), 그 코드가 질의 아래에 있다("under"), 상관없다("").
function relation(query, code) {
  if (query.startsWith(code)) return "in";
  if (code.startsWith(query)) return "under";
  return "";
}

// 목록에서 질의와 닿는 줄을 찾는다. 줄마다 { entry, how, excluded, partly }를 돌려준다.
// excluded: 질의가 통째로 드는 제외 품목. partly: 질의 아래의 일부 코드만 제외하는 품목.
export function hits(query, entries) {
  const found = [];
  for (const entry of entries) {
    const how = entry.codes.map((code) => relation(query, code)).find(Boolean);
    if (!how) continue;
    const excluded = (entry.except || []).filter((item) => item.codes.some((code) => query.startsWith(code)));
    const partly = (entry.except || []).filter((item) => item.codes.some((code) => code.startsWith(query) && code !== query));
    found.push({ entry, how, excluded, partly });
  }
  return found;
}

// 판정. state는 "short"(자릿수가 모자람), "in"(대상), "part"(코드의 일부 품목만 대상: 목록에 ex로 적힌 것),
// "mixed"(하위 코드에 따라 다름), "excluded"(따로 제외한 품목), "out"(목록에 없음) 가운데 하나다.
export function verdict(text, entries) {
  const query = digits(text);
  if (query.length < 4) return { state: "short", query, rows: [] };
  const all = hits(query, entries);
  const inside = all.filter((hit) => hit.how === "in");
  const live = inside.filter((hit) => !hit.excluded.length);
  if (live.length) {
    const state = live.some((hit) => hit.partly.length) ? "mixed" : (live.every((hit) => hit.entry.ex) ? "part" : "in");
    return { state, query, rows: live };
  }
  const under = all.filter((hit) => hit.how === "under");
  if (under.length) return { state: "mixed", query, rows: under };
  if (inside.length) return { state: "excluded", query, rows: inside };
  return { state: "out", query, rows: [] };
}
