// 글을 파일로 내려받게 한다(표의 CSV). 표 계산 프로그램이 한글을 제대로 읽도록 맨 앞에 BOM을 붙인다.
import { h } from "./dom.js";

export function saveCsv(name, text) {
  const blob = new Blob([`﻿${text}`], { type: "text/csv;charset=utf-8" });
  const link = h("a", { href: URL.createObjectURL(blob), download: name });
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(link.href), 2000);
}
