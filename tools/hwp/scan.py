"""HWPX 꾸러미 안의 글에서 낱말이 몇 번 나오는지 센다: python3 -m tools.hwp.scan <파일.hwpx> <낱말> [<낱말> …]

파일마다 (태그까지 넣어 센 수, 태그를 걷어 낸 글에서 센 수)를 찍는다. 두 수가 다르면 낱말이 글 조각 사이에서 끊긴 곳이 있다."""
import re
import sys
import zipfile


def texts(path):
    with zipfile.ZipFile(path) as box:
        for name in box.namelist():
            if name.endswith(".xml"):
                yield name, box.read(name).decode("utf-8", "replace")


def main(path, *words):
    with zipfile.ZipFile(path) as box:
        print(path.rsplit("/", 1)[-1], [(info.filename, info.compress_type, info.file_size) for info in box.infolist()][:12])
    for name, text in texts(path):
        plain = re.sub(r"<[^>]+>", "", text)
        hits = {word: (text.count(word), plain.count(word)) for word in words if word in plain or word in text}
        if hits:
            print("  ", name, hits)


if __name__ == "__main__":
    main(*sys.argv[1:])
