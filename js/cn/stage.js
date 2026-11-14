// 하류제품 확대 개정안이 지금 어느 단계인지. 품목 코드 조회와 기관별 입장 비교표가 이 값으로 안내의 말을 스스로 바꾼다.
// 화면 요소를 다루지 않는다. 기준은 tools/run/cn_health.py의 adopted와 같다: 단계의 길에서 이름에 '채택'이 든 단계에 이르렀는가.
export const PROPOSAL_RULE = "cbam-downstream";
const ADOPTED = "채택";

export function adopted(rule) {
  if (!rule) return false;
  const first = (rule.path || []).findIndex((name) => String(name).includes(ADOPTED));
  return first >= 0 && Number(rule.at || 0) >= first;
}

// 규제 목록에서 그 개정안을 찾는다. 없으면 null.
export function proposalRule(body) {
  return ((body && body.regulations) || []).find((rule) => rule.id === PROPOSAL_RULE) || null;
}
