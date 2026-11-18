// 준비 목록에서 '확인함'으로 표시한 항목을 이 브라우저에 남겨 둔다(브라우저의 저장소). 사이트로 보내지 않는다.
// 저장소를 쓸 수 없는 환경(사생활 보호 창 등)이나 적지 못한 때에는 화면을 떠날 때까지만 기억한다.
// 저장소를 넘겨받으므로 node로 시험한다(tests/test_prepare.py).

export const KEY = "cbam.prepare.done";
const ID = /^[a-z][a-z0-9-]{0,39}$/;   // 항목 id의 꼴과 길이(tools/publish/prepare.py의 ID, ID_MAX와 같다)
const MOST = 400; // 이보다 많이 적혀 있으면 낡은 것으로 보고 앞의 것만 읽는다

// 저장소에서 표시한 항목의 id 묶음을 읽는다. 읽지 못하거나 꼴이 다르면 빈 묶음.
export function readDone(storage) {
  try {
    const saved = JSON.parse(storage.getItem(KEY) || "[]");
    return new Set(Array.isArray(saved) ? saved.filter((id) => typeof id === "string" && ID.test(id)).slice(0, MOST) : []);
  } catch (error) {
    return new Set();
  }
}

// 표시한 항목을 저장소에 적는다. 적었으면 true. 하나도 없으면 적어 둔 것을 지운다.
export function writeDone(storage, done) {
  try {
    if (done.size) storage.setItem(KEY, JSON.stringify([...done].sort()));
    else storage.removeItem(KEY);
    return true;
  } catch (error) {
    return false;
  }
}

// 항목 하나의 표시를 켜거나 끈 새 묶음
export function toggled(done, id, on) {
  const next = new Set(done);
  if (on) next.add(id); else next.delete(id);
  return next;
}

// 그 항목들의 표시만 지운 새 묶음(다른 역할의 표시는 남긴다)
export function cleared(done, ids) {
  const gone = new Set(ids);
  return new Set([...done].filter((id) => !gone.has(id)));
}

// 지금 목록에 있는 항목의 표시만 남긴 새 묶음(없어진 항목의 표시가 쌓이지 않게, 적기 전에 거른다)
export function pruned(done, known) {
  return new Set([...done].filter((id) => known.has(id)));
}

// 표시를 읽고 적는 창구. 저장소가 없거나 한 번이라도 적지 못하면, 그 뒤로는 기억해 둔 묶음을 쓴다(역할을 바꿔 화면을 다시 그려도 표시가 남는다).
// 적을 때마다 저장소를 다시 읽는 쪽(화면)에서 쓰면, 다른 탭에서 한 표시를 덮어쓰지 않는다.
let memory = new Set();
let failed = false;
export function keeper(storage) {
  const usable = () => Boolean(storage) && !failed;
  return {
    read: () => (usable() ? readDone(storage) : new Set(memory)),
    write: (done) => {
      if (usable() && writeDone(storage, done)) return true;
      failed = Boolean(storage);
      memory = new Set(done);
      return false;
    },
  };
}
