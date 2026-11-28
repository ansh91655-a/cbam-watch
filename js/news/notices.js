// 국내 공지·자료: 국내 기관의 게시판에 올라온 글 가운데 제목이 곧 내용인 것(행사 안내, 지원사업 공고, 자료실의 자료).
// 요약이 없는 한 줄 소식이라 소식의 기본 목록과 주제별 건수에서 빼고 따로 모아 보여 준다.
// 본문을 읽어 요약을 붙인 것(tools.publish.revise가 brief를 뗀 것)은 다시 보통 소식이 된다.
// 화면 요소를 다루지 않으므로 node로 시험한다(tests/test_sitejs.py).

export const NOTICES = "notices";  // 주소에 쓰는 값: #news-notices
export const NOTICE_NAME = "국내 공지·자료";
export const NOTICE_ABOUT = "국내 기관의 게시판에 올라온 행사·교육 안내와 지원사업 공고, 자료입니다. 제목이 곧 내용이어서 요약 없이 제목과 원문 링크만 싣습니다.";

export function isNotice(item) {
  return Boolean(item && item.brief && !item.withdrawn);
}

// 소식을 보통 소식과 국내 공지·자료로 가른다. 차례는 그대로 둔다.
export function split(items) {
  const news = [];
  const notices = [];
  for (const item of items || []) (isNotice(item) ? notices : news).push(item);
  return { news, notices };
}
