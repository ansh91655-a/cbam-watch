// 데이터베이스의 문서들을 화면이 쓰기 좋은 모양으로 묶는다.
// 항목의 상태는 문서를 고쳐서가 아니라 판정 문서가 있는지로 읽는다(더하기만 하는 기록 방식).
import { getDb } from "./store.js";

async function readAll(path, orderBy, limit) {
  const db = await getDb();
  if (!db) throw new Error("not_available");
  const snap = await db.collection(path).orderBy(orderBy, "desc").limit(limit).get();
  return snap.docs.map((doc) => ({ id: doc.id, ...doc.data() }));
}

export async function load() {
  const [runs, items, verdicts, candidates] = await Promise.all([
    readAll("runs", "startedAt", 120),
    readAll("items", "writtenAt", 300),
    readAll("verdicts", "at", 400),
    readAll("candidates", "at", 300),
  ]);
  const verdictOf = new Map(verdicts.map((verdict) => [verdict.id, verdict]));
  const rows = items.map((item) => {
    const verdict = verdictOf.get(item.id) || null;
    const state = !verdict ? "검증 대기" : verdict.result === "pass" ? "통과" : "보류";
    return { ...item, verdict, state };
  });
  return { runs, items: rows, candidates };
}

export function today() {
  return new Date(Date.now() + 9 * 3600000).toISOString().slice(0, 10);
}

export function latest(runs, kind) {
  return runs.find((run) => run.kind === kind) || null;
}
