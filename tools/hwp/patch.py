"""HWPX 꾸러미 안의 글에서 낱말을 바꿔 새 꾸러미를 쓴다. 꾸러미의 파일 차례와 압축 방식은 그대로 둔다.

  python3 -m tools.hwp.patch <원본.hwpx> <새.hwpx> <바꿈표.json>      바꿈표는 [["옛 표기", "새 표기"], …]. 앞의 줄부터 차례로 바꾼다(긴 표기를 먼저 적는다)
글이 여러 조각으로 나뉘어 낱말이 끊긴 자리는 바꾸지 못하므로, 끝에 태그를 걷어 낸 글에 옛 표기가 남았는지 센다.
"""
import json
import re
import sys
import zipfile

TEXT_PARTS = ("Contents/section", "Preview/PrvText")


def swap(text, pairs):
    counts = {}
    for old, new in pairs:
        counts[old] = text.count(old)
        text = text.replace(old, new)
    return text, counts


def main(source, target, table):
    pairs = json.load(open(table, encoding="utf-8"))
    done, left = {}, {}
    with zipfile.ZipFile(source) as box, zipfile.ZipFile(target, "w") as out:
        for info in box.infolist():
            data = box.read(info.filename)
            if info.filename.startswith(TEXT_PARTS) and info.filename.endswith((".xml", ".txt")):
                text, counts = swap(data.decode("utf-8"), pairs)
                for old, count in counts.items():
                    done[old] = done.get(old, 0) + count
                plain = re.sub(r"<[^>]+>", "", text)
                for old, _ in pairs:
                    left[old] = left.get(old, 0) + plain.count(old)
                data = text.encode("utf-8")
            fresh = zipfile.ZipInfo(info.filename, date_time=info.date_time)
            fresh.compress_type, fresh.external_attr, fresh.create_system = info.compress_type, info.external_attr, info.create_system
            out.writestr(fresh, data)
    print(json.dumps({"바꾼 곳": done, "남은 곳": {old: count for old, count in left.items() if count}}, ensure_ascii=False))
    return 1 if any(left.values()) else 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:4]))
