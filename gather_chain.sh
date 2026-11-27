#!/bin/bash
# Gathering tour chain v4 (2026-11-26): every gathering skill to MAX
# (level 99). The driver is tier-aware: it discovers each skill's sources
# from live progression and always gathers the highest tier the agent's
# level unlocks (req 1 ~29 XP/pull, req 11 ~69, req 21 ~109, ...).
# Chain duties: feed at start and after each skill, sell the heavy
# sellables (driver exit 4), feed on hunger (exit 5), relaunch the skill
# on stall/timeout exits (2/3). Rare items are never sold.
set -u
cd "$(dirname "$0")"
LOG="$HOME/.midnight-city/gather-chain.log"

sell() {
  echo "[$(date +%H:%M:%S)] chain: sell pass" >> "$LOG"
  python3 sell_heavy.py >> "$LOG" 2>&1
  echo "[$(date +%H:%M:%S)] chain: sell pass done" >> "$LOG"
}

feed() {
  echo "[$(date +%H:%M:%S)] chain: feed pass" >> "$LOG"
  python3 feed.py >> "$LOG" 2>&1
  echo "[$(date +%H:%M:%S)] chain: feed pass done" >> "$LOG"
}

skill() { # skill
  local sk="$1"
  echo "[$(date +%H:%M:%S)] chain: SKILL $sk -> level 99 (tier-aware)" >> "$LOG"
  while true; do
    echo "[$(date +%H:%M:%S)] chain: $sk driver -> L99" >> "$LOG"
    python3 gather_driver.py "$sk" L99 10080
    rc=$?
    echo "[$(date +%H:%M:%S)] chain: $sk driver finished (exit $rc)" >> "$LOG"
    case "$rc" in
      0)
        sell
        feed
        echo "[$(date +%H:%M:%S)] chain: SKILL $sk LEVEL 99 DONE" >> "$LOG"
        return 0
        ;;
      4) sell ;;
      5) feed ;;
      *) sleep 60 ;;  # stall/timeout: brief pause, then relaunch
    esac
  done
}

feed  # start fed
sell  # start light

skill mining
skill woodcutting
skill fishing
skill farming
skill scavenging
skill agility
skill infiltration
skill energy

echo "[$(date +%H:%M:%S)] chain: ALL DONE" >> "$LOG"
