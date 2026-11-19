// 일정 이름의 끝 괄호에 든 단서("보도 기준", "잠정")를 떼어 낸다.
// 칸이 좁아 이름이 잘려도 단서는 보이도록, 이름과 따로 작은 표시로 적는 데 쓴다.
import { h } from "./dom.js";

const CAVEATS = ["보도 기준", "잠정"];

// "EU·영국 정상회의(타결 발표 예상, 보도 기준)" → { name: "EU·영국 정상회의(타결 발표 예상)", flag: "보도 기준" }
export function splitCaveat(title) {
  const text = String(title || "");
  const match = text.match(/^(.*)\(([^()]*)\)$/);
  const parts = match ? match[2].split(",").map((part) => part.trim()) : [];
  const flag = CAVEATS.find((word) => parts.includes(word)) || "";
  if (!flag) return { name: text, flag: "" };
  const rest = parts.filter((part) => part !== flag).join(", ");
  return { name: rest ? `${match[1]}(${rest})` : match[1].trim(), flag };
}

// 단서의 작은 표시. 단서가 없으면 null.
export function caveatMark(flag) {
  return flag ? h("em", { class: "caveat", text: flag }) : null;
}
