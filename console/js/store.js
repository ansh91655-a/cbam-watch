// 데이터베이스 접근. 화면 파일은 이 모듈만 거친다.

let dbPromise = null;

// 실행 환경이 준비될 때까지 잠깐 기다린다. 끝내 없으면 null.
function waitForRuntime(limitMs = 5000) {
  return new Promise((resolve) => {
    const started = Date.now();
    const tick = () => {
      if (window.claude && typeof window.claude.use === "function") {
        resolve(window.claude);
      } else if (Date.now() - started > limitMs) {
        resolve(null);
      } else {
        setTimeout(tick, 100);
      }
    };
    tick();
  });
}

export function getDb() {
  if (!dbPromise) {
    dbPromise = waitForRuntime()
      .then((runtime) => (runtime ? runtime.use("db") : null))
      .catch(() => null);
  }
  return dbPromise;
}

// 컬렉션을 한 번만 구독한다. 반환값은 구독 해제 함수.
export async function watchCollection(path, options, onData, onError) {
  const { orderBy = null, dir = "desc", limit = 200 } = options || {};
  const db = await getDb();
  if (!db) {
    onError({ code: "not_available", message: "데이터베이스를 쓸 수 없습니다" });
    return () => {};
  }
  let query = db.collection(path);
  if (orderBy) query = query.orderBy(orderBy, dir);
  if (limit) query = query.limit(limit);
  return query.onSnapshot(
    (snap) => onData(snap.docs.map((doc) => ({ id: doc.id, ...doc.data() })), snap.metadata),
    (error) => onError(error)
  );
}

// 컬렉션을 한 번 읽어 건수와 걸린 시간을 잰다(부하 시험용).
export async function countCollection(path, limit = 1000) {
  const db = await getDb();
  if (!db) return null;
  const started = performance.now();
  const snap = await db.collection(path).limit(limit).get();
  return { count: snap.size, ms: Math.round(performance.now() - started) };
}
