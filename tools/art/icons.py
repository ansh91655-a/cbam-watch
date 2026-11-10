"""화면에 쓰는 아이콘 모듈(site/js/ui/icons.js)을 만든다. 아이콘은 Lucide(ISC 라이선스)에서 가져온다.

쓰는 법: python -m tools.art.icons <lucide-static의 icons 폴더> [출력 파일]
아이콘을 더하거나 바꿀 때만 손으로 돌린다. 화면에서 쓰는 이름(왼쪽)과 Lucide의 이름(오른쪽)을 아래 표에 적는다.
"""
import json
import pathlib
import re
import sys

ICONS = {
    # 소식의 주제
    "law": "scale", "legis": "landmark", "declare": "clipboard-check", "emissions": "calculator", "verify": "shield-check",
    "price": "euro", "korea": "map-pin", "abroad": "globe", "events": "presentation", "etc": "ellipsis",
    # CBAM 대상 품목
    "cement": "brick-wall", "steel": "anvil", "aluminium": "layers", "fertilisers": "sprout", "electricity": "zap", "hydrogen": "atom",
    # 그 밖
    "download": "download", "out": "arrow-up-right", "calendar": "calendar-days", "search": "search", "file": "file-text",
    "trend": "trending-up", "clock": "clock", "news": "newspaper", "next": "chevron-right",
    # 안내 화면: 소식이 실리기까지의 단계와 항목
    "collect": "radar", "write": "pen-line", "publish": "send", "recheck": "refresh-cw",
    "who": "user-round", "what": "compass", "how": "list-checks", "limits": "triangle-alert", "reuse": "recycle", "stage": "flask-conical",
}


def inner(path):
    text = pathlib.Path(path).read_text(encoding="utf-8")
    body = re.search(r"<svg[^>]*>(.*)</svg>", text, re.S).group(1)
    return re.sub(r"\s+", " ", body).replace("> <", "><").strip()


def main(argv):
    if not argv:
        print("쓰는 법: python -m tools.art.icons <lucide-static/icons> [출력 파일]")
        return 1
    folder = pathlib.Path(argv[0])
    out = pathlib.Path(argv[1] if len(argv) > 1 else "site/js/ui/icons.js")
    book = {name: inner(folder / f"{source}.svg") for name, source in ICONS.items()}
    module = (
        "// 아이콘. tools/art/icons.py가 만든 파일이므로 손으로 고치지 않는다.\n"
        "// 그림은 Lucide(https://lucide.dev)의 것이다. ISC License, Copyright (c) Lucide Icons and Contributors.\n"
        "// 일부는 Feather(MIT License, Copyright (c) Cole Bemis)에서 온 것이다. 라이선스 전문은 assets/third-party.txt에 있다.\n"
        f"const ICONS = {json.dumps(book, ensure_ascii=False, indent=1)};\n\n"
        "const NS = \"http://www.w3.org/2000/svg\";\n\n"
        "// 이름으로 아이콘을 만든다. 꾸밈이므로 화면 낭독기에는 읽히지 않게 한다.\n"
        "export function icon(name, size = 20) {\n"
        "  const svg = document.createElementNS(NS, \"svg\");\n"
        "  for (const [key, value] of Object.entries({ viewBox: \"0 0 24 24\", width: size, height: size, fill: \"none\", stroke: \"currentColor\",\n"
        "    \"stroke-width\": 1.8, \"stroke-linecap\": \"round\", \"stroke-linejoin\": \"round\", \"aria-hidden\": \"true\", class: \"icon\" })) svg.setAttribute(key, value);\n"
        "  svg.innerHTML = ICONS[name] || ICONS.etc; // 이 파일에 든 고정된 그림이다. 데이터가 아니다.\n"
        "  return svg;\n"
        "}\n"
    )
    out.write_text(module, encoding="utf-8")
    print(json.dumps({"out": str(out), "icons": len(book), "bytes": len(module)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
