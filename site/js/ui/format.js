// 날짜와 숫자를 화면에 보이는 꼴로 바꾼다.

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

// 오늘부터 며칠 지났는지. 날짜를 읽지 못하면 null.
export function daysSince(value) {
  const text = day(value);
  if (!text) return null;
  const then = new Date(`${text}T00:00:00+09:00`).getTime();
  return Math.floor((Date.now() - then) / 86400000);
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
