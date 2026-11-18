// 인증서 비용 추정의 수를 화면에 적는 꼴과, 칸에 넣은 값을 수로 읽는 일. 비용 추정의 결과와 품목 한 장 보기가 함께 쓴다. 화면 요소를 다루지 않는다.
export const fixed = (value, digits) => Number(value).toLocaleString("ko-KR", { minimumFractionDigits: digits, maximumFractionDigits: digits });
export const tonnes = (value) => fixed(value, 3);                                   // 톤당 배출량(tCO2e)
export const pieces = (value) => fixed(value, value >= 100 || value === 0 ? 0 : value >= 10 ? 1 : 2); // 인증서 수
export const euros = (value) => fixed(value, value >= 1000 || value === 0 ? 0 : 2);  // 유로
export const percent = (value) => `${fixed(value, Number.isInteger(value) ? 0 : 1)}%`;

// 칸에 넣은 값: 0 이상의 수이면 그 수, 비었거나 수가 아니면 null
export function amount(value) {
  if (value === "" || value === null || value === undefined) return null;
  const number = Number(value);
  return Number.isFinite(number) && number >= 0 ? number : null;
}
