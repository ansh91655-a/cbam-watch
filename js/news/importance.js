// 소식의 중요도: 자료에 적힌 값(높음, 보통, 낮음)과 화면에 적는 이름. 카드의 표시와 소식 화면의 조건, 첫 화면의 차례가 같은 값을 쓴다.
// 가장 높은 것은 화면에 '중요'로 적는다(카드의 '중요' 표시, 첫 화면의 '중요 소식', 소식 화면의 조건이 같은 말을 쓴다).
// 화면 요소를 다루지 않으므로 node로 시험한다(tests/test_sitejs.py).
export const HIGH = "높음";
export const LOW = "낮음";
export const HIGH_NAME = "중요";

// 소식 화면의 '중요도' 조건에서 고르는 것: 값은 자료의 값, 글은 화면의 이름
export const IMPORTANCE = [{ value: HIGH, text: HIGH_NAME }, { value: "보통", text: "보통" }, { value: LOW, text: LOW }];

export const isHigh = (item) => Boolean(item) && item.importance === HIGH;
export const isLow = (item) => Boolean(item) && item.importance === LOW;
