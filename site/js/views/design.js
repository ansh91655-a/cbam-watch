// 디자인 안내와 색 변형 고르기. 지금의 디자인이 무엇을 참고했는지와, 색 변형 세 가지를 바꿔 볼 수 있게 한다.
// 변형을 정하면 js/theme.js의 기본값을 바꾸고 이 화면을 정리한다.
import { band } from "../ui/band.js";
import { fill, h, safeLink } from "../ui/dom.js";

const VARIANTS = [
  { key: "navy", name: "네이비", line: "짙은 남색 머리에 밝은 본문", about: "머리글과 첫 화면의 큰 머리, 화면 머리 띠를 짙은 남색으로 두고 본문은 밝게 둡니다. 숫자와 단추에 노랑을 씁니다.", colors: ["#050b24", "#0a1540", "#003399", "#ffcc00", "#f4f6fb", "#ffffff"] },
  { key: "white", name: "화이트", line: "전체를 밝게", about: "머리 쪽까지 흰 바탕으로 두고, 지도와 강조만 파랑으로 둡니다. 가볍고 깔끔합니다.", colors: ["#ffffff", "#f1f5ff", "#2b59e0", "#003399", "#ffcc00", "#0b1230"] },
  { key: "midnight", name: "미드나잇", line: "전체를 어둡게", about: "본문까지 짙은 남색으로 둡니다. 어두운 곳에서 보기 편하고 숫자와 그림이 도드라집니다.", colors: ["#060b22", "#0d1535", "#121c45", "#5b82f5", "#ffcc00", "#eef1fb"] },
];

// 참고한 것: [이름, 설명, [[링크 글, 주소], ...]]
const REFERENCES = [
  ["칸 배치(벤토 그리드)", "첫 화면을 크기가 다른 칸으로 나눈 배치입니다. Apple이 널리 알렸고 Vercel, Linear 같은 제품 사이트가 쓰는 방식을 따랐습니다.",
    [["벤토 그리드 설명", "https://studiomeyer.io/en/blog/bento-grid-layouts"]]],
  ["점으로 그린 지도와 흐름선", "땅을 점으로 찍고 두 곳을 선으로 잇는 그림은 GitHub와 Stripe가 첫 화면의 지구본에 쓴 방식입니다. 이 사이트의 지도는 공개 지도 자료로 직접 만든 평면 그림입니다.",
    [["GitHub의 설명", "https://github.blog/engineering/engineering-principles/how-we-built-the-github-globe/"], ["Stripe의 설명", "https://stripe.com/blog/globe"]]],
  ["큰 머리, 기능 칸, 마무리 띠", "큰 머리로 시작해 기능을 칸으로 보여 주고 짙은 띠로 마무리하는 짜임은 널리 쓰이는 템플릿 모음의 구획 나누기를 참고했습니다.",
    [["Tailwind Plus", "https://tailwindcss.com/plus"]]],
  ["EU의 색", "파랑 #003399와 노랑 #FFCC00은 EU 깃발의 색입니다. 깃발(별 열두 개)과 기관 로고는 쓰지 않았습니다.",
    [["EU의 깃발 안내", "https://european-union.europa.eu/principles-countries-history/symbols/european-flag_en"]]],
];

export async function render(main) {
  const current = (window.CBAM_THEME || {}).key || "navy";
  fill(main,
    band("디자인", "유명 사이트의 배치 방식을 참고해 다시 만든 디자인입니다. 색 변형 세 가지를 바꿔 볼 수 있습니다. 내용과 기능은 모두 같습니다."),
    h("section", { class: "stack", "aria-labelledby": "h-variants" }, [
      h("h2", { id: "h-variants", text: "색 변형" }),
      h("div", { class: "proposals" }, VARIANTS.map((variant) => h("section", { class: "proposal", "data-current": variant.key === current ? "true" : null }, [
        h("div", { class: "swatches", "aria-hidden": "true" }, variant.colors.map((color) => h("span", { class: "swatch", style: `background:${color}` }))),
        h("h3", { text: `${variant.name}: ${variant.line}` }),
        h("p", { text: variant.about }),
        h("p", {}, variant.key === current
          ? h("span", { class: "pill", "data-tone": "ok", text: "지금 보고 있는 변형" })
          : h("a", { class: "btn", href: `?theme=${variant.key}#home`, text: "이 변형으로 보기" })),
      ]))),
    ]),
    h("section", { class: "stack", "aria-labelledby": "h-refs" }, [
      h("h2", { id: "h-refs", text: "참고한 것" }),
      h("ul", { class: "refs" }, REFERENCES.map(([name, text, links]) => h("li", {}, [
        h("strong", { text: `${name}. ` }),
        h("span", { text: `${text} ` }),
        ...links.flatMap(([label, url], index) => [index ? " " : null, safeLink(url, label)]),
      ]))),
      h("p", { class: "count" }, [
        "그림은 모두 직접 만들었거나 자유롭게 쓸 수 있는 것입니다. 지도는 Natural Earth의 공개 자료, 아이콘은 Lucide, 글꼴은 Pretendard입니다. 사진은 쓰지 않았습니다. ",
        h("a", { href: "assets/third-party.txt", text: "쓴 자료의 라이선스 보기" }),
      ]),
    ]),
  );
}
