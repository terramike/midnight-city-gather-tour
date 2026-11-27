#!/usr/bin/env bash
# Midnight City rotation chain (v5, 2026-11-27).
#
# Mike's design: level everything semi-evenly with hacking (terrabyte's
# profession) always interleaved. Each leg trains ONE skill by +1 level
# (drivers resolve "next" at leg start); a hacker leg runs before every
# other skill's leg. Roster: 8 gathering skills + 5 crafting skills
# (crafting, smithing, cooking, chemistry, engineering). Combat skills
# join later on Mike's word. A skill that reaches 99 drops out of the
# rotation; when every leg in a full round reports already-99, the
# chain prints ALL DONE and exits (the systemd unit is
# Restart=on-failure, so a clean exit 0 stays stopped).
#
# Leg drivers handle their own load/hunger checks; on exit 4 the chain
# sells heavy goods (reserve-aware) and relaunches the leg, on exit 5
# it feeds and relaunches. A stalled leg is logged as SKILL STUCK and
# the rotation moves on rather than halting the whole system.
#
# Test hooks (env): ROT_LEG_MINUTES caps each leg (default 10080),
# ROT_SKILLS="mining,cooking" replaces the non-hacker roster,
# ROT_ROUNDS=N stops after N rounds (default 0 = forever).
set -u
cd "$(dirname "$0")"

STATE_DIR="$HOME/.midnight-city"
CHAIN_LOG="$STATE_DIR/gather-chain.log"
LEG_MINUTES="${ROT_LEG_MINUTES:-10080}"
MAX_ROUNDS="${ROT_ROUNDS:-0}"

GATHER_SKILLS=(mining woodcutting fishing farming scavenging agility infiltration energy)
CRAFT_SKILLS=(crafting smithing cooking chemistry engineering)
if [ -n "${ROT_SKILLS:-}" ]; then
  IFS=',' read -ra ROSTER <<< "$ROT_SKILLS"
else
  ROSTER=("${GATHER_SKILLS[@]}" "${CRAFT_SKILLS[@]}")
fi

log() { echo "[$(date +%H:%M:%S)] chain: $*" >> "$CHAIN_LOG"; }

is_craft() {
  local s
  for s in "${CRAFT_SKILLS[@]}"; do [ "$s" = "$1" ] && return 0; done
  return 1
}

feed_pass() { python3 feed.py >> "$CHAIN_LOG" 2>&1; log "feed pass done"; }
sell_pass() { python3 sell_heavy.py >> "$CHAIN_LOG" 2>&1; log "sell pass done"; }

# run one +1-level leg; returns 6 if the skill is already 99, else 0
leg() {
  local skill="$1"
  while true; do
    if is_craft "$skill"; then
      python3 craft_driver.py "$skill" next "$LEG_MINUTES"
    else
      python3 gather_driver.py "$skill" next "$LEG_MINUTES"
    fi
    local rc=$?
    case $rc in
      0) log "LEG DONE $skill (+1 level)"; return 0 ;;
      6) log "LEG SKIP $skill (already level 99)"; return 6 ;;
      7) log "LEG SKIP $skill (nothing craftable right now)"; return 0 ;;
      4) log "LEG $skill overburdened: sell pass, then resume leg"
         sell_pass ;;
      5) log "LEG $skill hungry: feed pass, then resume leg"
         feed_pass ;;
      2) log "SKILL $skill STUCK (driver stalled; rotation moving on)"
         return 0 ;;
      3) log "LEG TIMEOUT $skill (leg cap ${LEG_MINUTES}m; rotation moving on)"
         return 0 ;;
      *) log "LEG $skill driver exit $rc (rotation moving on)"; return 0 ;;
    esac
  done
}

log "rotation chain start (roster: ${ROSTER[*]}; hacker interleaved; leg cap ${LEG_MINUTES}m)"
round=0
while true; do
  round=$((round + 1))
  log "ROTATION ROUND $round start"
  feed_pass
  sell_pass
  not99=0
  for skill in "${ROSTER[@]}"; do
    leg hacking; rc_h=$?
    [ "$rc_h" -eq 6 ] || not99=1
    leg "$skill"; rc_s=$?
    [ "$rc_s" -eq 6 ] || not99=1
  done
  log "ROTATION ROUND $round complete"
  if [ "$not99" -eq 0 ]; then
    log "ALL DONE: every rotation skill at level 99"
    exit 0
  fi
  if [ "$MAX_ROUNDS" -gt 0 ] && [ "$round" -ge "$MAX_ROUNDS" ]; then
    log "rotation chain stopping after $round round(s) (ROT_ROUNDS)"
    exit 0
  fi
done
