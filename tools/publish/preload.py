"""화면 모듈을 한꺼번에 받게 하는 줄을 지어 낸 index.html의 머리에 넣는다.

js/app.js는 화면마다의 모듈을 import로 잇고, 그 모듈이 다시 다른 모듈을 잇는다. 브라우저는 모듈 하나를 받아 읽은 뒤에야
그 모듈이 잇는 다음 모듈을 알게 되므로, 이음이 여러 겹이면 그 겹만큼 서버를 오간다. <link rel="modulepreload">를 모듈마다
적어 두면 처음부터 한꺼번에 받아, 처음 여는 사람의 첫 화면이 그만큼 빨리 뜬다.

- 넣는 것: js/app.js에서 import ... from "./…"로 이어진 모듈 모두(app.js 자신도).
- 넣지 않는 것: import()로 그때그때 받는 모듈(의견 보내기, 새 소식 받아 보기)과 바깥 라이브러리(pdf.min.js). 쓰지 않을 수도 있는 것을 미리 받지 않는다.
- site/index.html은 건드리지 않는다. 지어 낸 폴더의 index.html만 고친다(tools/publish/build_site.py가 부른다).
- 이음을 따라가다 없는 파일을 만나면 아무것도 넣지 않고 그 까닭을 돌려준다. 줄이 없어도 사이트는 그대로 돌아간다.
"""
import pathlib
import posixpath
import re

ENTRY = "js/app.js"
MARK = '<script type="module" src="js/app.js"></script>'
# import … from "./x.js", export … from "./x.js", import "./x.js". 여러 줄에 걸친 import도 읽는다(따옴표가 나오기 전까지가 한 문장이다).
STATIC = re.compile(r"""^[ \t]*(?:import|export)\b[^'"`;]*?\bfrom\s*["'](\.{1,2}/[^"']+)["']|^[ \t]*import\s*["'](\.{1,2}/[^"']+)["']""", re.M)


def imports(text):
    """모듈의 글에서 이어 놓은 모듈의 주소들(적힌 차례대로)."""
    return [first or second for first, second in STATIC.findall(text)]


def modules(root, entry=ENTRY):
    """entry에서 이어진 모듈의 경로들(root 기준, 처음 만난 차례대로). 없는 파일을 만나면 (지금까지의 목록, 그 경로)를 돌려준다."""
    root = pathlib.Path(root)
    found, queue = [], [entry]
    while queue:
        path = queue.pop(0)
        if path in found:
            continue
        file = root / path
        if not file.is_file():
            return found, path
        found.append(path)
        for target in imports(file.read_text(encoding="utf-8")):
            queue.append(posixpath.normpath(posixpath.join(posixpath.dirname(path), target)))
    return found, None


def lines(paths):
    return "".join(f'<link rel="modulepreload" href="{path}">\n' for path in paths)


def inject(out):
    """지어 낸 폴더의 index.html에 줄을 넣는다. 돌려주는 값: (넣은 모듈 수, 넣지 못한 까닭 또는 "")."""
    page = pathlib.Path(out) / "index.html"
    if not page.is_file():
        return 0, "index.html이 없음"
    text = page.read_text(encoding="utf-8")
    if "modulepreload" in text:
        return 0, "이미 들어 있음"
    if text.count(MARK) != 1 or "</head>" not in text:
        return 0, "app.js를 부르는 줄이나 머리의 끝을 찾지 못함"
    paths, missing = modules(out)
    if missing:
        return 0, f"이어진 모듈을 찾지 못함: {missing}"
    page.write_text(text.replace("</head>", lines(paths) + "</head>", 1), encoding="utf-8")
    return len(paths), ""
