"""사이트의 주소와 배포하는 곳을 한 군데서 읽는다.

- 사이트 주소: site/site.config.json 의 url. 보고 글과 알림 글이 이 주소를 적는다.
- 배포하는 곳: deploy.json 의 siteRepo. 비어 있으면 이 저장소의 gh-pages 가지로 배포하고,
  "주인/이름"이 적혀 있으면 사이트만 싣는 그 공개 저장소의 gh-pages 가지로 배포한다(.github/workflows/pages.yml).
주소를 바꿀 때는 이 두 파일만 고친다.
"""
from tools.common.jsonio import read_json

DEFAULT_URL = "https://ansh91655-a.github.io/cbam-watch/"
CONFIG = "site/site.config.json"
DEPLOY = "deploy.json"


def site_url(config=None):
    """공개 사이트의 주소(끝에 빗금)."""
    config = read_json(CONFIG, {}) if config is None else config
    url = str((config or {}).get("url") or DEFAULT_URL).strip()
    return url if url.endswith("/") else url + "/"


def site_repo(deploy=None):
    """사이트만 싣는 저장소의 이름("주인/이름"). 이 저장소에서 바로 배포하면 빈 글."""
    deploy = read_json(DEPLOY, {}) if deploy is None else deploy
    name = str((deploy or {}).get("siteRepo") or "").strip().strip("/")
    return name if name.count("/") == 1 and " " not in name else ""


def deploy_remote(deploy=None):
    """배포한 가지를 받아 볼 git 원격. 이 저장소면 origin."""
    name = site_repo(deploy)
    return f"https://github.com/{name}" if name else "origin"
