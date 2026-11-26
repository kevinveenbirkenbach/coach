#!/usr/bin/env bash
set -euo pipefail
export PATH=/usr/bin:/bin

schedules="${COACH_SCHEDULES:-$(dirname "$0")/../../kvb-org-organize/scripts/schedules.py}"
[[ -f "${schedules}" ]] || exit 0
every="$(/usr/bin/python3 -I "${schedules}" check coach </dev/null 2>/dev/null)" || exit 0
[[ "${every}" =~ ^[1-9][0-9]?$ ]] || exit 0

hours="${COACH_STAMP_DIR:-${HOME}/.claude/.coach-hours}"
hour="${COACH_HOUR:-$(date +%Y-%m-%dT%H)}"
epoch="$(date -d "${hour/T/ }:00" +%s)" || exit 0
slot="every${every}h-$((epoch / 3600 / every))"

mkdir -p "${hours}"
mkdir "${hours}/${slot}" 2>/dev/null || exit 0
find "${hours}" -mindepth 1 -maxdepth 1 -type d ! -name "${slot}" -exec rmdir {} +

case "${hour##*T}" in
  22 | 23 | 0[0-5]) tip="😴 Late: wind down, screens off soon, seven to nine hours of sleep." ;;
  1[2-3] | 1[8-9]) tip="🥗 Meal time: a real meal with vegetables and protein, and a glass of water." ;;
  *) tip="🚶 Stand up, stretch neck, hips and back for two minutes, and drink a glass of water." ;;
esac

printf 'COACH HOUR: open your answer with this one line for the operator, word for word, then continue with the request; load no skill for it:\n%s (More: /kvb-coach)\n' "${tip}"
