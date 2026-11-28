// 역할별 준비 목록의 셈: 주소에서 역할과 항목을 읽고, 항목이 기대는 의무 일정을 찾아 날짜와 글을 붙이고, 다가오는 날짜를 고른다.
// 자료는 준비 목록(prepare.json)과 의무 일정(duties.json)이다. 화면 요소를 다루지 않으므로 node로 시험한다(tests/test_prepare.py).

// 주소의 뒷부분("operator.o-kets")에서 역할과 항목을 읽는다. 역할이 없거나 목록에 없으면 첫 역할이다.
export function placeOf(arg, roles) {
  const [asked, item = ""] = String(arg || "").split(".");
  const role = (roles || []).find((one) => one.key === asked) || (roles || [])[0] || null;
  return { role: role ? role.key : "", item: role && role.key === asked ? item : "" };
}

// 역할(과 항목)을 주소로. 첫 역할은 역할을 적지 않는다.
export function hrefOf(roles, key, item = "") {
  const first = (roles || [])[0];
  if (item) return `#prepare-${key}.${item}`;
  return first && first.key === key ? "#prepare" : `#prepare-${key}`;
}

// 그 의무의 일정 가운데 다가오는 것. 해마다 돌아오는 의무(repeat)에는 "<id>-<해>"의 일정이 더 있고, 그 가운데 오늘이나 그 뒤의 첫 일정을 고른다.
// 모두 지났으면 마지막 것, 한 번뿐인 의무는 그 일정, 없는 의무는 null.
export function occurrence(duties, baseId, todayIso) {
  const base = (duties || []).find((duty) => duty.id === baseId);
  if (!base) return null;
  if (!base.repeat) return base;   // 이름이 "<id>-<해>"로 비슷한 다른 의무와 섞이지 않게, 되풀이하는 의무만 뒤 해의 일정을 찾는다
  const made = new RegExp(`^${String(baseId).replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}(-20\\d\\d)?$`);
  const mine = duties.filter((duty) => duty.repeat && made.test(String(duty.id))).sort((a, b) => String(a.date).localeCompare(String(b.date)));
  return mine.find((duty) => String(duty.date) >= String(todayIso)) || mine[mine.length - 1];
}

// 항목 하나를 화면에 놓을 꼴로.
// 제목과 글은 항목이 적은 것을 먼저 쓰고, 없으면 기대는 일정의 것을 쓴다(note가 있으면 일정의 그 글).
// 해마다 돌아오는 의무에 기대는 항목이 제 말로 적은 제목과 글은 첫 일정에 관한 것이다. 그 일정이 지나 다음 해의 일정으로 넘어가면 일정의 제목과 글을 쓴다
// (글은 첫 신고를 말하는데 날짜는 다음 해인 어긋남이 생기지 않게).
// 의무 일정을 읽지 못했으면 항목에 함께 실린 제목과 글(fallback)을 쓴다.
export function resolve(item, duties, todayIso) {
  const duty = item.duty ? occurrence(duties, item.duty, todayIso) : null;
  const moved = Boolean(duty) && duty.id !== item.duty;
  const own = moved ? {} : item;
  const spare = item.fallback || {};
  const noted = duty && item.note ? duty[item.note] : "";
  return {
    id: item.id,
    title: own.title || (duty ? duty.title : "") || item.title || spare.title || "",
    text: own.text || noted || (duty ? duty.text : "") || item.text || spare.text || "",
    noteKind: !own.text && item.note && (noted || (!duty && spare.text)) ? item.note : "",
    sections: item.sections || [],
    refs: item.refs || [],
    tool: item.tool || null,
    duty,
    date: duty ? duty.date : "",
    past: Boolean(duty) && String(duty.date) < String(todayIso),
  };
}

// 역할의 모든 항목(묶음의 차례대로)
export function itemsOf(role) {
  return ((role || {}).groups || []).flatMap((group) => group.items || []);
}

// 다가오는 날짜가 있는 항목을 이른 날부터 limit개. 같은 일정에 기대는 항목은 먼저 나온 하나만 고른다.
export function upcoming(rows, todayIso, limit = 4) {
  const seen = new Set();
  return rows.filter((row) => row.date && !row.past && String(row.date) >= String(todayIso))
    .sort((a, b) => String(a.date).localeCompare(String(b.date)))
    .filter((row) => (seen.has(row.duty.id) ? false : seen.add(row.duty.id)))
    .slice(0, limit);
}

// 확인한 항목의 수: { done, all }. 지금 목록에 없는 id는 세지 않는다.
export function progress(rows, done) {
  return { done: rows.filter((row) => done.has(row.id)).length, all: rows.length };
}
