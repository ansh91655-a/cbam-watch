// 데이터베이스의 문서들을 화면이 쓰기 좋은 모양으로 묶는다.
// 항목의 상태는 문서를 고쳐서가 아니라 판정 문서가 있는지로 읽는다(더하기만 하는 기록 방식).
import { getDb } from "./store.js";

// 글을 고치면 풀리는 보류 사유. 이런 보류는 다음 수집·작성 실행이 한 번 다시 쓴다.
const FIXABLE = new Set(["용어", "문체", "사실", "근거", "의무", "형식", "재이용"]);

async function readAll(path, orderBy, limit) {
  const db = await getDb();
  if (!db) throw new Error("not_available");
  const snap = await db.collection(path).orderBy(orderBy, "desc").limit(limit).get();
  return snap.docs.map((doc) => ({ id: doc.id, ...doc.data() }));
}

// 컬렉션이 아직 없거나 읽지 못해도 화면 전체가 멈추지 않게 빈 목록으로 둔다.
async function readOptional(path, orderBy, limit) {
  try {
    return await readAll(path, orderBy, limit);
  } catch (error) {
    return [];
  }
}

function stateOf(item, verdict, revisedIds) {
  if (!verdict) return "검증 대기";
  if (verdict.result === "pass") return "통과";
  if (revisedIds.has(item.id)) return "보류(다시 씀)";
  if (!item.revises && FIXABLE.has(verdict.gate)) return "보류(다시 쓸 예정)";
  return "보류(확인 필요)";
}

export async function load() {
  const [runs, items, verdicts, candidates, audits] = await Promise.all([
    readAll("runs", "startedAt", 120),
    readAll("items", "writtenAt", 300),
    readAll("verdicts", "at", 400),
    readAll("candidates", "at", 300),
    readOptional("audits", "at", 200),
  ]);
  const verdictOf = new Map(verdicts.map((verdict) => [verdict.id, verdict]));
  const revisedIds = new Set(items.map((item) => item.revises).filter(Boolean));
  const rows = items.map((item) => {
    const verdict = verdictOf.get(item.id) || null;
    return { ...item, verdict, state: stateOf(item, verdict, revisedIds) };
  });
  return { runs, items: rows, candidates, audits };
}

export function today() {
  return new Date(Date.now() + 9 * 3600000).toISOString().slice(0, 10);
}

export function latest(runs, kind) {
  return runs.find((run) => run.kind === kind) || null;
}

export const isHold = (item) => item.state.startsWith("보류");
export const needsEyes = (item) => item.state === "보류(확인 필요)";
