// 색 고르기. 화면의 색 변형 세 가지를 바꿔 볼 수 있다. 메뉴에는 없고 주소 끝에 #design을 붙여 연다.
// 기본으로 쓸 변형은 js/theme.js의 DEFAULT가 정한다.
import { band } from "../ui/band.js";
import { fill, h } from "../ui/dom.js";

const VARIANTS = [
  { key: "navy", name: "네이비", line: "짙은 남색 머리에 밝은 본문", about: "머리글과 첫 화면의 큰 머리, 화면 머리 띠를 짙은 남색으로 두고 본문은 밝게 둡니다. 숫자와 단추에 노랑을 씁니다.", colors: ["#050b24", "#0a1540", "#003399", "#ffcc00", "#f4f6fb", "#ffffff"] },
  { key: "white", name: "화이트", line: "전체를 밝게", about: "머리 쪽까지 흰 바탕으로 두고, 지도와 강조만 파랑으로 둡니다. 가볍고 깔끔합니다.", colors: ["#ffffff", "#f1f5ff", "#2b59e0", "#003399", "#ffcc00", "#0b1230"] },
  { key: "midnight", name: "미드나잇", line: "전체를 어둡게", about: "본문까지 짙은 남색으로 둡니다. 어두운 곳에서 보기 편하고 숫자와 그림이 도드라집니다.", colors: ["#060b22", "#0d1535", "#121c45", "#5b82f5", "#ffcc00", "#eef1fb"] },
];

export async function render(main) {
  const current = (window.CBAM_THEME || {}).key || "navy";
  fill(main,
    band("화면 색", "화면의 색을 세 가지 가운데에서 골라 볼 수 있습니다. 내용과 기능은 모두 같습니다."),
    h("div", { class: "proposals" }, VARIANTS.map((variant) => h("section", { class: "proposal", "data-current": variant.key === current ? "true" : null }, [
      h("div", { class: "swatches", "aria-hidden": "true" }, variant.colors.map((color) => h("span", { class: "swatch", style: `background:${color}` }))),
      h("h2", { text: `${variant.name}: ${variant.line}` }),
      h("p", { text: variant.about }),
      h("p", {}, variant.key === current
        ? h("span", { class: "pill", "data-tone": "ok", text: "지금 보고 있는 색" })
        : h("a", { class: "btn", href: `?theme=${variant.key}#home`, text: "이 색으로 보기" })),
    ]))),
  );
}
