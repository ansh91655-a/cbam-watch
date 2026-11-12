// 규정 원문 화면들이 함께 기억하는 것: 방금 찾은 낱말(조문을 열었을 때 칠해 보이려는 것)과 보는 방식(나란히, 원문만, 국문만).
// 화면을 떠나면 잊는다(브라우저에 저장하지 않는다).
export const recent = { needles: [], mode: "both" };

export function remember(needles) {
  recent.needles = needles || [];
}
