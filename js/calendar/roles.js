// 의무 일정을 역할로 골라 본다: 신고인·수입자, 제3국 사업자, 검증기관, 영국 수입자. 역할의 목록은 자료(duties.json의 roles)에 있다.
// 주소의 #calendar-<해>.role-<역할>로 고른 역할을 넘긴다. 화면 요소를 다루지 않으므로 node로 시험한다(tests/test_sitejs.py).

const PREFIX = "role-";

// 주소의 뒷부분("role-verifier")에서 역할의 key를 읽는다. 역할이 아니거나 목록에 없으면 빈 글.
export function roleIn(target, roles) {
  const key = String(target || "").startsWith(PREFIX) ? String(target).slice(PREFIX.length) : "";
  return (roles || []).some((role) => role.key === key) ? key : "";
}

// 역할을 주소의 뒷부분으로. 역할이 없으면 빈 글.
export function roleTarget(key) {
  return key ? `${PREFIX}${key}` : "";
}

// 그 역할의 의무만. 역할을 주지 않으면 모두.
export function forRole(duties, key) {
  return key ? (duties || []).filter((duty) => (duty.roles || []).includes(key)) : [...(duties || [])];
}

// 역할마다의 건수: [{ key, name, about, size }]. 그해에 의무가 하나도 없는 역할은 뺀다.
export function tally(duties, roles) {
  return (roles || []).map((role) => ({ ...role, size: forRole(duties, role.key).length })).filter((role) => role.size);
}
