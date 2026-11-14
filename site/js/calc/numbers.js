// 인증서 비용 추정의 수를 화면에 적는 꼴. 비용 추정의 결과와 품목 한 장 보기가 함께 쓴다. 화면 요소를 다루지 않는다.
export const fixed = (value, digits) => Number(value).toLocaleString("ko-KR", { minimumFractionDigits: digits, maximumFractionDigits: digits });
export const tonnes = (value) => fixed(value, 3);                                   // 톤당 배출량(tCO2e)
export const pieces = (value) => fixed(value, value >= 100 || value === 0 ? 0 : value >= 10 ? 1 : 2); // 인증서 수
export const euros = (value) => fixed(value, value >= 1000 || value === 0 ? 0 : 2);  // 유로
export const percent = (value) => `${fixed(value, Number.isInteger(value) ? 0 : 1)}%`;
