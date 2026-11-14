// 접근성 자동 검사(axe.mjs)가 돌려받은 위반 가운데 이 사이트에서는 위반이 아닌 것을 가려낸다.
// 딸린 도구 없이 읽히는 파일이라 node로 바로 시험한다(tests/test_sitecheck.py).

// 건너뛰기 링크가 아닌데 그렇게 잡히는 자리. 사이트의 링크는 모두 #으로 시작하는 주소라, axe는 화면 왼쪽 밖에 놓인 링크를
// '본문으로 건너뛰기' 같은 건너뛰기 링크로 보고 그 주소의 요소를 찾는다(skip-link). 좁은 화면에서 가로로 넘겨 보는 고르기 줄(.side-nav)은
// 고른 것이 보이도록 옮겨 두므로(site/js/ui/sidenav.js) 앞의 것들이 왼쪽 밖에 놓인다. 이 줄 안의 링크는 화면을 고르는 링크이므로 세지 않는다.
// 진짜 건너뛰기 링크(.skip)와 그 밖의 자리는 그대로 검사한다.
const NOT_SKIP_LINKS = [".side-nav"];

// axe가 돌려준 위반들에서 위의 자리를 뺀다: [{ id, impact, nodes: [고르는 말] }] → 같은 꼴. 남은 자리가 없는 위반은 뺀다.
export function kept(found) {
  return found.map((one) => (one.id === "skip-link" ? { ...one, nodes: one.nodes.filter((target) => !NOT_SKIP_LINKS.some((place) => target.includes(place))) } : one))
    .filter((one) => one.nodes.length);
}
