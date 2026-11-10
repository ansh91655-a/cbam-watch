"""사이트에 쓴 남의 자료(아이콘, 지도 자료, 글꼴)의 라이선스 고지를 한 파일(site/assets/third-party.txt)로 모은다.

쓰는 법: python -m tools.art.notices <node_modules 폴더> [출력 파일]
아이콘이나 지도, 글꼴의 판을 바꿀 때만 손으로 돌린다. 고지의 글은 각 꾸러미에 든 LICENSE 파일을 그대로 옮긴다.
"""
import json
import pathlib
import sys

# (사이트에서 쓰는 곳, 꾸러미 이름, 덧붙이는 말)
PARTS = [
    ("아이콘 (site/js/ui/icons.js)", "lucide-static", "Lucide https://lucide.dev"),
    ("점 지도의 나라 경계 (site/js/ui/heromap.js)", "world-atlas",
     "world-atlas https://github.com/topojson/world-atlas . 나라 경계 자료는 Natural Earth(공개 자료, https://www.naturalearthdata.com)의 것이다."),
    ("글꼴 (jsDelivr에서 불러 쓴다. 이 저장소에 파일을 두지 않는다)", "pretendard", "Pretendard https://github.com/orioncactus/pretendard"),
]


def main(argv):
    if not argv:
        print("쓰는 법: python -m tools.art.notices <node_modules> [출력 파일]")
        return 1
    root = pathlib.Path(argv[0])
    out = pathlib.Path(argv[1] if len(argv) > 1 else "site/assets/third-party.txt")
    blocks = ["이 사이트에 쓴 다른 사람의 자료와 그 라이선스입니다. (Third-party notices)\n"]
    for where, package, note in PARTS:
        meta = json.loads((root / package / "package.json").read_text(encoding="utf-8"))
        found = [root / package / name for name in ("LICENSE", "LICENSE.md", "LICENSE.txt") if (root / package / name).exists()]
        # 꾸러미에 LICENSE 파일이 없으면(글꼴) 라이선스의 이름만 적고 전문은 그 저장소를 보게 한다.
        text = found[0].read_text(encoding="utf-8").strip() if found else "이 꾸러미에는 LICENSE 파일이 들어 있지 않습니다. 라이선스의 전문은 위 주소의 저장소에 있습니다."
        blocks.append("\n".join([
            "=" * 78,
            f"{where}",
            f"{note}",
            f"판 {meta.get('version')}, 라이선스 {meta.get('license')}",
            "=" * 78,
            "",
            text,
            "",
        ]))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(blocks), encoding="utf-8")
    print(json.dumps({"out": str(out), "bytes": out.stat().st_size, "parts": len(PARTS)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
