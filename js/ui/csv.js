// 표를 내려받는 파일(CSV)의 글을 짓는다. 화면 요소를 다루지 않는다(내려받게 하는 일은 save.js가 한다).

// 한 칸: 쉼표, 따옴표, 줄바꿈이 있으면 따옴표로 싼다. 빈 값(null, undefined)은 빈 칸이다.
export function csvCell(value) {
  if (value === null || value === undefined) return "";
  const text = String(value);
  return /[",\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

// 줄들([[칸, …], …])을 한 파일의 글로. 줄은 CRLF로 끝낸다(표 계산 프로그램이 읽는 꼴).
export function csvText(rows) {
  return `${rows.map((row) => row.map(csvCell).join(",")).join("\r\n")}\r\n`;
}
