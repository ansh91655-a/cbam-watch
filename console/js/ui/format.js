// 사이트와 같은 표기 함수에 콘솔만 쓰는 것을 더한다.
// format-base.js와 dom.js, css 폴더는 저장소에 두 벌 두지 않고, 콘솔 폴더를 만들 때(tools/publish/build_console) site에서 복사한다.
export * from "./format-base.js";

// 실행 기록의 건수를 국문 이름으로 풀어 쓴다.
const COUNT_LABEL = {
  candidates: "후보", written: "초안", rewritten: "다시 씀", excluded: "제외", bulk: "묶음", skipped: "건너뜀", waiting: "미룸",
  pending: "검증 대기", pass: "통과", hold: "보류", published: "게시", total: "누적",
  items: "지난주 소식", digest: "주간 요약", audited: "다시 대조", match: "일치", mismatch: "어긋남", unknown: "확인 불가", withdrawn: "요약 내림",
};

export function countsText(counts) {
  return Object.entries(counts || {}).map(([key, value]) => `${COUNT_LABEL[key] || key} ${value}`).join(", ");
}
