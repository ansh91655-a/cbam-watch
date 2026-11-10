"""운영 콘솔(Claude 아티팩트에 올리는 화면)의 폴더를 만든다.

콘솔은 사이트의 화면 도우미(dom.js, format.js)를 함께 쓴다. 저장소에 두 벌 두지 않고 여기서 복사한다.
모양(css)은 콘솔 폴더에 따로 둔다(공개 사이트의 디자인이 바뀌어도 운영 화면은 그대로 둔다).
쓰는 법: python -m tools.publish.build_console [출력 폴더]
"""
import pathlib
import shutil
import sys

SHARED = [("site/js/ui/dom.js", "js/ui/dom.js"), ("site/js/ui/format.js", "js/ui/format-base.js")]


def main(argv):
    out = pathlib.Path(argv[0] if argv else "_console")
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree("console", out)
    for source, target in SHARED:
        source_path, target_path = pathlib.Path(source), out / target
        if source_path.is_dir():
            shutil.copytree(source_path, target_path)
        else:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source_path, target_path)
    files = sorted(str(path.relative_to(out)) for path in out.rglob("*") if path.is_file())
    print("콘솔 폴더:", out, len(files), "개 파일")
    for name in files:
        print(" ", name)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
