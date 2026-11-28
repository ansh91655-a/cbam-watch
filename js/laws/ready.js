// 문서의 국문 번역이 준비된 정도. 사이트에는 검수를 마친 번역만 실리므로(tools/laws/build.py), 문단 수로 가린다.
// 퍼센트는 보여 주지 않는다: 다 준비된 문서에는 아무 표시가 없고, 그렇지 않은 문서에만 '번역 준비 중'이라고 적는다.
const LABELS = { none: "번역 준비 중", partial: "일부 번역 준비 중" };

// "ready"(다 실림), "partial"(일부만 실림), "none"(아직 실린 번역이 없음)
export function translation(progress) {
  const blocks = Number((progress || {}).blocks) || 0;
  const done = Number((progress || {}).done) || 0;
  if (!blocks || done >= blocks) return "ready";
  return done > 0 ? "partial" : "none";
}

// 화면에 적는 말. 다 준비된 문서는 빈 글이다
export function waitLabel(progress) {
  return LABELS[translation(progress)] || "";
}
