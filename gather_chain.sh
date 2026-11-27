#!/bin/bash
# Gathering tour chain v3 (Mike 2026-11-26): every gathering skill to MAX
# (level 99), not just level 3. Per skill, rotate its level-1 sources in
# long runs until the driver reports the level reached (exit 0).
# Exit 4 = overburdened -> sell the heavy sellables and relaunch the same
# source. Exit 3 (24h run cap) counts as progress -> next source.
# Exit 2 (stall) -> next source; a full rotation of pure stalls marks the
# skill STUCK and the chain moves on (the watcher flags it).
# Rare items are never sold.
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

skill() { # skill source1 [source2 ...]
  local sk="$1"; shift
  echo "[$(date +%H:%M:%S)] chain: SKILL $sk -> level 99 via: $*" >> "$LOG"
  while true; do
    local progress=0
    for src in "$@"; do
      while true; do
        echo "[$(date +%H:%M:%S)] chain: $sk via $src -> L99" >> "$LOG"
        python3 gather_driver.py "$src" "$sk" L99 1440
        rc=$?
        echo "[$(date +%H:%M:%S)] chain: $sk via $src finished (exit $rc)" >> "$LOG"
        if [ "$rc" -eq 0 ]; then
          sell
          feed
          echo "[$(date +%H:%M:%S)] chain: SKILL $sk LEVEL 99 DONE" >> "$LOG"
          return 0
        fi
        if [ "$rc" -eq 4 ]; then
          sell
          progress=1
          continue
        fi
        if [ "$rc" -eq 5 ]; then
          feed
          progress=1
          continue
        fi
        if [ "$rc" -eq 3 ]; then
          progress=1
        fi
        break
      done
    done
    if [ "$progress" -eq 0 ]; then
      echo "[$(date +%H:%M:%S)] chain: SKILL $sk STUCK (all sources stalled)" >> "$LOG"
      return 1
    fi
  done
}

feed  # start fed
sell  # start light

skill mining ore_vein
skill woodcutting tree_stand
skill fishing canal_eddy river_eel_weir moon_oyster_reef roofwater_cistern
skill farming mycelium_nursery rain_wheat_deck rooftop_tomato_bed violet_herb_plot
skill scavenging arcology_refuse_dock drone_wreckfield floodwall_rubble market_parts_bin transit_scrap_heap
skill agility skybridge_rigging
skill infiltration patrol_locker
skill energy static_substation

echo "[$(date +%H:%M:%S)] chain: ALL DONE" >> "$LOG"
