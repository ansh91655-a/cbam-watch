#!/bin/sh
# 저장소에 올린다. 올리기가 응답 없이 멈춰 서면 끊고 다시 해 본다(자동 실행에서 올리기가 3분 동안 멈춘 적이 있다).
# 세 번 모두 안 되면 1로 끝나서 그 실행이 실패로 남는다(조용히 넘어가지 않는다).
#
# 쓰는 법:
#   sh tools/dev/push.sh                      지금 가지의 커밋을 main에 올린다(먼저 받아서 그 위에 얹는다)
#   sh tools/dev/push.sh --force <주소> <가지>  한 커밋짜리 배포 가지를 덮어쓴다(사이트 배포)
# PUSH_LIMIT(한 번에 기다리는 초, 기본 120), PUSH_TRIES(해 보는 횟수, 기본 3)로 바꿀 수 있다.
limit="${PUSH_LIMIT:-120}"
tries="${PUSH_TRIES:-3}"

once() {
  if [ "${1:-}" = "--force" ]; then
    timeout "$limit" git push -q -f "$2" "$3"
  else
    git rebase --abort 2>/dev/null  # 앞의 시도가 받다가 끊겼으면 정리한다
    timeout "$limit" git pull -q --rebase --autostash origin main && timeout "$limit" git push -q origin HEAD:main
  fi
}

n=1
while [ "$n" -le "$tries" ]; do
  if once "$@"; then exit 0; fi
  echo "올리기 ${n}번째 실패" >&2
  n=$((n + 1))
  [ "$n" -le "$tries" ] && sleep "${PUSH_WAIT:-10}"
done
echo "저장소에 올리지 못했습니다(${tries}번 해 봄)." >&2
exit 1
