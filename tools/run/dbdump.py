"""데이터베이스에서 파일로 받아 둔 문서를 읽는다.

ArtifactData의 list나 query에 out_dir을 주면 문서가 <out_dir>/<컬렉션>/<문서 id>.json 으로 저장된다.
"""
import pathlib

from tools.common.jsonio import read_json


def ids(db_dir, collection):
    folder = pathlib.Path(db_dir) / collection
    return {path.stem for path in folder.glob("*.json")} if folder.exists() else set()


def docs(db_dir, collection):
    folder = pathlib.Path(db_dir) / collection
    result = {}
    if folder.exists():
        for path in sorted(folder.glob("*.json")):
            body = read_json(path, None)
            if isinstance(body, dict):
                result[path.stem] = body
    return result
