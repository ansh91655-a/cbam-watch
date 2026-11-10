"""출처 목록 읽기."""
from tools.common.jsonio import read_json

REGISTRY_PATH = "sources/registry.json"


def load(path=REGISTRY_PATH):
    data = read_json(path, {"sources": [], "keywords": []})
    return data.get("sources", []), data.get("keywords", [])


def github_sources(sources):
    """자동 실행(GitHub)이 맡는 출처만."""
    return [source for source in sources if source.get("collector") == "github" and source.get("watch")]
