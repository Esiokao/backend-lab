#!/bin/sh
# Poll until every probe command succeeds in the same round.
#
# Usage: wait_for.sh <attempts> <sleep-seconds> <failure-log-command> <probe> [<probe>...]
#   attempts              max polling rounds before giving up
#   sleep-seconds         pause between rounds
#   failure-log-command   diagnostic command run once before failing ("" skips it)
#   probe                 shell command; every probe must succeed in one round
set -eu

attempts=$1
sleep_seconds=$2
failure_log_command=$3
shift 3

attempt=1
while [ "$attempt" -le "$attempts" ]; do
  ready=true
  for probe in "$@"; do
    if ! sh -c "$probe"; then
      ready=false
    fi
  done

  if [ "$ready" = true ]; then
    exit 0
  fi

  sleep "$sleep_seconds"
  attempt=$((attempt + 1))
done

if [ -n "$failure_log_command" ]; then
  sh -c "$failure_log_command"
fi
exit 1
