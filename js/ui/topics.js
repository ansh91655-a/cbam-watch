// 소식의 주제 목록. 시작할 때 한 번 읽어 두고 화면들이 이름과 차례를 물어본다.
import * as data from "../data.js";

const OTHER = "etc";
let list = [];
let book = new Map();

export async function loadTopics() {
  list = await data.topics();
  book = new Map(list.map((topic) => [topic.code, topic]));
  return list;
}

export function topicList() {
  return list;
}

// 소식의 주제 코드. 목록에 없는 값이면 '기타'로 본다.
export function topicOf(item) {
  return book.has(item.topic) ? item.topic : OTHER;
}

export function topicName(code) {
  return book.get(code)?.name || book.get(OTHER)?.name || "기타";
}

export function topicAbout(code) {
  return book.get(code)?.about || "";
}
