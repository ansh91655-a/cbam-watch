// 입법 절차의 자료(data/procedures.json)와 규제의 진행도(regulations.json의 progress)를 화면이 쓰기 좋은 꼴로 바꾸는 셈.
// 화면 요소를 다루지 않으므로 node로 시험한다. 단계의 상태를 정하는 일은 사이트를 만들 때 한다(tools/publish/rule_steps.py).

// 단계의 상태와 화면에 적는 말
export const STATES = { done: "마침", now: "진행 중", next: "다음", none: "기록 없음", todo: "남음" };

export function kindOf(book, key) {
  return ((book && book.kinds) || []).find((kind) => kind.key === key) || null;
}

// 다른 이름을 적는 말: "각료이사회라고도 부릅니다", "유럽감사원이라고도 부릅니다"(끝 글자에 받침이 있으면 '이'를 넣는다)
export function alsoCalled(name) {
  const text = String(name || "").trim();
  if (!text) return "";
  const code = text.charCodeAt(text.length - 1) - 0xac00;
  const closed = code >= 0 && code <= 11171 && code % 28 !== 0;
  return `${text}${closed ? "이" : ""}라고도 부릅니다`;
}

// 단계의 짧은 이름: "의회: 위원회 표결" → "위원회 표결"(누가 하는지를 따로 보여 주는 자리에 쓴다)
export function shortName(step) {
  const name = String(step.name || "");
  return name.includes(": ") ? name.split(": ").slice(1).join(": ") : name;
}

// 규제 하나의 세부 단계: 절차의 단계에 그 규제의 상태와 그 단계에서 일어난 사건을 붙인다.
// 절차마다 꼭 있지는 않은 단계(사전 준비, 자문 의견)는 기록이 있거나 진행 중일 때만 싣는다.
export function stepsOf(kind, rule) {
  const rows = new Map((((rule && rule.progress) || {}).steps || []).map((row) => [row.key, row]));
  const timeline = (rule && rule.timeline) || [];
  return (kind.steps || []).map((step) => {
    const row = rows.get(step.key) || { state: "todo" };
    return { ...step, state: row.state, note: row.note || "", events: (row.events || []).map((index) => timeline[index]).filter(Boolean) };
  }).filter((step) => !step.optional || step.state === "done" || step.state === "now");
}

// 꼭 있는 단계의 상태만(작은 진행 표시에 쓴다): [{ key, name, state }]
export function dots(kind, rule) {
  const rows = new Map((((rule && rule.progress) || {}).steps || []).map((row) => [row.key, row.state]));
  return (kind.steps || []).filter((step) => !step.optional).map((step) => ({ key: step.key, name: step.name, state: rows.get(step.key) || "todo" }));
}

// 지금 서 있는 곳: 진행 중인 단계가 있으면 그 단계들, 없으면 기다리는 다음 단계. 절차가 끝났으면 빈 것.
export function current(kind, rule) {
  const progress = (rule && rule.progress) || {};
  const names = (keys) => keys.map((key) => (kind.steps || []).find((step) => step.key === key)).filter(Boolean).map((step) => step.name);
  if ((progress.now || []).length) return { label: "지금", names: names(progress.now) };
  if (progress.next) return { label: "다음", names: names([progress.next]) };
  return { label: "", names: [] };
}

// 진행도를 한두 문장으로
export function summary(kind, rule) {
  const progress = (rule && rule.progress) || {};
  const where = current(kind, rule);
  const quoted = where.names.map((name) => `‘${name}’`).join(", ");
  if (progress.finished) return `이 절차의 주요 단계 ${progress.total}개를 모두 지났습니다.`;
  const head = `주요 단계 ${progress.total}개 가운데 ${progress.passed}개를 지났습니다.`;
  if (where.label === "지금") return `${head} 지금은 ${quoted} 단계입니다.`;
  if (where.label === "다음") return `${head} 다음 단계는 ${quoted}입니다.`;
  return head;
}

// 세부 절차가 있고 아직 끝나지 않은 규제(한눈에 보기에 싣는다)
export function ongoing(rules) {
  return (rules || []).filter((rule) => rule.progress && !rule.progress.finished);
}

// 그 기관이 맡은 단계에서 일어난 일을 새 것부터: [{ rule, step, event }]. 규제 화면으로 이어 주는 '최근에 한 일'에 쓴다.
export function activity(book, rules, who, limit = 4) {
  const found = [];
  for (const rule of rules || []) {
    const kind = rule.progress ? kindOf(book, rule.progress.kind) : null;
    if (!kind) continue;
    for (const row of rule.progress.steps || []) {
      const step = kind.steps.find((one) => one.key === row.key);
      if (!step || !(step.who || []).includes(who)) continue;
      for (const index of row.events || []) {
        const event = rule.timeline[index];
        if (event && !event.press) found.push({ rule, step, event });
      }
    }
  }
  return found.sort((a, b) => String(b.event.date).localeCompare(String(a.event.date))).slice(0, limit);
}

// 기관별 줄 그림의 칸들. 절차의 단계를 차례로 놓되, 같은 때에 따로 나아가는 갈래(track)의 단계들은 한 묶음의 줄에 나란히 놓는다.
// 돌려주는 것: { lanes: [기관], rows: 줄 수, cells: [{ step, from, to, row, span }] }
//   from, to는 칸이 차지하는 줄(기관)의 차례 번호(1부터, to는 끝 다음), row는 시작하는 줄, span은 줄 수.
//   줄에 선 기관이 하지 않는 단계(관보 게재, 자문 의견)는 모든 줄을 가로지른다(wide).
export function lanes(kind) {
  const names = kind.lanes || [];
  const cells = [];
  let row = 1;
  const place = (step, at, span) => {
    const columns = (step.who || []).map((who) => names.indexOf(who)).filter((index) => index >= 0).sort((a, b) => a - b);
    const joined = columns.length && columns[columns.length - 1] - columns[0] === columns.length - 1;   // 이웃한 줄들이면 하나로 잇는다
    if (!columns.length) cells.push({ step, from: 1, to: names.length + 1, row: at, span, wide: true });
    else if (joined) cells.push({ step, from: columns[0] + 1, to: columns[columns.length - 1] + 2, row: at, span });
    else for (const column of columns) cells.push({ step, from: column + 1, to: column + 2, row: at, span });
  };
  const steps = kind.steps || [];
  for (let index = 0; index < steps.length;) {
    const step = steps[index];
    const inLane = (one) => (one.who || []).some((who) => names.includes(who));
    if (!step.track || !inLane(step)) {
      place(step, row, 1);
      row += 1;
      index += 1;
      continue;
    }
    // 갈래가 있는 단계들이 이어진 곳: 갈래마다 위에서 아래로 놓고, 묶음의 높이는 가장 긴 갈래에 맞춘다
    const block = [];
    while (index < steps.length && steps[index].track && inLane(steps[index])) block.push(steps[index++]);
    const tracks = [...new Set(block.map((one) => one.track))];
    const height = Math.max(...tracks.map((track) => block.filter((one) => one.track === track).length));
    for (const track of tracks) {
      const mine = block.filter((one) => one.track === track);
      mine.forEach((one, at) => place(one, row + at, at === mine.length - 1 ? height - at : 1));
    }
    row += height;
  }
  return { lanes: names, rows: row - 1, cells };
}
