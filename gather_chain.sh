#!/bin/bash
# Gathering tour chain v2 (sell policy, Mike 2026-11-26): run the driver
# skill by skill to level 3 (16,704 XP). Whenever the driver exits 4
# (overburdened), sell the heavy sellable commons (logs, ore) and relaunch
# the same stage. After each stage, sell once more so the next skill starts
# light. Rare items are never sold.
set -u
cd "$(dirname "$0")"
LOG="$HOME/.midnight-city/gather-chain.log"

sell() {
  echo "[$(date +%H:%M:%S)] chain: sell pass" >> "$LOG"
  python3 sell_heavy.py >> "$LOG" 2>&1
  echo "[$(date +%H:%M:%S)] chain: sell pass done" >> "$LOG"
}

run() { # sourceId skill targetXp maxMinutes
  while true; do
    echo "[$(date +%H:%M:%S)] chain: $2 via $1 -> $3 XP" >> "$LOG"
    python3 gather_driver.py "$1" "$2" "$3" "$4"
    rc=$?
    echo "[$(date +%H:%M:%S)] chain: $2 via $1 finished (exit $rc)" >> "$LOG"
    if [ "$rc" -eq 4 ]; then
      sell
      continue
    fi
    break
  done
  sell
}

sell  # start light

run ore_vein mining 16704 240

run canal_eddy fishing 4200 120
run river_eel_weir fishing 8400 120
run moon_oyster_reef fishing 12600 120
run roofwater_cistern fishing 16704 180

run mycelium_nursery farming 4200 120
run rain_wheat_deck farming 8400 120
run rooftop_tomato_bed farming 12600 120
run violet_herb_plot farming 16704 180

run arcology_refuse_dock scavenging 3400 120
run drone_wreckfield scavenging 6800 120
run floodwall_rubble scavenging 10200 120
run market_parts_bin scavenging 13600 120
run transit_scrap_heap scavenging 16704 180

run skybridge_rigging agility 16704 300
run patrol_locker infiltration 16704 300
run static_substation energy 16704 300

echo "[$(date +%H:%M:%S)] chain: ALL DONE" >> "$LOG"
