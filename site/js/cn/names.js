// 품목 코드 조회의 이름과 적는 꼴: 부속서 I의 부문 이름, 판정의 이름, 코드를 띄어 적는 법.
// 품목 코드 조회와 사이트 검색이 함께 쓴다. 화면 요소를 다루지 않는다.
export const SECTOR = { cement: "시멘트", electricity: "전력", fertilisers: "비료", steel: "철강", aluminium: "알루미늄", chemicals: "화학제품(수소)", combined: "복합 금속 제품" };

// 온실가스의 이름(부속서 I의 표가 품목마다 적는 것)
export const GAS = { co2: "이산화탄소", n2o: "아산화질소", pfc: "과불화탄소" };

// 판정마다: [짧은 이름, 색, 설명]
export const STATE = {
  in: ["대상", "ok", "이 코드의 품목은 CBAM 대상입니다."],
  part: ["일부 품목만 대상", "warn", "이 코드의 품목 가운데 아래 품목 이름에 해당하는 것만 CBAM 대상입니다."],
  mixed: ["하위 코드에 따라 다름", "warn", "이 코드 아래의 일부 코드만 CBAM 대상입니다. 8자리 코드로 다시 확인해 주세요."],
  excluded: ["대상에서 제외", "", "이 코드는 부속서 I이 따로 제외한 품목입니다."],
  out: ["목록에 없음", "", "이 코드는 부속서 I의 대상 품목 목록에 없습니다."],
};

// "72081000" → "7208 10 00"
export function spaced(code) {
  return String(code).replace(/^(\d{4})(\d{2})?(\d{2})?(\d+)?$/, (all, a, b, c, d) => [a, b, c, d].filter(Boolean).join(" "));
}
