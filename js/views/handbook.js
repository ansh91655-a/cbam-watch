// CBAM 해설서. 제도가 돌아가는 차례를 장과 절로 풀어 쓴 글이다(글은 data/handbook.json에 있고, tools/publish/handbook.py가 검사해 싣는다).
// #handbook은 차례(장의 목록, 용어로 찾기), #handbook-<장>은 그 장, #handbook-<장>.<절>은 그 장을 열고 그 절로 옮겨 간다.
// #handbook-all은 해설서 전체를 한 화면에 놓는다(인쇄하거나 PDF로 저장할 때).
// 차례는 views/handbook/contents.js, 장 하나는 views/handbook/chapter.js, 절 하나는 views/handbook/section.js, 전체는 views/handbook/whole.js가 그린다.
import * as data from "../data.js";
import { band } from "../ui/band.js";
import { empty, fill } from "../ui/dom.js";
import { groupTabs } from "../ui/tabs.js";
import { chapterPage, reach } from "./handbook/chapter.js";
import { contents } from "./handbook/contents.js";
import { wholeBook } from "./handbook/whole.js";

const TITLE = "CBAM 해설서";
const WHOLE = "all";   // 전체를 한 화면에 놓는 주소(#handbook-all). 장의 이름으로는 쓰지 않는다(tools/publish/handbook.py가 막는다)

export async function render(main, arg) {
  const book = await data.handbook();
  const [chapterId, sectionId = ""] = String(arg || "").split(".");
  if (!book.chapters.length) {
    fill(main, band(TITLE, "", groupTabs("handbook")), empty("해설서를 불러오지 못했습니다. 잠시 뒤에 다시 열어 주세요."));
    return TITLE;
  }
  if (chapterId === WHOLE) {
    fill(main, band(`${TITLE} 전체`, book.lead, groupTabs("handbook")), wholeBook(book));
    return `전체 - ${TITLE}`;
  }
  const at = book.chapters.findIndex((chapter) => chapter.id === chapterId);
  if (at < 0) {
    fill(main, band(TITLE, book.lead, groupTabs("handbook")), contents(book, Boolean(chapterId)));
    return TITLE;
  }
  const chapter = book.chapters[at];
  fill(main, band(`${at + 1}장 ${chapter.title}`, chapter.lead, groupTabs("handbook")), chapterPage(book, at));
  // 화면을 바꾼 뒤에는 맨 위에서 시작하므로(router.js), 그다음에 그 절로 옮겨 간다
  if (sectionId) setTimeout(() => reach(sectionId, true), 0);
  return `${chapter.title} - ${TITLE}`;
}
