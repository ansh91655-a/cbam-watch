#!/bin/sh
# 올리기 전에 돌리는 검사. 자동 실행 환경과 같게, requirements.txt의 꾸러미만 깐 깨끗한 환경에서 시험을 돌린다.
# (작업 환경에만 깔려 있는 꾸러미 덕에 시험이 통과하는 일을 막는다.)
# 쓰는 법: sh tools/dev/check.sh
set -e
cd "$(dirname "$0")/../.."
ENV_DIR="${TMPDIR:-/tmp}/cbam-watch-check-env"
if [ ! -x "$ENV_DIR/bin/python" ] || [ requirements.txt -nt "$ENV_DIR/installed" ]; then
  rm -rf "$ENV_DIR"
  python3 -m venv "$ENV_DIR"
  "$ENV_DIR/bin/pip" install -q -r requirements.txt
  touch "$ENV_DIR/installed"
fi
"$ENV_DIR/bin/python" -m unittest discover -s tests -t .
python3 -m tools.publish.build_site "${TMPDIR:-/tmp}/cbam-watch-check-site" > /dev/null
echo "검사 통과: 시험, 사이트 만들기"
