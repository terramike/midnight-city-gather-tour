#!/bin/bash
# Gathering tour chain: run the gather driver skill by skill to level 3
# (16,704 XP). Multi-source skills are staged across their level-1 sources
# so the haul covers every item type, not just the first source's yield.
#
# Usage:  MCITY_AGENT_ID=<your-agent-id> bash gather_chain.sh
# Requires: the Midnight City direct-control helper (mcity-control.mjs)
#           sitting next to gather_driver.py, and a connected agent session.
set -u
cd "$(dirname "$0")"
LOG="${MCITY_STATE_DIR:-$HOME/.midnight-city}/gather-chain.log"
mkdir -p "$(dirname "$LOG")"

run() { # sourceId skill targetXp maxMinutes
  echo "[$(date +%H:%M:%S)] chain: $2 via $1 -> $3 XP" >> "$LOG"
  python3 gather_driver.py "$1" "$2" "$3" "$4"
  echo "[$(date +%H:%M:%S)] chain: $2 via $1 finished (exit $?)" >> "$LOG"
}

# Plentiful-node skills first, single source each.
run tree_stand woodcutting 16704 240
run ore_vein mining 16704 240

# Fishing: 4 level-1 sources share the canal fishing spots; stage across them.
run canal_eddy fishing 4200 120
run river_eel_weir fishing 8400 120
run moon_oyster_reef fishing 12600 120
run roofwater_cistern fishing 16704 180

# Farming: 4 level-1 sources share the crop beds; stage across them.
run mycelium_nursery farming 4200 120
run rain_wheat_deck farming 8400 120
run rooftop_tomato_bed farming 12600 120
run violet_herb_plot farming 16704 180

# Scavenging: 5 level-1 sources, few nodes each; stage across them.
run arcology_refuse_dock scavenging 3400 120
run drone_wreckfield scavenging 6800 120
run floodwall_rubble scavenging 10200 120
run market_parts_bin scavenging 13600 120
run transit_scrap_heap scavenging 16704 180

# Scarce-node skills last (3-4 nodes each; slower, longer budgets).
run skybridge_rigging agility 16704 300
run patrol_locker infiltration 16704 300
run static_substation energy 16704 300

echo "[$(date +%H:%M:%S)] chain: ALL DONE" >> "$LOG"
