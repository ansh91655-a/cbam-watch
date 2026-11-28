// 날짜와 숫자를 화면에 보이는 꼴로 바꾼다.

const WEEKDAYS = ["일", "월", "화", "수", "목", "금", "토"];

// "2026-11-10" 또는 ISO 시각에서 날짜만.
export function day(value) {
  const match = String(value || "").match(/^(\d{4})-(\d{2})-(\d{2})/);
  return match ? `${match[1]}-${match[2]}-${match[3]}` : "";
}

// ISO 시각에서 "2026-11-10 08:20".
export function minute(value) {
  const match = String(value || "").match(/^(\d{4}-\d{2}-\d{2})[T ](\d{2}:\d{2})/);
  return match ? `${match[1]} ${match[2]}` : day(value);
}

// 한국 시각의 오늘 날짜.
export function today() {
  return new Date(Date.now() + 9 * 3600000).toISOString().slice(0, 10);
}

// 오늘에서 그 날짜까지 남은 날 수. 지난 날짜면 음수. 날짜를 읽지 못하면 null.
export function daysUntil(value) {
  const text = day(value);
  if (!text) return null;
  return Math.round((Date.parse(`${text}T00:00:00Z`) - Date.parse(`${today()}T00:00:00Z`)) / 86400000);
}

export function daysSince(value) {
  const left = daysUntil(value);
  return left === null ? null : -left;
}

// "55일 남음", "오늘", "3일 지남".
export function countdown(value) {
  const left = daysUntil(value);
  if (left === null) return "";
  if (left === 0) return "오늘";
  return left > 0 ? `${left}일 남음` : `${-left}일 지남`;
}

// "2027-01-04" → "2027년 1월 4일(월)", "2027-02" → "2027년 2월".
export function koreanDate(value, withYear = true) {
  const match = String(value || "").match(/^(\d{4})-(\d{2})(?:-(\d{2}))?/);
  if (!match) return "";
  const head = withYear ? `${match[1]}년 ` : "";
  if (!match[3]) return `${head}${Number(match[2])}월`;
  const weekday = WEEKDAYS[new Date(`${match[1]}-${match[2]}-${match[3]}T00:00:00Z`).getUTCDay()];
  return `${head}${Number(match[2])}월 ${Number(match[3])}일(${weekday})`;
}

export function bytes(value) {
  const number = Number(value) || 0;
  if (number >= 1048576) return `${(number / 1048576).toFixed(1)} MB`;
  if (number >= 1024) return `${Math.round(number / 1024)} KB`;
  return `${number} B`;
}

export function count(value) {
  return (Number(value) || 0).toLocaleString("ko-KR");
}

// 가격은 소수 둘째 자리까지.
export function price(value) {
  return Number(value).toFixed(2);
}

// 늘고 준 값에 부호를 붙인다. 빼기 기호는 숫자 폭에 맞는 글자를 쓴다.
export function signed(value, digits = 2) {
  const number = Number(value);
  if (!Number.isFinite(number)) return "";
  const body = Math.abs(number).toFixed(digits);
  return number > 0 ? `+${body}` : number < 0 ? `−${body}` : body;
}
