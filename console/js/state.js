// 초안의 상태를 판정 문서에서 읽어 내는 규칙. 화면도 데이터베이스도 쓰지 않아 따로 시험할 수 있다.
// 저장소의 tools/run/rechecks.py, holds_to_fix.py, holds_to_recheck.py와 같은 규칙이다(tests/test_console.py가 견준다).

// 글을 고치면 풀리는 보류 사유. 이런 보류는 다음 수집·작성 실행이 한 번 다시 쓴다.
const FIXABLE = new Set(["용어", "문체", "사실", "근거", "의무", "형식", "재이용"]);
// 원문을 열지 못한 보류. 다음 수집·작성 실행이 글을 그대로 둔 채 두 번까지 다시 검증에 낸다(-c2, -c3).
const UNOPENED = "확인 불가";
const LAST_TURN = 3;
const MAX_AGE_DAYS = 7;

// 이 초안이 몇 번째로 검증에 나온 것인지. id 끝의 -c2, -c3에서 읽는다.
export function turnOf(id) {
  const found = /-c(\d+)$/.exec(String(id));
  return found ? Number(found[1]) : 1;
}

function tooOld(at, now) {
  const judged = Date.parse(at || "");
  return Number.isFinite(judged) && now - judged > MAX_AGE_DAYS * 86400000;
}

// revisedIds: 다시 쓴 초안이 가리키는 옛 초안의 id들. resubmittedIds: 그대로 다시 낸 초안이 가리키는 옛 초안의 id들.
export function stateOf(item, verdict, revisedIds, resubmittedIds, now = Date.now()) {
  if (!verdict) return "검증 대기";
  if (verdict.result === "pass") return "통과";
  if (revisedIds.has(item.id)) return "보류(다시 씀)";
  if (resubmittedIds.has(item.id)) return "보류(다시 냄)";
  if (verdict.gate === UNOPENED) return turnOf(item.id) < LAST_TURN && !tooOld(verdict.at, now) ? "보류(다시 낼 예정)" : "보류(확인 필요)";
  if (!item.revises && FIXABLE.has(verdict.gate)) return "보류(다시 쓸 예정)";
  return "보류(확인 필요)";
}

export const isHold = (item) => item.state.startsWith("보류");
export const needsEyes = (item) => item.state === "보류(확인 필요)";
export const willRetry = (item) => item.state === "보류(다시 쓸 예정)" || item.state === "보류(다시 낼 예정)";
